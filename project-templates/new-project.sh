#!/usr/bin/env bash
# =============================================================================
# iOPEX — new-project.sh
# Scaffold generator for new and existing projects.
#
# Usage:
#   ./project-templates/new-project.sh new              # Interactive new project
#   ./project-templates/new-project.sh apply <dir>      # Retroactive scaffold for existing project
#   ./project-templates/new-project.sh checklist <dir>  # Print missing/incomplete scaffold files
# =============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SCAFFOLD_DIR="$SCRIPT_DIR/scaffold"
TODAY=$(date +%Y-%m-%d)

# ── colours ──────────────────────────────────────────────────────────────────
GREEN='\033[0;32m'; CYAN='\033[0;36m'; AMBER='\033[0;33m'
RED='\033[0;31m'; BOLD='\033[1m'; RESET='\033[0m'

info()    { echo -e "${CYAN}▸ $*${RESET}"; }
success() { echo -e "${GREEN}✓ $*${RESET}"; }
warn()    { echo -e "${AMBER}⚠ $*${RESET}"; }
error()   { echo -e "${RED}✗ $*${RESET}"; exit 1; }
header()  { echo -e "\n${BOLD}$*${RESET}"; }

# =============================================================================
# SUBSTITUTE — replace [[PLACEHOLDER]] tokens in a file
# =============================================================================
substitute() {
  local file="$1"
  [[ ! -f "$file" ]] && return

  sed -i \
    -e "s|\[\[PROJECT_NAME\]\]|${PROJECT_NAME}|g" \
    -e "s|\[\[PROJECT_TITLE\]\]|${PROJECT_TITLE}|g" \
    -e "s|\[\[DESCRIPTION\]\]|${DESCRIPTION}|g" \
    -e "s|\[\[CUSTOMER\]\]|${CUSTOMER}|g" \
    -e "s|\[\[STACK_LANG\]\]|${STACK_LANG}|g" \
    -e "s|\[\[STACK_FRAMEWORK\]\]|${STACK_FRAMEWORK}|g" \
    -e "s|\[\[STACK_DB\]\]|${STACK_DB}|g" \
    -e "s|\[\[STACK_DEPLOY\]\]|${STACK_DEPLOY}|g" \
    -e "s|\[\[GITHUB_REPO\]\]|${GITHUB_REPO}|g" \
    -e "s|\[\[GITHUB_VISIBILITY\]\]|${GITHUB_VISIBILITY}|g" \
    -e "s|\[\[ENV_VARS\]\]|${ENV_VARS}|g" \
    -e "s|\[\[DATE_CREATED\]\]|${TODAY}|g" \
    -e "s|\[\[MILESTONES_DONE\]\]|${MILESTONES_DONE}|g" \
    -e "s|\[\[MILESTONES_NEXT\]\]|${MILESTONES_NEXT}|g" \
    -e "s|\[\[PROJECT_STATUS\]\]|${PROJECT_STATUS}|g" \
    "$file"
}

# =============================================================================
# COPY SCAFFOLD — copy template files into target dir, skip existing files
# =============================================================================
copy_scaffold() {
  local target="$1"
  local skipped=0
  local created=0

  while IFS= read -r -d '' tmpl; do
    rel="${tmpl#$SCAFFOLD_DIR/}"
    dest="$target/$rel"

    # Create parent dirs
    mkdir -p "$(dirname "$dest")"

    if [[ -f "$dest" ]]; then
      warn "SKIPPED (exists): $rel"
      ((skipped++)) || true
    elif [[ "$rel" == "pyproject.toml" && "$STACK_LANG" != "python" ]]; then
      : # skip pyproject for non-python projects
    else
      cp "$tmpl" "$dest"
      substitute "$dest"
      success "CREATED: $rel"
      ((created++)) || true
    fi
  done < <(find "$SCAFFOLD_DIR" -type f ! -name ".gitkeep" -print0 | sort -z)

  echo ""
  info "Created: $created  |  Skipped (already existed): $skipped"
}

# =============================================================================
# DETECT — auto-detect project properties from existing code
# =============================================================================
detect_project_properties() {
  local dir="$1"

  # Project name from directory
  PROJECT_NAME="${PROJECT_NAME:-$(basename "$dir")}"
  PROJECT_TITLE="${PROJECT_TITLE:-$(echo "$PROJECT_NAME" | sed 's/-/ /g' | awk '{for(i=1;i<=NF;i++) $i=toupper(substr($i,1,1)) substr($i,2)} 1')}"

  # Stack detection
  if [[ -z "${STACK_LANG:-}" ]]; then
    if [[ -f "$dir/pyproject.toml" ]] || ls "$dir"/*.py &>/dev/null 2>&1 || ls "$dir"/core/*.py &>/dev/null 2>&1; then
      STACK_LANG="python"
    elif [[ -f "$dir/package.json" ]]; then
      STACK_LANG="node"
    elif [[ -f "$dir/pom.xml" ]]; then
      STACK_LANG="java"
    elif [[ -f "$dir/frontend/index.html" ]] || [[ -f "$dir/index.html" ]]; then
      STACK_LANG="static"
    else
      STACK_LANG="unknown"
    fi
  fi

  # Framework detection
  if [[ -z "${STACK_FRAMEWORK:-}" ]]; then
    if grep -qr "fastapi\|FastAPI" "$dir" 2>/dev/null; then
      STACK_FRAMEWORK="fastapi"
    elif grep -qr "langgraph\|LangGraph" "$dir" 2>/dev/null; then
      STACK_FRAMEWORK="langgraph"
    elif grep -qr "spring\|SpringBoot" "$dir" 2>/dev/null; then
      STACK_FRAMEWORK="springboot"
    elif [[ "$STACK_LANG" == "static" ]]; then
      STACK_FRAMEWORK="vanilla-js"
    else
      STACK_FRAMEWORK="none"
    fi
  fi

  # DB detection
  if [[ -z "${STACK_DB:-}" ]]; then
    if grep -qr "pgvector\|postgresql\|psycopg" "$dir" 2>/dev/null; then
      STACK_DB="postgres+pgvector"
    elif grep -qr "mongodb\|pymongo" "$dir" 2>/dev/null; then
      STACK_DB="mongodb"
    elif grep -qr "supabase" "$dir" 2>/dev/null; then
      STACK_DB="supabase"
    elif [[ -f "$dir/docker-compose.yml" ]] && grep -q "postgres" "$dir/docker-compose.yml" 2>/dev/null; then
      STACK_DB="postgres"
    else
      STACK_DB="none"
    fi
  fi

  # Deploy target
  if [[ -z "${STACK_DEPLOY:-}" ]]; then
    if [[ -f "$dir/render.yaml" ]]; then
      STACK_DEPLOY="render"
    elif [[ -f "$dir/Dockerfile" ]] || [[ -f "$dir/docker-compose.yml" ]]; then
      STACK_DEPLOY="docker"
    elif ls "$dir"/*.yaml 2>/dev/null | xargs grep -l "kind: Deployment" &>/dev/null 2>&1; then
      STACK_DEPLOY="k8s"
    else
      STACK_DEPLOY="local"
    fi
  fi

  # GitHub repo from git remote
  if [[ -z "${GITHUB_REPO:-}" ]]; then
    GITHUB_REPO=$(git -C "$dir" remote get-url origin 2>/dev/null | sed 's|.*github.com[:/]||;s|\.git$||' || echo "jerm71279/[[REPO]]")
  fi

  # Description from existing CLAUDE.md or README
  if [[ -z "${DESCRIPTION:-}" ]]; then
    if [[ -f "$dir/CLAUDE.md" ]]; then
      DESCRIPTION=$(grep -m1 "^>" "$dir/CLAUDE.md" 2>/dev/null | sed 's/^> //' || echo "[[DESCRIPTION]]")
    elif [[ -f "$dir/README.md" ]]; then
      DESCRIPTION=$(grep -m1 "^>" "$dir/README.md" 2>/dev/null | sed 's/^> //' || echo "[[DESCRIPTION]]")
    else
      DESCRIPTION="[[DESCRIPTION]]"
    fi
  fi

  # Defaults for anything still unset
  CUSTOMER="${CUSTOMER:-internal}"
  GITHUB_VISIBILITY="${GITHUB_VISIBILITY:-private}"
  ENV_VARS="${ENV_VARS:-# See .env.example}"
  PROJECT_STATUS="${PROJECT_STATUS:-active}"
  MILESTONES_DONE="${MILESTONES_DONE:-See git log}"
  MILESTONES_NEXT="${MILESTONES_NEXT:-See CHANGELOG.md}"
}

# =============================================================================
# AUTO-GENERATE AGENTS.MD content from agents/ dir
# =============================================================================
generate_agents_content() {
  local dir="$1"
  local agents_dir=""

  # Find agents directory
  for d in "$dir/agents" "$dir/agent_api" "$dir/scripts"; do
    [[ -d "$d" ]] && agents_dir="$d" && break
  done

  [[ -z "$agents_dir" ]] && return

  local count=0
  while IFS= read -r f; do
    base=$(basename "$f" .py)
    echo "| $((++count)) | $base | — | [[ROLE]] |"
  done < <(find "$agents_dir" -name "agent_*.py" -o -name "*agent*.py" 2>/dev/null | sort)
}

# =============================================================================
# GENERATE CHECKLIST
# =============================================================================
generate_checklist() {
  local dir="$1"
  local checklist="$dir/CHECKLIST.md"
  local date
  date=$(date "+%Y-%m-%d %H:%M")

  {
    echo "# Scaffold Checklist — $(basename "$dir")"
    echo "Generated: $date"
    echo ""
    echo "## Scaffold Files"
    for f in CLAUDE.md README.md ARCHITECTURE.md AGENTS.md MAVERICK_CONTEXT.md CHANGELOG.md CONTRIBUTING.md LICENSE NOTICE.md Makefile render.yaml; do
      if [[ -f "$dir/$f" ]]; then
        if grep -q "\[\[" "$dir/$f" 2>/dev/null; then
          echo "- [ ] $f — **STUB** (contains unfilled [[PLACEHOLDER]] tokens)"
        else
          echo "- [x] $f"
        fi
      else
        echo "- [ ] $f — **MISSING**"
      fi
    done
    echo ""
    echo "## Manual Actions Required"
    echo "- [ ] Review AGENTS.md — fill in [[ROLE]] for each agent"
    echo "- [ ] Add architecture diagram or component map to ARCHITECTURE.md"
    echo "- [ ] Fill MAVERICK_CONTEXT.md with project history and client context"
    echo "- [ ] Populate CHANGELOG.md with actual version history"
    echo "- [ ] Replace all remaining [[PLACEHOLDER]] tokens"
    echo "- [ ] Add project-specific spells to prompts/spells/"
    echo ""
    echo "## Unfilled Placeholders Found"
    grep -rn "\[\[" "$dir" --include="*.md" --include="*.yaml" --include="*.toml" 2>/dev/null \
      | grep -v "node_modules\|.git\|SCAFFOLD-ONBOARDING" \
      | sed 's|'"$dir"'/||' \
      | head -30 \
      || echo "(none — all placeholders filled)"
  } > "$checklist"

  success "CHECKLIST written: $(basename "$checklist")"
}

# =============================================================================
# MODE: new — interactive new project
# =============================================================================
mode_new() {
  header "iOPEX New Project Scaffold"
  echo "Answer the prompts below. Press Enter to accept defaults."
  echo ""

  # Phase 1 — Identity
  header "Phase 1 — Project Identity"
  read -rp "Project name (kebab-case, e.g. accent-neutralizer): " PROJECT_NAME
  [[ -z "$PROJECT_NAME" ]] && error "Project name is required"
  PROJECT_NAME=$(echo "$PROJECT_NAME" | tr '[:upper:]' '[:lower:]' | tr ' ' '-')
  PROJECT_TITLE=$(echo "$PROJECT_NAME" | sed 's/-/ /g' | awk '{for(i=1;i<=NF;i++) $i=toupper(substr($i,1,1)) substr($i,2)} 1')

  read -rp "One-line description: " DESCRIPTION
  DESCRIPTION="${DESCRIPTION:-[[DESCRIPTION]]}"
  read -rp "Customer / client (or 'internal') [internal]: " CUSTOMER
  CUSTOMER="${CUSTOMER:-internal}"
  read -rp "Deployment target (render/docker/k8s/local) [render]: " STACK_DEPLOY
  STACK_DEPLOY="${STACK_DEPLOY:-render}"
  read -rp "GitHub repo (jerm71279/????): " GITHUB_REPO
  GITHUB_REPO="${GITHUB_REPO:-jerm71279/$PROJECT_NAME}"
  read -rp "Repo visibility (public/private) [private]: " GITHUB_VISIBILITY
  GITHUB_VISIBILITY="${GITHUB_VISIBILITY:-private}"

  # Phase 2 — Stack
  header "Phase 2 — Stack"
  read -rp "Primary language (python/node/java/static) [static]: " STACK_LANG
  STACK_LANG="${STACK_LANG:-static}"
  read -rp "Framework (fastapi/react/langgraph/vanilla/none) [none]: " STACK_FRAMEWORK
  STACK_FRAMEWORK="${STACK_FRAMEWORK:-none}"
  read -rp "Database (postgres/supabase/mongodb/none) [none]: " STACK_DB
  STACK_DB="${STACK_DB:-none}"

  # Phase 3 — Env vars
  header "Phase 3 — Environment Variables"
  read -rp "Required env vars (comma-separated or 'none') [none]: " ENV_VARS
  ENV_VARS="${ENV_VARS:-none}"

  # Phase 4 — Milestones
  header "Phase 4 — Milestones"
  read -rp "What is done so far (brief): " MILESTONES_DONE
  MILESTONES_DONE="${MILESTONES_DONE:-Initial scaffold}"
  read -rp "What is next (brief): " MILESTONES_NEXT
  MILESTONES_NEXT="${MILESTONES_NEXT:-Define architecture}"
  PROJECT_STATUS="active"

  # Confirm
  header "Summary"
  echo "  Name:     $PROJECT_NAME"
  echo "  Title:    $PROJECT_TITLE"
  echo "  Customer: $CUSTOMER"
  echo "  Stack:    $STACK_LANG / $STACK_FRAMEWORK / $STACK_DB"
  echo "  Deploy:   $STACK_DEPLOY"
  echo "  Repo:     $GITHUB_REPO ($GITHUB_VISIBILITY)"
  echo ""
  read -rp "Generate scaffold in ./$PROJECT_NAME/? (y/n) [y]: " confirm
  confirm="${confirm:-y}"
  [[ "$confirm" != "y" ]] && warn "Aborted." && exit 0

  TARGET_DIR="$PROJECT_NAME"
  mkdir -p "$TARGET_DIR"
  copy_scaffold "$TARGET_DIR"
  generate_checklist "$TARGET_DIR"

  echo ""
  success "Scaffold created at ./$TARGET_DIR"
  echo ""
  info "Next steps:"
  echo "  cd $TARGET_DIR"
  echo "  cat CHECKLIST.md"
  echo "  git add . && git commit -m 'feat: initial scaffold'"
}

# =============================================================================
# MODE: apply — retroactive scaffold for existing project
# =============================================================================
mode_apply() {
  local dir="${1:-}"
  [[ -z "$dir" ]] && error "Usage: $0 apply <project-dir>"
  [[ ! -d "$dir" ]] && error "Directory not found: $dir"

  header "iOPEX Scaffold — Applying to: $dir"
  info "Auto-detecting project properties..."

  # Reset all vars so detect can fill them
  PROJECT_NAME="" PROJECT_TITLE="" DESCRIPTION="" CUSTOMER=""
  STACK_LANG="" STACK_FRAMEWORK="" STACK_DB="" STACK_DEPLOY=""
  GITHUB_REPO="" GITHUB_VISIBILITY="" ENV_VARS=""
  PROJECT_STATUS="" MILESTONES_DONE="" MILESTONES_NEXT=""

  detect_project_properties "$dir"

  echo ""
  info "Detected:"
  echo "  Name:    $PROJECT_NAME"
  echo "  Stack:   $STACK_LANG / $STACK_FRAMEWORK / $STACK_DB"
  echo "  Deploy:  $STACK_DEPLOY"
  echo "  Repo:    $GITHUB_REPO"
  echo ""
  read -rp "Override any value before generating? (y/n) [n]: " override
  override="${override:-n}"

  if [[ "$override" == "y" ]]; then
    read -rp "Description [$DESCRIPTION]: " inp; DESCRIPTION="${inp:-$DESCRIPTION}"
    read -rp "Customer [$CUSTOMER]: " inp; CUSTOMER="${inp:-$CUSTOMER}"
    read -rp "Stack language [$STACK_LANG]: " inp; STACK_LANG="${inp:-$STACK_LANG}"
    read -rp "Framework [$STACK_FRAMEWORK]: " inp; STACK_FRAMEWORK="${inp:-$STACK_FRAMEWORK}"
    read -rp "Database [$STACK_DB]: " inp; STACK_DB="${inp:-$STACK_DB}"
    read -rp "Deploy target [$STACK_DEPLOY]: " inp; STACK_DEPLOY="${inp:-$STACK_DEPLOY}"
    read -rp "GitHub repo [$GITHUB_REPO]: " inp; GITHUB_REPO="${inp:-$GITHUB_REPO}"
    read -rp "Env vars [$ENV_VARS]: " inp; ENV_VARS="${inp:-$ENV_VARS}"
    read -rp "What is done [$MILESTONES_DONE]: " inp; MILESTONES_DONE="${inp:-$MILESTONES_DONE}"
    read -rp "What is next [$MILESTONES_NEXT]: " inp; MILESTONES_NEXT="${inp:-$MILESTONES_NEXT}"
  fi

  copy_scaffold "$dir"
  generate_checklist "$dir"

  echo ""
  success "Scaffold applied to: $dir"
  info "Review CHECKLIST.md for remaining manual steps."
}

# =============================================================================
# MODE: checklist — print scaffold status for existing project
# =============================================================================
mode_checklist() {
  local dir="${1:-}"
  [[ -z "$dir" ]] && error "Usage: $0 checklist <project-dir>"
  [[ ! -d "$dir" ]] && error "Directory not found: $dir"

  header "Scaffold Status — $(basename "$dir")"
  echo ""

  local present=0 stub=0 missing=0
  for f in CLAUDE.md README.md ARCHITECTURE.md AGENTS.md MAVERICK_CONTEXT.md CHANGELOG.md CONTRIBUTING.md LICENSE NOTICE.md Makefile render.yaml; do
    if [[ -f "$dir/$f" ]]; then
      if grep -q "\[\[" "$dir/$f" 2>/dev/null; then
        echo -e "  ${AMBER}STUB   ${RESET} $f  (contains unfilled [[PLACEHOLDER]] tokens)"
        ((stub++)) || true
      else
        echo -e "  ${GREEN}PRESENT${RESET} $f"
        ((present++)) || true
      fi
    else
      echo -e "  ${RED}MISSING${RESET} $f"
      ((missing++)) || true
    fi
  done

  echo ""
  echo -e "  ${GREEN}Present: $present${RESET}  ${AMBER}Stubs: $stub${RESET}  ${RED}Missing: $missing${RESET}"

  if [[ $((stub + missing)) -gt 0 ]]; then
    echo ""
    info "Run '$0 apply $dir' to generate missing files."
  fi
}

# =============================================================================
# MAIN
# =============================================================================
MODE="${1:-}"
case "$MODE" in
  new)       mode_new ;;
  apply)     mode_apply "${2:-}" ;;
  checklist) mode_checklist "${2:-}" ;;
  *)
    echo ""
    echo -e "${BOLD}iOPEX Project Scaffold${RESET}"
    echo ""
    echo "Usage:"
    echo "  $0 new                  Interactive new project"
    echo "  $0 apply <dir>          Apply scaffold to existing project"
    echo "  $0 checklist <dir>      Check scaffold status"
    echo ""
    exit 1
    ;;
esac

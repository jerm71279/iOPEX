#!/usr/bin/env bash
# ═══════════════════════════════════════════════════════════════════
# sync-repos.sh — Safe sync from working control center to private repo
#
# Syncs pam-migration-control-center/ → pam-migration-control-center/
# (same path — private repo IS the iOPEX directory)
#
# PUBLIC repo:  jerm71279/pam-control-center  → pam-migration-control-center/
# PRIVATE repo: jerm71279/iOPEX               → /home/maverick/projects/iOPEX/
#
# SAFETY: Validates .git integrity before and after every operation.
# ═══════════════════════════════════════════════════════════════════
set -euo pipefail

IOPEX_DIR="/home/maverick/projects/iOPEX"
PUBLIC_DIR="$IOPEX_DIR/pam-migration-control-center"
GIT_DIR="$IOPEX_DIR/.git"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# ── Pre-flight: Validate .git exists ──────────────────────────────
preflight() {
    echo -e "${YELLOW}[PREFLIGHT]${NC} Checking .git integrity..."

    if [ ! -d "$GIT_DIR" ]; then
        echo -e "${RED}[ABORT]${NC} $GIT_DIR is MISSING!"
        echo "  The private repo .git directory does not exist."
        echo "  Run: cd /tmp && git clone https://github.com/jerm71279/iOPEX.git iOPEX-clone"
        echo "  Then: cp -a /tmp/iOPEX-clone/.git $GIT_DIR"
        exit 1
    fi

    if [ ! -f "$GIT_DIR/HEAD" ]; then
        echo -e "${RED}[ABORT]${NC} $GIT_DIR/HEAD is missing — .git is corrupted!"
        exit 1
    fi

    # Verify remote points to the right repo
    local remote
    remote=$(cd "$IOPEX_DIR" && git remote get-url origin 2>/dev/null || echo "NONE")
    if [[ "$remote" != *"jerm71279/iOPEX"* ]]; then
        echo -e "${RED}[ABORT]${NC} Remote origin is '$remote' — expected jerm71279/iOPEX"
        exit 1
    fi

    echo -e "${GREEN}[OK]${NC} .git intact, remote: $remote"
}

# ── Post-flight: Verify .git survived ────────────────────────────
postflight() {
    if [ ! -d "$GIT_DIR" ] || [ ! -f "$GIT_DIR/HEAD" ]; then
        echo -e "${RED}[CRITICAL]${NC} .git was DESTROYED during operation!"
        echo "  Restoring from backup..."
        if [ -d "$GIT_DIR.bak" ]; then
            cp -a "$GIT_DIR.bak" "$GIT_DIR"
            echo -e "${GREEN}[RESTORED]${NC} .git recovered from backup"
        else
            echo -e "${RED}[FATAL]${NC} No backup found. Manual recovery needed."
            echo "  Run: cd /tmp && git clone https://github.com/jerm71279/iOPEX.git iOPEX-clone"
            echo "  Then: cp -a /tmp/iOPEX-clone/.git $GIT_DIR"
            exit 1
        fi
    fi
    echo -e "${GREEN}[POSTFLIGHT]${NC} .git integrity confirmed"
}

# ── Backup .git before risky operations ──────────────────────────
backup_git() {
    echo -e "${YELLOW}[BACKUP]${NC} Creating .git backup..."
    cp -a "$GIT_DIR" "$GIT_DIR.bak"
    echo -e "${GREEN}[OK]${NC} Backup at $GIT_DIR.bak"
}

# ── Status: Show both repos ──────────────────────────────────────
status() {
    preflight
    echo ""
    echo -e "${YELLOW}=== PRIVATE REPO (iOPEX) ===${NC}"
    cd "$IOPEX_DIR" && git log --oneline -3
    echo ""
    echo -e "${YELLOW}=== PUBLIC REPO (pam-control-center) ===${NC}"
    cd "$PUBLIC_DIR" && git log --oneline -3
    echo ""
    echo -e "${YELLOW}=== WORKING TREE ===${NC}"
    cd "$IOPEX_DIR" && git status --short pam-migration-control-center/ | head -10
    local count
    count=$(git status --short pam-migration-control-center/ | wc -l)
    if [ "$count" -gt 10 ]; then
        echo "  ... and $((count - 10)) more"
    fi
    if [ "$count" -eq 0 ]; then
        echo -e "  ${GREEN}Clean — no pending changes${NC}"
    fi
}

# ── Push: Commit and push both repos ─────────────────────────────
push() {
    preflight
    local msg="${1:-Sync control center updates}"

    echo ""
    echo -e "${YELLOW}[PUSH]${NC} Committing to both repos..."

    # Public repo
    echo -e "${YELLOW}--- PUBLIC ---${NC}"
    cd "$PUBLIC_DIR"
    if git diff --quiet && git diff --cached --quiet && [ -z "$(git ls-files --others --exclude-standard)" ]; then
        echo -e "  ${GREEN}Nothing to commit${NC}"
    else
        git add -A
        git commit -m "$msg"
        git push origin main
        echo -e "  ${GREEN}Pushed to pam-control-center${NC}"
    fi

    # Private repo
    echo -e "${YELLOW}--- PRIVATE ---${NC}"
    cd "$IOPEX_DIR"
    if git diff --quiet -- pam-migration-control-center/ && git diff --cached --quiet -- pam-migration-control-center/ && [ -z "$(git ls-files --others --exclude-standard -- pam-migration-control-center/)" ]; then
        echo -e "  ${GREEN}Nothing to commit${NC}"
    else
        git add pam-migration-control-center/
        git commit -m "$msg"
        git push origin main
        echo -e "  ${GREEN}Pushed to iOPEX${NC}"
    fi

    postflight
    echo ""
    echo -e "${GREEN}[DONE]${NC} Both repos synced"
}

# ── Main ─────────────────────────────────────────────────────────
case "${1:-status}" in
    preflight) preflight ;;
    status)    status ;;
    push)      push "${2:-Sync control center updates}" ;;
    backup)    backup_git ;;
    *)
        echo "Usage: $0 {preflight|status|push \"commit msg\"|backup}"
        echo ""
        echo "  preflight  — Check .git integrity"
        echo "  status     — Show both repos + pending changes"
        echo "  push       — Commit and push both repos"
        echo "  backup     — Backup .git directory"
        ;;
esac

#!/usr/bin/env bash
# Master Prompt — Claude CLI installer for WSL2 / Linux / Mac

set -e

BOLD="\033[1m"
BLUE="\033[34m"
GREEN="\033[32m"
RED="\033[31m"
RESET="\033[0m"

echo -e "${BLUE}${BOLD}"
echo "  ┌─────────────────────────────────────────┐"
echo "  │   Master Prompt — Claude CLI Installer  │"
echo "  │   JIT Technologies LLC │"
echo "  └─────────────────────────────────────────┘"
echo -e "${RESET}"

# ── 1. Node.js ──────────────────────────────────────────────────────────────
echo -e "${BOLD}[1/4] Checking Node.js...${RESET}"
if command -v node &>/dev/null; then
  NODE_VER=$(node -v)
  echo -e "  ${GREEN}✓ Node.js $NODE_VER found${RESET}"
else
  echo "  Node.js not found. Installing via nvm..."
  curl -fsSL https://raw.githubusercontent.com/nvm-sh/nvm/v0.39.7/install.sh | bash
  export NVM_DIR="$HOME/.nvm"
  source "$NVM_DIR/nvm.sh"
  nvm install --lts
  echo -e "  ${GREEN}✓ Node.js installed${RESET}"
fi

# ── 2. Claude CLI ───────────────────────────────────────────────────────────
echo -e "${BOLD}[2/4] Installing Claude CLI...${RESET}"
npm install -g @anthropic-ai/claude-code
echo -e "  ${GREEN}✓ Claude CLI installed${RESET}"

# ── 3. Scaffold command ─────────────────────────────────────────────────────
echo -e "${BOLD}[3/4] Installing /scaffold command...${RESET}"
mkdir -p ~/.claude/commands
cp "$(dirname "$0")/SCAFFOLD-ONBOARDING-PROMPT.md" ~/.claude/commands/scaffold.md
echo -e "  ${GREEN}✓ /scaffold command ready${RESET}"

# ── 4. API Key ──────────────────────────────────────────────────────────────
echo -e "${BOLD}[4/4] Anthropic API Key${RESET}"
if [ -z "$ANTHROPIC_API_KEY" ]; then
  echo -e "  ${RED}⚠  ANTHROPIC_API_KEY is not set.${RESET}"
  echo "  Get your key at: https://console.anthropic.com"
  echo "  Then add to your shell:"
  echo '  echo '"'"'export ANTHROPIC_API_KEY="sk-ant-..."'"'"' >> ~/.bashrc && source ~/.bashrc'
else
  echo -e "  ${GREEN}✓ ANTHROPIC_API_KEY found${RESET}"
fi

# ── Done ────────────────────────────────────────────────────────────────────
echo ""
echo -e "${GREEN}${BOLD}Setup complete.${RESET}"
echo ""
echo "  Next steps:"
echo "  1. cd into any project folder"
echo "  2. Run: claude"
echo "  3. Type: /scaffold"
echo ""

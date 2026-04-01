# Master Prompt — AI Project Starter

> Get Claude CLI installed and your first AI-powered project scaffolded in under 5 minutes.

---

## What's in Here

| File | Purpose |
|------|---------|
| `SCAFFOLD-ONBOARDING-PROMPT.md` | The master prompt — paste into any AI to scaffold a new project |
| `AGENTS.md` | Template for defining AI agent rosters |
| `ARCHITECTURE.md` | Template for system architecture docs |
| `CLAUDE.md` | Template for Claude Code project context |
| `MAVERICK_CONTEXT.md` | Template for internal project context |
| `docs/DEPLOYMENT.md` | Template for deployment guides |
| `Claude_Code_WSL_Setup.docx` | Full WSL2 + Claude CLI setup guide (Windows) |

---

## Quickstart

### Option A — Windows (WSL2) or Linux/Mac

```bash
# 1. Clone this repo
git clone https://github.com/jerm71279/Master-Prompt.git
cd Master-Prompt

# 2. Run the install script
chmod +x install.sh && ./install.sh
```

### Option B — Windows (PowerShell)

```powershell
# 1. Clone this repo
git clone https://github.com/jerm71279/Master-Prompt.git
cd Master-Prompt

# 2. Run the install script
./install.ps1
```

### Option C — No install (any AI platform)

Copy the contents of `SCAFFOLD-ONBOARDING-PROMPT.md` and paste directly into:
- Claude.ai, ChatGPT, Gemini, or any AI chat
- A Custom GPT or Claude Project as system instructions

---

## What the Install Script Does

1. Checks for Node.js (installs if missing)
2. Installs Claude CLI (`claude`) globally via npm
3. Copies `/scaffold` as a slash command into Claude Code
4. Prints next steps

After install, open a terminal in any project folder and run:

```bash
claude
```

Then type `/scaffold` to start the guided project onboarding.

---

## The `/scaffold` Flow

When you run `/scaffold`, Claude will:

1. **Phase 0** — Ask for any existing docs, SOWs, or specs to read first
2. **Phase 1** — Interview you using the CRISP-E framework (Context, Role, Instructions, Specification, Performance, Examples)
3. **Phases 2–7** — Collect architecture, agents, environment, spells, IP, and milestones
4. **Phase 8** — Generate a fully populated project scaffold (README, CLAUDE.md, ARCHITECTURE.md, AGENTS.md, and more)
5. **Phase 8.5** — Optional Draft-to-Genius 3-round polish pass

---

## Requirements

| Tool | Version | Notes |
|------|---------|-------|
| Node.js | 18+ | Required for Claude CLI |
| Claude CLI | latest | Installed by the script |
| Anthropic API Key | — | Get one at console.anthropic.com |

---

*Proprietary. © JIT Technologies LLC.*

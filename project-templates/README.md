# iOPEX Project Templates

Scaffold system for all iOPEX projects. Ensures every project has consistent documentation,
IP notices, and structure from day one.

---

## Quick Start

### New project from scratch
```bash
./project-templates/new-project.sh new
```

### Apply scaffold to an existing project
```bash
./project-templates/new-project.sh apply bt-autonomous-healing/
```

### Check what's missing in an existing project
```bash
./project-templates/new-project.sh checklist digital-expert/
```

---

## What Gets Generated

| File | Purpose |
|------|---------|
| `CLAUDE.md` | Full project context for Claude Code |
| `README.md` | Public-facing project overview |
| `ARCHITECTURE.md` | System design, component map, data flow |
| `AGENTS.md` | AI agent roster and responsibilities |
| `MAVERICK_CONTEXT.md` | Internal context (Jeremy / Claude Code only — not for clients) |
| `CHANGELOG.md` | Version history |
| `CONTRIBUTING.md` | IP notice + dev guidelines |
| `LICENSE` | Proprietary — JIT Technologies LLC |
| `NOTICE.md` | Copyright + ownership table |
| `Makefile` | Standard make targets (run, test, deploy, lint) |
| `render.yaml` | Render.com static site config |
| `pyproject.toml` | Python project config (Python projects only) |
| `docs/DEPLOYMENT.md` | Deployment instructions |
| `prompts/spells/` | Reusable Claude Code spell commands |
| `CHECKLIST.md` | Auto-generated list of remaining manual steps |

---

## `apply` Mode — How Retroactive Detection Works

When you run `apply` on an existing project, the script:

1. Reads `CLAUDE.md` and `README.md` to extract the description
2. Detects language from file extensions (`*.py` → python, `package.json` → node, etc.)
3. Detects framework from imports (`fastapi`, `langgraph`, `spring`, etc.)
4. Detects database from imports and `docker-compose.yml`
5. Detects deploy target from `render.yaml` or `Dockerfile`
6. Reads git remote to find the GitHub repo name
7. **Skips any file that already exists** — never overwrites
8. Generates `CHECKLIST.md` listing remaining `[[PLACEHOLDER]]` tokens

---

## IP Model

All code generated using these templates is the exclusive property of **JIT Technologies LLC**.
Clients purchase service outcomes, not code. See `scaffold/LICENSE` for full terms.

White label rights require a separate White Label License Agreement.

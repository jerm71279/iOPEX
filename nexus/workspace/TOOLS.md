# TOOLS.md - iOPEX Stack

## Delivery Channels
| Tool | Detail |
|------|--------|
| Telegram Bot | @iOPEXpert_Bot — Nexus + PMO Brain merged. `/pmo` activates PMO mode. Token: TELEGRAM_BOT_TOKEN_IOPEX |
| HeyGen Avatar | Avatar ID: 947bea007e7b40abad1d19f9f44b438d |
| HeyGen Voice | Voice ID: cce9cb863a5440e1a09a55bc0202f9c8 (Jeremy_heygen_upload) |
| HeyGen API | Funded — $10 API credit balance |

Note: @SHIFT_PMObot is dormant. Token preserved in openclaw.json but bot is not active.
PMO runs via `/pmo` command in @iOPEXpert_Bot → routed through `nexus-core run pmo`.
shift-pmo.sh and wave-ready.sh are retired — nexus-core pmo.py runner replaces both.

## nexus-core
- Location: `~/projects/nexus-core`
- PMO runner: `nexus-core run pmo --subcommand <directive|status|wave|escalate|ask>`
- SHIFT runner: `nexus-core run pmo --subcommand shift --phase P1 --dry-run`
- Output dir: `/tmp/shift-pmo/`

## Backend Services
| Service | Location | Purpose |
|---------|----------|---------|
| FastAPI | localhost:8001 | Webhook receiver + agent API |
| PostgreSQL | localhost:5432/iopex_expert | pgvector knowledge base |
| Redis | localhost:6379 | HeyGen callbacks, video prefs, LangGraph checkpoints |
| ngrok | historically-empirical-peter.ngrok-free.dev | HeyGen webhook tunnel (local dev) |

## LangGraph Agent
- Confidence threshold: 0.55
- Below threshold: Tavily web augmentation (C-08 sanitized)
- Domains: pam, zerotrust, network, secops, cloud, ai
- Embeddings: BAAI/bge-small-en-v1.5 (384-dim, CPU-only)

## PAM Control Center
- URL: https://pam-control-center.onrender.com
- API base: https://pam-control-center.onrender.com/api/pmo/

## GitHub
- Account: jerm71279
- Repos: iOPEX (private), pam-control-center (public), iopex-digital-expert

## SSH
| Alias | Host | Port | User | Purpose |
|-------|------|------|------|---------|
| hostinger | 147.93.42.92 | 65002 | u280943813 | CCNA app hosting (not suitable for bot) |

## Start / Stop
```bash
cd /home/maverick/projects/iOPEX/digital-expert
./start.sh          # start API + bot + watcher
pkill -f "uvicorn|run.py|watcher.py"   # stop all
```

## Logs
```
/tmp/iopex-api.log      FastAPI webhook server
/tmp/iopex-bot.log      Telegram bot
/tmp/iopex-watcher.log  File watcher / auto-ingest
```

## iOPEX Project Directory
```
/home/maverick/projects/iOPEX/
```
Poll this directory during heartbeats to detect new project folders.

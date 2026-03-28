# PAM Migration Control Center (SHIFT)

Real-time migration orchestration dashboard and AI-backed PMO layer for CyberArk migrations.
This is the **template for all iOPEX demo apps** — do not reference it in client-facing content.

## Stack
- **Frontend**: Vanilla JS SPA (`frontend/`) — no build step required
- **Backend**: FastAPI + Python (`backend/`)
- **ML**: LightGBM NHI classifier + Isolation Forest anomaly detection
- **MCP Servers**: (`mcp-servers/`) — tool integrations for AI agents
- **Deployment**: Docker Compose + Render (`render.yaml`)
- **Repos**: `jerm71279/pam-control-center` (public) + `jerm71279/iOPEX` (private, includes this)

## Key Files
```
frontend/
  index.html              Main dashboard SPA
  js/app.js               Dashboard logic, gate controls, agent cards
  js/guide.js             Security Q&A, risk tables, deep-dive content
  js/securityqa.js        Security Q&A module
backend/
  main.py                 FastAPI app
  requirements.txt        fastapi, uvicorn, scikit-learn, lightgbm, numpy, joblib
mcp-servers/              MCP tool servers for agent integrations
docker-compose.yml        Local dev stack
render.yaml               Render.com deployment config
```

## Run Commands
```bash
# Frontend only (no build needed)
cd frontend && python3 -m http.server 8080

# Full stack
docker-compose up

# Backend only
cd backend && pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

## Dashboard Features
- Wave execution tracker (5 waves, 15 agents)
- Gate approval controls (Yellow Checkpoint gates)
- NHI classifier (LightGBM — ML confidence scoring)
- Anomaly detection (Isolation Forest)
- Security Q&A deep-dive module
- Agent output viewer

## Git Push Workflow
This project lives in TWO repos simultaneously. Always push both:
```bash
# Option A: Use sync script (from /home/maverick/projects/iOPEX/)
./sync-repos.sh push "commit message"

# Option B: Manual
cd pam-migration-control-center && git add ... && git commit && git push
cd /home/maverick/projects/iOPEX && git add pam-migration-control-center/ && git commit && git push
```

## Environment Variables
See `.env` — backend is mostly self-contained; env vars needed for ML model paths and API integrations.

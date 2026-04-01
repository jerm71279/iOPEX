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

## CRISP-E Persona

> **C (Context):** iOPEX is executing a live CyberArk PAS → KeeperPAM migration for an enterprise client. The Control Center is the client-facing PMO dashboard and the internal AI orchestration layer. It is also the template for all iOPEX demo apps — never reference its internals in client content.
> **R (Role):** You are the SHIFT PAM Migration Control Center — the single pane of glass for migration progress, gate approvals, ML anomaly scores, agent status, and compliance evidence. You bridge the delivery team and the client stakeholder in real time.
> **I (Intent):** Make the migration feel controlled, auditable, and professional. Surface the right data at the right gate. Enable stakeholder decisions without context-switching. Flag anomalies before they become incidents. Keep the demo always client-ready.
> **S (Scope):** Dashboard and orchestration control layer only. The 15-agent orchestrators execute migrations; this system displays and controls their state via MCP servers. Live target: CyberArk → KeeperPAM. Option A/B shown for comparison only.
> **P (Persona/Style):** Enterprise-grade, confident, data-driven. Every number has a source. No placeholder text visible in client view. State transitions are instant and visible. Designed to impress a CISO.
> **E (Examples):** "Approve gate G5" → cascading agent activation shown live on dashboard. "NHI score for svc-oracle-prod?" → LightGBM confidence + subtype returned. "Show wave 3 ETL anomalies" → Isolation Forest flags per step with explanation.

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

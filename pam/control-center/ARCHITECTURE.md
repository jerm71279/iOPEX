# PAM Migration Control Center — Architecture

## System Overview

FastAPI + Vanilla JS SPA providing real-time orchestration dashboard and PMO layer for the live CyberArk → KeeperPAM migration. Demo mode runs entirely on mock data with in-memory state. Production mode connects the data import engine to the KeeperPAM orchestrator output directory and replaces in-memory state with Redis/PostgreSQL persistence. Two MCP servers expose the system to AI agents. Two public repos: `jerm71279/pam-control-center` (public demo) and `jerm71279/iOPEX` (private, includes this).

---

## Component Map

```
pam/control-center/
│
├── frontend/                       Vanilla JS SPA — no build step
│   ├── index.html                  Main dashboard shell
│   └── js/
│       ├── app.js                  Core dashboard: wave tracker, gate controls, agent cards
│       ├── agents.js               Agent status cards + output viewer
│       ├── gates.js                Gate approval UI + cascading state display
│       ├── waves.js                Wave execution tracker (5 waves)
│       ├── ml.js                   ML scores display (NHI + ETL anomalies)
│       ├── compare.js              Option A / Option B / KeeperPAM comparison view
│       ├── guide.js                Deep-dive security content
│       ├── securityqa.js           Security Q&A module
│       ├── mcp.js                  MCP tool console
│       ├── mission.js              Mission/engagement overview
│       ├── phases.js               Phase timeline view
│       ├── renderers.js            Shared UI rendering utilities
│       ├── api.js                  Shared API client (relative URLs)
│       ├── accounts.js             Account list + NHI classification view
│       ├── yellow.js               Yellow Checkpoint gate module
│       └── (+ life-of-pam.html)   Standalone lifecycle animation
│
├── backend/
│   ├── app.py                      FastAPI app — 11 routers + data import + static files
│   ├── state.py                    In-memory state manager (⚠ replace with Redis for prod)
│   ├── ml_provider.py              LiveMLProvider — LightGBM + Isolation Forest inference
│   ├── routers/
│   │   ├── dashboard.py            /api/dashboard/stats — summary counts
│   │   ├── phases.py               /api/phases — phase list + status
│   │   ├── agents.py               /api/agents — agent list + status
│   │   ├── waves.py                /api/waves — wave progress
│   │   ├── gates.py                /api/gates + /api/gates/{id}/approve
│   │   ├── accounts.py             /api/accounts — account list + NHI scores
│   │   ├── checkpoints.py          /api/checkpoints — Yellow Checkpoint data
│   │   ├── deliverables.py         /api/deliverables — client deliverable list
│   │   ├── ml.py                   /api/ml — NHI classifications + ETL anomalies
│   │   ├── mcp.py                  /api/mcp — MCP server status + tool list
│   │   └── state.py                /api/state — snapshot, reset, advance
│   ├── mock_data/                  Default demo data (phases, agents, waves, gates, ML)
│   ├── ml/                         ML model code (LightGBM NHI + Isolation Forest ETL)
│   └── imported_data/              Runtime JSON overrides (persisted across restarts)
│
├── mcp-servers/
│   ├── pam-migration-mcp/          10-tool MCP server wrapping orchestrator pipeline
│   │   ├── server.py               FastMCP server, lifespan, crash recovery
│   │   ├── shared/                 config, credentials, state bridge, audit bridge, phase enforcer
│   │   ├── crash_recovery/         watchdog, frozen registry, signal handlers
│   │   └── tools/                  accounts, compliance, discovery, etl, migration, permissions,
│   │                               preflight, validation
│   └── control-center-mcp/         FastAPI proxy — exposes CC REST API as MCP tools
│
├── docs/                           Client-facing HTML deliverables (served at /docs)
├── docker-compose.yml              3-service stack: control-center + pam-migration-mcp + control-center-mcp
├── render.yaml                     Render.com deployment (web service, Docker, free plan)
└── Dockerfile                      Production container (FastAPI + frontend)
```

---

## Data Flow

```
DEMO MODE (current)
  Browser → frontend SPA → GET /api/* → FastAPI routers → mock_data/ (in-memory)
  Gate approval: POST /api/gates/{id}/approve → state.approve_gate() → cascading activation
  State resets to mid-migration snapshot on restart

PRODUCTION MODE (KeeperPAM go-live)
  KeeperPAM Orchestrator → output/                    ← real migration output
      ↓ (cron/webhook)
  POST /api/import/{data_type} → imported_data/       ← overrides mock data
      ↓
  FastAPI routers → real migration data               ← dashboard goes live

  Gate approvals:
  POST /api/gates/{id}/approve → state (Redis/PG) → cascading activation persisted

  ML Inference:
  GET /api/ml/classifications → LiveMLProvider → LightGBM on real account data
  GET /api/ml/anomalies → Isolation Forest on real ETL step metrics

  AI Agents (Claude / other):
  MCP client → pam-migration-mcp:8100 → orchestrator tools (preflight, discovery, ETL status)
  MCP client → control-center-mcp:8101 → dashboard tools (gate approve, state query)
```

---

## Key Interfaces

| Interface | Type | Direction | Notes |
|-----------|------|-----------|-------|
| Browser → SPA | HTTP | Inbound | `GET /` serves `index.html`; `/css`, `/js` static mounts |
| SPA → API | HTTP/JSON | Internal | Relative URLs via `api.js`; all endpoints under `/api/` |
| `POST /api/gates/{id}/approve` | HTTP/JSON | Inbound | Core gate control — triggers state cascade |
| `POST /api/import/{data_type}` | HTTP multipart | Inbound | Runtime mock override with real orchestrator data |
| `GET /api/ml/classifications` | HTTP/JSON | Inbound | LightGBM NHI scores or mock fallback |
| `GET /api/ml/anomalies` | HTTP/JSON | Inbound | Isolation Forest ETL anomaly scores |
| PAM Migration MCP | HTTP/SSE | Inbound (AI) | Port 8100; 10 tools; wraps orchestrator |
| Control Center MCP | HTTP/SSE | Inbound (AI) | Port 8101; proxies CC REST API |
| Shared volume `/app/output` | Docker volume | Internal | Bridges CC ↔ pam-migration-mcp ↔ orchestrator |
| `GET /api/dashboard/stats` | HTTP/JSON | Inbound | Health check path (Docker + Render) |

---

## Deployment Topology

```
LOCAL DEV
  docker-compose up
    control-center:8080     FastAPI + SPA
    pam-migration-mcp:8100  MCP server
    control-center-mcp:8101 MCP proxy
  shared-state volume bridges all three services

  Alt (frontend-only dev):
    cd frontend && python3 -m http.server 8080

PRODUCTION — Render.com (current)
  render.yaml: single web service, Docker runtime, free plan
  healthCheckPath: /api/dashboard/stats
  Secrets: Render env vars
  Note: rootDir commented out — assumes dedicated repo (jerm71279/pam-control-center)

PRODUCTION — Self-Hosted (KeeperPAM go-live)
  docker-compose up on engagement workstation or cloud VM
  Mount orchestrator output directory to shared-state volume
  Set CYBERARK_BASE_URL + Key Vault URI for live PVWA connectivity
  Add Redis service to docker-compose for persistent state

DUAL-REPO PUSH (always required)
  pam-control-center repo (public): push frontend + backend changes
  iOPEX repo (private): push same files as subdirectory
  Use: ./sync-repos.sh push "message" from iOPEX root
  ⚠ Path has changed: now pam/control-center/ (was pam-migration-control-center/)
  Update sync-repos.sh and render.yaml rootDir if using monorepo option
```

---

## Security Notes

- **No authentication (demo)**: All API endpoints are currently open. Add middleware before exposing to a real client environment.
- **Gate approval endpoint**: `POST /api/gates/{id}/approve` has no auth — anyone with network access can approve a gate. Add operator auth before production.
- **Import endpoint**: Accepts arbitrary JSON — add schema validation to prevent state corruption via malformed imports.
- **MCP transport**: HTTP/Streamable (not STDIO) — avoids NeighborJack vulnerability per mcp-servers/pam-migration-mcp/server.py comment.
- **Credentials (MCP)**: CyberArk PVWA credentials loaded via env vars or Azure Key Vault. Never hardcoded. See `shared/credential_loader.py`.
- **Public repo**: `jerm71279/pam-control-center` is public — ensure no credentials, internal hostnames, or client data are committed.
- **ML models**: Not sensitive, but model files should not be committed to public repo — load from mounted volume.

---

## Decision Log

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Frontend framework | Vanilla JS (no build) | Zero build toolchain = instant demo, no Node dependency, works offline |
| State management | In-memory (demo) → Redis/PG (prod) | In-memory is fast for demo; persistence is a known prod requirement |
| ML stack | LightGBM + Isolation Forest | Lightweight, no GPU required; fits on migration workstation; silent mock fallback |
| MCP transport | HTTP/Streamable (not STDIO) | Security: STDIO vulnerable to NeighborJack; HTTP allows network separation |
| Dual-repo | pam-control-center (public) + iOPEX (private) | Public demo for client credibility; private for IP protection |
| Mock data override | JSON import endpoints | Allows live data injection without code changes or restart |
| Docker Compose | 3 services + shared volume | Control Center + 2 MCP servers share orchestrator output via volume |
| Render.com | Free plan, Docker runtime | Zero-cost public demo hosting; swap for self-hosted on live engagement |
| Live target | KeeperPAM (Keeper Security) | Confirmed go-live target 2026-03-28; Option A/B retained as comparison |

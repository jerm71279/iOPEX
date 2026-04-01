# PAM Migration Control Center — Agent Roster

## Overview

The Control Center is composed of 7 functional service agents: a FastAPI backend, an in-memory state manager, an ML inference provider, two MCP servers, a data import engine, and the frontend SPA. Together they form the orchestration and visualization layer over the live KeeperPAM migration.

**Production Target:** CyberArk PAS on-prem → **KeeperPAM** (Keeper Security). Option A (Privilege Cloud) and Option B (Secret Server) are retained as reference/comparison paths in the dashboard.

**Red Team Risk (Phase 7.5):** The #1 risk is the in-memory state manager. All gate approvals, agent statuses, and wave progress are lost on server restart. In a live client engagement, a crash mid-gate-approval resets the dashboard to the mock snapshot, which could cause a stakeholder to approve the same gate twice or miss a completed milestone. Persistence is the critical production gap.

---

## Agents

| # | Agent | Alias | Role | Failure Mode | Remediation Script |
|---|-------|-------|------|--------------|--------------------|
| 1 | backend/app.py | Dispatcher | FastAPI — serves SPA, 11 REST API routers, data import endpoints | Import endpoint accepts any JSON — malformed data silently corrupts in-memory store | Validate JSON schema on import; add `Content-Type` enforcement; reject unknown keys |
| 2 | backend/state.py | Tracker | In-memory state manager — gate approvals, cascading agent activation, phase unlocks | **CRITICAL (PROD)**: State lost on restart — mid-engagement crash resets to mock snapshot | Replace with Redis or PostgreSQL persistence before go-live; `state.snapshot()` → persist on every write |
| 3 | backend/ml_provider.py | Scorer | LightGBM NHI classifier + Isolation Forest ETL anomaly detection — live inference or mock fallback | Model file missing on cold start → silent mock fallback; operators see ML data that isn't real | Add `ML_PROVIDER_MODE` env var (`live`/`mock`); log and surface fallback state clearly in `/api/ml/status` |
| 4 | mcp-servers/pam-migration-mcp/ | Bridge | 10-tool MCP server wrapping the 15-agent orchestrator pipeline; crash recovery + frozen account registry | MCP server starts before orchestrator state file exists → tools return empty results silently | Add startup dependency check: verify `output/state/migration_state.json` exists before accepting requests |
| 5 | mcp-servers/control-center-mcp/ | Proxy | FastAPI proxy MCP server — exposes Control Center REST API as MCP tools for AI agents | Proxied requests use hardcoded `http://control-center:8080` — fails in non-Docker environments | Make `CC_MCP_CONTROL_CENTER_URL` env var required; add connection health check on startup |
| 6 | backend/app.py `/api/import/` | Loader | JSON data import engine — overrides mock data at runtime without restart | Imported data persists in `imported_data/` but is not version-controlled — silent data drift between deployments | Add import manifest with timestamps; log all imports to audit trail; clear stale imports on deploy |
| 7 | frontend/ | Canvas | Vanilla JS SPA — wave tracker, gate approvals, agent cards, ML scores, Security Q&A | API base URL hardcoded to relative path — fails when frontend is served from a different origin | Confirm `api.js` uses relative URLs throughout; add CORS headers to FastAPI for external embedding |

---

## Agent Details

### Agent 1 — Dispatcher (FastAPI Backend)
**File:** `backend/app.py` | **Port:** 8080 (Docker) / 8000 (local)
Serves the frontend SPA as static files and mounts 11 API routers. Also handles the data import system (`/api/import/{data_type}`) which allows runtime override of mock data with real migration data. Loads previously imported data on startup from `backend/imported_data/`.

**Production checklist:**
- [ ] Add authentication middleware (currently unauthenticated)
- [ ] Rate-limit gate approval endpoints
- [ ] Add request logging for audit trail
- [ ] Confirm CORS settings for production domain

### Agent 2 — Tracker (State Manager)
**File:** `backend/state.py`
Manages mutable agent/wave/gate statuses. Gate approval triggers cascading activation via `GATE_PHASE_UNLOCKS` + `PHASE_AGENTS` maps. Default snapshot: P0–P2 complete, P3 active (mid-migration demo state).

**Production checklist:**
- [ ] Replace in-memory dict with Redis or PostgreSQL-backed state
- [ ] Add state write persistence: call `snapshot()` + persist on every `approve_gate()` / `advance_agent()`
- [ ] Add engagement ID scoping — one state per live client engagement
- [ ] Implement state history (append-only log of all transitions)

### Agent 3 — Scorer (ML Provider)
**File:** `backend/ml_provider.py` + `backend/ml/`
Two models: LightGBM NHI classifier (7 subtypes, confidence score) and Isolation Forest ETL anomaly detector (per-step anomaly scores for 5 waves). Falls back to static mock data if models fail to load. Fallback is silent unless checked via `/api/ml/status`.

**Production checklist:**
- [ ] Surface `ML_PROVIDER_MODE: live|mock` prominently in dashboard header
- [ ] Load models from mounted volume or Azure Blob (not baked into Docker image)
- [ ] Retrain models on real KeeperPAM migration data post-P1

### Agent 4 — Bridge (PAM Migration MCP Server)
**File:** `mcp-servers/pam-migration-mcp/server.py` | **Port:** 8100
10 MCP tools wrapping the migration orchestrator. Includes crash recovery (watchdog, frozen account registry, signal handlers), phase enforcement, and optional CyberArk PVWA integration. Reads orchestrator state from shared volume.

**Production checklist:**
- [ ] Set `PAM_MCP_CYBERARK_BASE_URL` for live PVWA connectivity
- [ ] Configure Azure Key Vault (`PAM_MCP_KEY_VAULT_URI`) for credential loading
- [ ] Set `PAM_MCP_MIGRATION_OPTION=keeper` once KeeperPAM orchestrator path is available
- [ ] Verify watchdog timer is appropriate for KeeperPAM ETL batch sizes
- [ ] Test frozen account registry recovery path before P4

### Agent 5 — Proxy (Control Center MCP Server)
**File:** `mcp-servers/control-center-mcp/server.py` | **Port:** 8101
Wraps the Control Center REST API as MCP tools for AI agent consumption. Allows Claude/other AI to query migration state, approve gates, and retrieve ML scores programmatically.

**Production checklist:**
- [ ] Set `CC_MCP_CONTROL_CENTER_URL` to production Control Center URL
- [ ] Add authentication token forwarding if API auth is enabled
- [ ] Test tool schemas against Claude tool use format

### Agent 6 — Loader (Data Import Engine)
**File:** `backend/app.py` `/api/import/` routes
Accepts JSON uploads for: phases, agents, waves, gates, deliverables, discovery, heartbeat, staging. Writes to `backend/imported_data/` and applies to in-memory store. Persists across restarts.

**Production checklist:**
- [ ] Wire real KeeperPAM migration output (phases, agents, waves) to import endpoints
- [ ] Add schema validation per data_type
- [ ] Automate import from orchestrator output directory (cron or webhook)

### Agent 7 — Canvas (Frontend SPA)
**File:** `frontend/` — no build step
Vanilla JS SPA with modules: app.js (dashboard), agents.js (agent cards), gates.js (approvals), waves.js (wave tracker), ml.js (ML scores), guide.js + securityqa.js (Security Q&A), mcp.js (MCP tool console), compare.js (Option A vs B vs KeeperPAM).

**Production checklist:**
- [ ] Update `compare.js` to show KeeperPAM as the live path (not just Option A/B comparison)
- [ ] Remove any visible mock data labels from client-facing views
- [ ] Confirm all API calls use relative paths (not localhost)
- [ ] Test on mobile viewport for client presentations

---

## Orchestration

The Control Center does not orchestrate the migration directly. It reflects and controls the state of the 15-agent orchestrators via:
1. **Import endpoints** — real migration data replaces mock data at runtime
2. **State manager** — gate approvals trigger cascading agent/phase activation visible on dashboard
3. **MCP Bridge** — AI agents can query and control the orchestrator via MCP tools

For KeeperPAM go-live: the orchestrator output directory is mounted as a shared volume. The data import engine polls or webhooks from that directory to keep the dashboard current.

---

## Status

| Agent | Status | Last Action |
|-------|--------|-------------|
| 1 Dispatcher | production-ready (demo) | Auth + rate limiting needed for go-live |
| 2 Tracker ⚠ | **NOT production-ready** | In-memory only — persistence required before go-live |
| 3 Scorer | production-ready (mock fallback) | Retrain on KeeperPAM data post-P1 |
| 4 Bridge ⚠ | staging-ready | KeeperPAM path + Azure Key Vault config needed |
| 5 Proxy | staging-ready | Production URL + auth forwarding needed |
| 6 Loader | production-ready | Schema validation + automation needed |
| 7 Canvas | production-ready (demo) | compare.js KeeperPAM update + mobile test needed |

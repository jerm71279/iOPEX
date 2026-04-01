# PAM Migration Control Center — Maverick Context

> Internal-only. Not for client distribution.
> Provides Jeremy / Claude Code with full project context for AI-assisted development.

---

## Project Identity

| Field | Value |
|-------|-------|
| Project | PAM Migration Control Center (SHIFT) |
| Customer | iOPEX / live KeeperPAM engagement client |
| Status | active — demo complete, production prep in progress |
| Started | 2026-03-28 |
| Live Target | CyberArk PAS on-prem → **KeeperPAM (Keeper Security)** |
| Owner | JIT Technologies LLC |
| Primary Contact | Jeremy Smith (jerm712@icloud.com) |
| Public Repo | `jerm71279/pam-control-center` |
| Private Repo | `jerm71279/iOPEX` (includes this as `pam/control-center/`) |

---

## Why This Exists

iOPEX clients need a single PMO dashboard to track a PAM migration that runs for 50–80 weeks across 15 agents, 5 waves, and 15+ gate approvals. Without a control center, the delivery team is managing state in spreadsheets and the client has no real-time visibility. SHIFT closes that gap — it makes the migration visible, controlled, and audit-ready. It also serves as the internal template for every future iOPEX demo app.

---

## What Has Been Built

**Demo layer (~95% complete):**
- FastAPI backend with 11 REST API routers (phases, agents, waves, gates, accounts, ML, MCP, state, deliverables, checkpoints, import)
- Vanilla JS SPA: wave tracker, gate approval controls, agent cards, ML scores, Security Q&A, MCP console, lifecycle animation
- In-memory state manager with cascading gate approval → agent activation
- LightGBM NHI classifier + Isolation Forest ETL anomaly detector (with mock fallback)
- JSON data import engine — runtime override of mock data without restart
- PAM Migration MCP Server (10 tools, crash recovery, frozen account registry, phase enforcer)
- Control Center MCP Server (FastAPI proxy for AI agent consumption)
- Docker Compose 3-service stack (CC + 2 MCP servers + shared volume)
- Render.com deployment config
- Client-facing HTML deliverables served at `/docs`

**Gate approval:** Wired. `POST /api/gates/{id}/approve` → cascading state transition works.

---

## What Is In Progress

### Production Gaps (required before KeeperPAM go-live)

| Priority | Item | File | Effort |
|----------|------|------|--------|
| P0 — BLOCKER | Persistent state (Redis/PG) | `backend/state.py` | Medium |
| P0 — BLOCKER | API authentication middleware | `backend/app.py` | Small |
| P1 | KeeperPAM orchestrator path in MCP | `mcp-servers/pam-migration-mcp/shared/config.py` | Small |
| P1 | Azure Key Vault credential loading | `mcp-servers/pam-migration-mcp/shared/credential_loader.py` | Small |
| P1 | Import automation (orchestrator → dashboard) | `backend/app.py` | Medium |
| P2 | compare.js KeeperPAM as live path | `frontend/js/compare.js` | Small |
| P2 | ML model retraining on real data | `backend/ml/` | Medium (post-P1) |
| P2 | Mobile viewport QA | `frontend/` | Small |
| P3 | sync-repos.sh path update | `./sync-repos.sh` | Small |
| P3 | render.yaml rootDir update | `render.yaml` | Small |

---

## Known Issues / Blockers

- **State not persisted (BLOCKER):** All gate approvals and agent status changes are lost on restart. In a live engagement, a server crash resets the dashboard to the mid-migration mock snapshot. Must be fixed before P4 of the live migration.
- **No API auth:** Gate approval endpoint is open. In a live client environment this means anyone on the network can approve a gate. Add JWT or API key middleware.
- **Dual-repo path changed:** `pam-migration-control-center/` was renamed to `pam/control-center/`. The `sync-repos.sh` script and `render.yaml` rootDir option reference the old path. Update before next push to the public repo.
- **ML mock fallback is silent:** If models fail to load, `/api/ml/status` returns mock data without a clear visual indicator in the dashboard. Operators may not notice they're looking at synthetic data.
- **MCP server KeeperPAM path:** `PAM_MCP_MIGRATION_OPTION` currently supports `a` or `b`. Needs a `keeper` option with the KeeperPAM orchestrator path once that orchestrator is built.
- **KeeperPAM audit log continuity (undocumented):** CyberArk audit logs do NOT automatically transfer to KeeperPAM. This is documented for Option B (Secret Server) but not for the KeeperPAM live path. Before P5, confirm compliance retention requirements and keep CyberArk read-only for the required retention period. Add to Agent 07 compliance report scope.
- **Azure security pre-checks (gates g5 + g6):** Added `azure_checks` arrays to g5 (Structure Approval) and g6 (Pilot Results Approval) covering Key Vault credential verification, managed identity role assignment, Conditional Access exemption (if applicable), SOC notification window, SIEM connector handoff, and break-glass account sequencing. These are conditional — only enforce items that apply to the client's Azure environment. See pre-engagement questionnaire.

---

## Key Decisions Made

- **KeeperPAM is the live target (confirmed 2026-03-28):** Option A (Privilege Cloud) and Option B (Secret Server) are retained in the dashboard as comparison views only. All production wiring should target KeeperPAM.
- **Demo-first architecture:** In-memory state + mock data allowed fast iteration. The import engine is the bridge to production — no code changes required to go live, only data.
- **No build toolchain for frontend:** Vanilla JS + no bundler = zero setup friction. Client can open `index.html` directly. Deliberate choice for demo portability.
- **Two public repos:** `pam-control-center` (public, client-presentable) + `iOPEX` (private, full codebase). Public repo never receives credentials or internal architecture details.
- **Template for all iOPEX demo apps:** The frontend structure, API pattern, and Docker setup are the reference implementation for every future iOPEX demo. Never break this pattern without updating the template standard.

---

## Client Context

The Control Center is the primary client-facing touchpoint for the KeeperPAM migration engagement. The client stakeholder (likely a CISO or IT Director) sees this dashboard, not the agent code. It must be polished, data-accurate, and always operational during the engagement.

Client deliverables live in `docs/` and are accessible at `/docs` on the deployed instance. These are the HTML visualization files (migration lifecycle, AI orchestration, proposal bundle).

Do NOT share: `backend/state.py` internals, MCP server code, ML model weights, or mock data structure with the client. These are iOPEX IP.

---

## IP Notes

All code in this project is the exclusive property of JIT Technologies LLC.
The client has purchased the service outcome (migration + dashboard access), not the code.
Do not share source code, agent logic, or system architecture beyond what is
explicitly covered in the Statement of Work.

White label rights require a separate White Label License Agreement.

---

## Useful Commands

```bash
# Full stack (recommended)
docker-compose up

# Frontend only (for rapid UI dev)
cd frontend && python3 -m http.server 8080

# Backend only
cd backend && pip install -r requirements.txt
uvicorn app:app --reload --port 8000

# Check API health
curl http://localhost:8080/api/dashboard/stats

# Approve a gate (demo or production)
curl -X POST http://localhost:8080/api/gates/g5/approve

# Import real migration data (waves example)
curl -X POST http://localhost:8080/api/import/waves \
  -F "file=@/path/to/waves.json"

# Check import status
curl http://localhost:8080/api/import/status

# Clear an import and revert to mock
curl -X DELETE http://localhost:8080/api/import/waves

# State snapshot (debug)
curl http://localhost:8080/api/state/snapshot

# Reset to mid-migration demo snapshot
curl -X POST http://localhost:8080/api/state/reset

# Manually advance an agent (demo control)
curl -X POST "http://localhost:8080/api/state/advance-agent/4?status=active"

# Push to BOTH repos (always use this)
# ⚠ Update path in sync-repos.sh: pam-migration-control-center → pam/control-center
./sync-repos.sh push "your commit message"
```

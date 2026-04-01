# Changelog — Pam Migration Control Center

All notable changes to this project are documented here.
Format: [Version/Date] — Description

---

## [Unreleased]

### Added
- Azure pre-check arrays added to gates g5 (Structure Approval) and g6 (Pilot Results Approval) covering Key Vault credential verification, managed identity, CA policy exemption, SOC notification, SIEM handoff, and break-glass account sequencing
- KeeperPAM audit log continuity gap documented in MAVERICK_CONTEXT.md and ARCHITECTURE.md security notes

### Fixed
- `DELETE /api/import/{data_type}` now correctly reverts in-memory data store to original mock values (previously only deleted the file, left memory stale)
- `_load_imports_on_startup` now logs warnings instead of silently swallowing corrupt import files
- ML mock fallback is now surfaced — `/api/ml/status` returns `mock_fallback: true` + `inference: mock` when `LiveMLProvider` fails; dashboard ML badge shows amber MOCK with failure reason tooltip
- MCP server now fails fast at startup in non-dev environments when `PAM_MCP_KEY_VAULT_URI` is set but required credentials (`CYBERARK_USERNAME`, `CYBERARK_PASSWORD`) fail to load from Key Vault

## [2026-03-28] — Initial Build

### Added
- FastAPI backend with 11 REST API routers: dashboard, phases, agents, waves, gates, deliverables, accounts, checkpoints, MCP, ML, state
- Vanilla JS SPA: wave tracker, gate approval controls, agent cards, ML scores, Security Q&A, MCP console, lifecycle animation
- In-memory state manager (`backend/state.py`) with cascading gate approval → agent activation
- LightGBM NHI classifier + Isolation Forest ETL anomaly detector with mock fallback
- JSON data import engine — runtime override of mock data without restart
- PAM Migration MCP Server (10 tools, crash recovery, frozen account registry, phase enforcer)
- Control Center MCP Server (FastAPI proxy for AI agent consumption)
- Docker Compose 3-service stack (control-center + pam-migration-mcp + control-center-mcp + shared volume)
- Render.com deployment config (`render.yaml`)
- Client-facing HTML deliverables served at `/docs`
- Azure Key Vault credential loader (`shared/credential_loader.py`) using `DefaultAzureCredential`
- Mock data import system with startup reload from `backend/imported_data/`

---

## Notes

- Use ISO dates (YYYY-MM-DD)
- Prefix entries: Added / Changed / Fixed / Removed / Security

# CyberArk Migration — Maverick Context

> Internal-only. Not for client distribution.
> Provides Jeremy / Claude Code with full project context for AI-assisted development.

---

## Project Identity

| Field | Value |
|-------|-------|
| Project | CyberArk Migration — Option A (KeeperPAM) |
| Customer | iOPEX / end client (engagement-specific) |
| Status | active |
| Started | 2026-03-28 |
| Owner | JIT Technologies LLC |
| Primary Contact | Jeremy Smith (jerm712@icloud.com) |

---

## Why This Exists

iOPEX customers running CyberArk PAS on-premises face increasing pressure to migrate to KeeperPAM (SaaS). The migration is technically complex — 15+ migration domains, 22-permission mapping, NHI classification, dependency scanning, compliance evidence — and doing it manually risks data loss, downtime, and audit failure. This orchestrator automates the entire migration lifecycle, reducing a 6–12 month manual project to a supervised automated run.

---

## What Has Been Built

- 15-agent orchestrator covering all 8 migration phases (P0–P7)
- PVWA REST client (source) + KeeperPAM REST client (target) with OAuth2
- 7-step ETL pipeline with watchdog, emergency unfreeze, linked account support
- 22→22 permission mapping (1:1, no loss) via Safe Members API
- 3-signal NHI classifier (7 subtypes, weighted scoring, per-type strategies)
- 6-scanner dependency mapper (IIS, services, tasks, Jenkins, scripts, configs)
- 10-assertion staging validation with rollback
- CCP/AAM integration repointing (Python, Java, .NET, PowerShell, Bash)
- 4-framework compliance evidence (PCI-DSS, NIST 800-53, HIPAA, SOX)
- Multi-vendor source adapters (BeyondTrust, SS, HashiCorp, AWS, Azure, GCP)
- Atomic state machine with crash recovery and SHA-256 audit chain
- App onboarding factory (10-step pipeline)
- Hybrid fleet manager for P6 parallel running

---

## What Is In Progress

- Test environment decision pending (Lab Instance vs Mock API vs Hybrid — see README.md)
- Agent 08 approval timeout not yet enforced — runbook can hang indefinitely
- No Slack/email integration for human approval escalation
- `output/` report format standardization across all 15 agents
- Performance testing on large vaults (>50K accounts)

---

## Known Issues / Blockers

- **No test sandbox**: No dedicated CyberArk PVWA dev/lab or KeeperPAM test tenant. All testing requires production-like environment. See README.md for options.
- **Agent 08 timeout**: `APPROVAL_TIMEOUT_MIN` config key exists but not yet enforced in `agent_08_runbook.py` — add enforcement before P4.
- **Agent 04 kill risk**: If the migration process is killed (SIGKILL, OOM) mid-ETL, the watchdog thread also dies. Vault remains frozen. Recovery: restart coordinator, run `--emergency-unfreeze`.
- **PVWA SAML**: SAML auth not supported via API (requires browser). Customers using SAML-only SSO must create a service account with LDAP/Windows auth for migration.
- **Large vault performance**: Agents 01 and 04 not yet benchmarked above 50K accounts. Pagination and batch sizes may need tuning via `agent_config.json`.

---

## Key Decisions Made

- **Option A (KeeperPAM) vs Option B (Secret Server)**: This project is Option A. KeeperPAM preserves the 22-permission model 1:1 — no permission loss. Secret Server (Option B) collapses to 4 roles with lossy mapping.
- **Python 3.12+**: asyncpg for state I/O performance; match-case for agent result routing; type hints throughout.
- **No ORM for state**: Plain JSON + atomic file writes. Avoids DB dependency on migration workstation. Inspectable by humans mid-migration.
- **Watchdog as thread**: ETL watchdog runs in a separate thread so it fires even if the main pipeline hangs. Risk: SIGKILL kills both. Mitigation: systemd service with RestartSec.
- **SHA-256 audit chain**: Each log entry hashes previous entry — tamper-evident without a blockchain. SIEM-importable JSONL.

---

## Client Context

This codebase is the engine for iOPEX PAM migration engagements. Each client engagement uses the same orchestrator with a client-specific `config.json` (gitignored). Client deliverables are the migration output (reports, runbooks, compliance evidence) — not the orchestrator source code.

Do NOT share `coordinator.py`, agent logic, or `core/` internals with clients. The Statement of Work covers migration execution, not tool licensing. White label rights require a separate agreement.

---

## IP Notes

All code in this project is the exclusive property of JIT Technologies LLC.
The client has purchased the service outcome, not the code.
Do not share source code, agent logic, or system architecture beyond what is
explicitly covered in the Statement of Work.

White label rights require a separate White Label License Agreement.

---

## Useful Commands

```bash
# First-time setup
cp config.example.json config.json   # edit with real URLs + credentials
export CYBERARK_USERNAME="svc-migration"
export CYBERARK_PASSWORD="..."
export KEEPERPAM_CLIENT_ID="..."
export KEEPERPAM_CLIENT_SECRET="..."

# Verify connectivity before starting
python3 cli.py preflight

# Start a migration run
python3 cli.py start my-migration-001

# Run a phase (dry-run first)
python3 cli.py run P1 --dry-run
python3 cli.py run P1

# Check status
python3 cli.py status

# Advance to next phase (after human review)
python3 cli.py advance P1

# Run a specific agent
python3 cli.py agent 04

# Emergency: unfreeze vault if ETL left it frozen
python3 cli.py agent 04 --emergency-unfreeze

# View agent list
python3 cli.py agents
```

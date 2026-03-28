# Secret Server Migration — Maverick Context

> Internal-only. Not for client distribution.
> Provides Jeremy / Claude Code with full project context for AI-assisted development.

---

## Project Identity

| Field | Value |
|-------|-------|
| Project | Secret Server Migration — Option B (Delinea Secret Server) |
| Customer | iOPEX / end client (engagement-specific) |
| Status | active |
| Started | 2026-03-28 |
| Owner | JIT Technologies LLC |
| Primary Contact | Jeremy Smith (jerm712@icloud.com) |

---

## Why This Exists

Some iOPEX customers are migrating away from CyberArk entirely — choosing Delinea Secret Server for cost, licensing, or vendor preference reasons. This is the harder migration path: it's cross-vendor, the permission model is lossy, audit logs can't transfer, and every integration needs a full OAuth2 rewrite. Without orchestration, this project takes 9–18 months manually and produces significant compliance risk from undocumented permission changes. This orchestrator automates the full lifecycle and surfaces every compromise explicitly.

---

## What Has Been Built

- 15-agent orchestrator covering P0–P7 (same phase structure as Option A)
- PVWA REST client (source) + Secret Server REST client (target) with OAuth2 + proactive token refresh
- Lossy permission mapper (22→4 roles) with escalation detection and per-member loss report
- 7-step ETL: Safe→Folder, Platform→Template, Account→Secret; watchdog; emergency unfreeze
- SS heartbeat API + RPC plugin validation in Agent 05
- Full CCP/AAM → SS REST API + OAuth2 integration rewriter (Agent 06)
- SS-specific compliance risks documented: audit discontinuity (HIGH), permission collapse (HIGH), PSM loss (MEDIUM)
- Platform → Secret Template auto-mapping for 8 standard platforms (Agent 13)
- SS-specific onboarding pipeline: folders/templates/secrets (Agent 14)
- All agents shared with Option A where logic is identical (01, 05 base, 07 base, 08, 09, 10, 11, 12, 15)

---

## What Is In Progress

- Agent 08 approval timeout not yet enforced
- No Slack/email escalation for approval workflow
- RPC plugin rebuild guidance for custom templates (manual — not automated)
- Performance testing on large vaults (>50K accounts)
- `output/reports/risk_acceptances/` directory and signed risk acceptance workflow

---

## Known Issues / Blockers

- **No test sandbox**: No dedicated PVWA dev/lab or SS test instance. See README.md for test environment options.
- **Agent 03 escalation edge case**: Members with only one Edit-triggering permission (e.g., UnlockAccounts only) receive the full Edit role, which also grants Add/Delete/Update. Run `--strict-escalation` to flag these.
- **Agent 08 timeout**: Approval timeout not enforced — runbook can hang. Add before P4.
- **Custom platform templates**: Any platform not in the standard 8-mapping table requires manual SS template creation before ETL. Agent 02 flags these but doesn't auto-create.
- **Audit discontinuity**: CyberArk audit history ends at cutover date. Regulators may require a formal letter acknowledging the gap. Store in `output/reports/risk_acceptances/`.
- **PSM recording loss**: Document explicitly in compliance report before client signs off on P3.
- **Failed password retrieval**: Accounts where CyberArk password retrieval fails during ETL are skipped (not imported with empty secrets). These must be handled manually post-migration.

---

## Key Decisions Made

- **Option B vs Option A**: Chosen when the client wants to exit CyberArk entirely. Always present both options — Option A preserves the permission model 1:1 and is preferred when Privilege Cloud is viable.
- **Lossy permission mapping is documented, not hidden**: Agent 03 makes loss explicit in every report. The goal is informed consent before P3, not silent compromise.
- **No audit log transfer**: Transferring CyberArk audit logs to SS creates false provenance (events in SS that SS never generated). Archive CyberArk logs separately.
- **Full OAuth2 rewrite over shim**: A CCP→SS shim layer would carry forward CyberArk API patterns that don't map cleanly. Clean OAuth2 rewrite is safer and easier to maintain.
- **Skip failed password retrievals**: An account imported with an empty secret is worse than a missing account — it creates a false sense of coverage. Operators should know what's missing.

---

## Client Context

This codebase is the engine for iOPEX CyberArk→Secret Server migration engagements. Each engagement uses a client-specific `config.json` (gitignored). Client deliverables are migration output (reports, runbooks, compliance evidence, signed risk acceptances) — not the orchestrator source code.

The Agent 03 loss report is a client deliverable. The compliance evidence package (Agent 07) is a client deliverable. The orchestrator source code is not.

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
cp config.example.json config.json   # edit with real URLs
export CYBERARK_USERNAME="svc-migration"
export CYBERARK_PASSWORD="..."
export SS_CLIENT_ID="..."
export SS_CLIENT_SECRET="..."

# Verify connectivity
python3 cli.py preflight

# Start a migration run
python3 cli.py start my-migration-001

# Run a phase (dry-run first)
python3 cli.py run P1 --dry-run
python3 cli.py run P1

# Check status
python3 cli.py status

# Advance phase (gate validation required)
python3 cli.py advance P1

# Review Agent 03 loss report before P3
python3 cli.py agent 03 --report
python3 cli.py agent 03 --strict-escalation

# Emergency: unfreeze vault if ETL left it frozen
python3 cli.py agent 04 --emergency-unfreeze

# Run specific agent
python3 cli.py agent 13
```

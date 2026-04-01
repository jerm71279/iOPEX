# Secret Server Migration — Architecture

## System Overview

15-agent AI orchestrator for CyberArk PAS on-prem → Delinea Secret Server migration. Unlike Option A (Privilege Cloud), this is a cross-vendor migration with structural differences: Safes become Folders, Platforms become Secret Templates, and the 22-permission model is lossy-collapsed to 4 roles. Audit logs and PSM recordings cannot be transferred. All CCP/AAM integrations require full OAuth2 re-architecture targeting the SS REST API.

---

## Component Map

```
coordinator.py              Phase sequencer — agents run in order, AgentResult gates enforced
cli.py                      Entry point: preflight / start / run / advance / status / agent

core/
  base.py                   AgentBase ABC + AgentResult
  state.py                  MigrationState — atomic JSON writes, fcntl locking, .bak recovery
  logging.py                AuditLogger — SHA-256 hash chain, SIEM-ready JSONL
  cyberark_client.py        PVWA REST client (source)
  secret_server_client.py   SS REST client — OAuth2 + legacy, folders/secrets/templates
  source_adapters.py        7 vendor adapters

agents/
  agent_01_discovery.py     Scout      — safe/account/platform enumeration
  agent_02_gap_analysis.py  Analyst    — 10 domains + SS template readiness + permission risk
  agent_03_permissions.py   Mapper     — LOSSY 22→4 role mapping, escalation detection
  agent_04_etl.py           Mover      — 7-step ETL: Safe→Folder, Platform→Template, Account→Secret
  agent_05_heartbeat.py     Validator  — 10 checks + SS heartbeat API + RPC + audit continuity
  agent_06_integration.py   Rewirer    — CCP/AAM → SS REST API + OAuth2 full re-architecture
  agent_07_compliance.py    Auditor    — 4 frameworks + 3 SS-specific risks
  agent_08_runbook.py       Gatekeeper — phase gates + P3 loss report sign-off gate
  agent_09_dependency_mapper.py  Mapper — 6-scanner dependency graph
  agent_10_staging.py       Tester     — 10 assertions against SS staging instance
  agent_11_source_adapter.py     Importer — multi-vendor normalization
  agent_12_nhi_handler.py   Classifier — NHI classification, SS folder/template strategies
  agent_13_platform_plugins.py   Porter — CyberArk platform → SS Secret Template mapping
  agent_14_onboarding.py    Onboarder  — SS folders/templates/secrets onboarding pipeline
  agent_15_hybrid_fleet.py  Balancer   — hybrid CPM + SS RPC routing during P6

config.example.json         Connection template (never commit config.json)
agent_config.json           Thresholds + platform→template mapping table
output/                     Runtime (logs/, reports/, state/, state/raw/) — gitignored
```

---

## Data Flow

```
PHASE P1 — DISCOVERY
  PVWA API → Agent 01 (Scout) → raw inventory
           → Agent 09 (Mapper) → dependency graph
           → Agent 12 (Classifier) → NHI classifications (SS folder/template strategies)
           → Agent 11 (Importer) → normalize multi-vendor sources
           → Agent 02 (Analyst) → gap analysis + SS template readiness + permission risk score
           → Agent 03 (Mapper) → per-member loss report (22→4, escalation flags)
  ⚠ GATE: Loss report MUST be human-reviewed before advancing to P2

PHASE P2 — INFRASTRUCTURE
  → Agent 13 (Porter) → CyberArk platforms mapped to SS Secret Templates
                         custom templates auto-created where possible
                         unmapped platforms flagged for manual creation
  → Agent 10 (Tester) → 10 assertions against SS staging instance
  Gate: all assertions pass + human approval → advance to P3

PHASE P3 — FOLDER & TEMPLATE MIGRATION
  → Agent 03 (Mapper) re-run → folder hierarchy created in SS
                                per-safe child folders under "Imported" root
  → Agent 14 (Onboarder) → onboarding pipeline configured
  ⚠ HARD GATE: Agent 03 loss report sign-off required here

PHASE P4 — PILOT ETL
  → Agent 04 (Mover) → FREEZE → EXPORT → TRANSFORM →
                        FOLDER CREATION → IMPORT → HEARTBEAT → UNFREEZE
    Transform: userName→slug, address→machine, platformId→template,
               platformAccountProperties→notes
    Passwords: POST /Accounts/{id}/Password/Retrieve (skip on failure)
    Secrets: POST /api/v1/secrets with template ID + field items
  → Agent 05 (Validator) → 10 checks incl. SS heartbeat + RPC + audit trail start

PHASE P5 — PRODUCTION WAVES
  Waves 1–5: Agent 04 + 05 repeat
  → Agent 06 (Rewirer) → CCP/AAM → SS REST API + OAuth2 (full re-architecture)
  → Agent 14 (Onboarder) → new account onboarding to SS
  → Agent 07 (Auditor) → per-wave compliance evidence

PHASE P6 — PARALLEL RUNNING
  → Agent 15 (Balancer) → route CPM (on-prem) vs RPC (SS) per account
  → Agent 05 + 06 + 07 continuous

PHASE P7 — DECOMMISSION
  → Agent 07 (Auditor) → final report with audit discontinuity acknowledgment
```

---

## Key Interfaces

| Interface | Type | Direction | Notes |
|-----------|------|-----------|-------|
| PVWA REST API | HTTP/JSON | Outbound (source) | `/PasswordVault/api/`; LDAP/Windows auth |
| SS REST API | HTTP/JSON | Outbound (target) | `/api/v1/`; OAuth2 client_credentials |
| SS OAuth2 | HTTP/JSON | Outbound (auth) | `{ss_url}/oauth2/token`; proactive refresh 60s before expiry |
| CLI | stdin/stdout | Inbound | Human operator interface |
| State file | JSON/disk | Internal | Atomic writes, SHA-256 chain |
| Audit log | JSONL/disk | Internal | New SS audit trail starts at migration date; CyberArk logs archived separately |
| Vendor APIs | HTTP/JSON | Outbound (P1) | BeyondTrust, HashiCorp, AWS, Azure, GCP |

---

## Deployment Topology

```
LOCAL / ON-PREM EXECUTION
  Python 3.12+ on migration workstation with network access to:
    - Source PVWA: https://pvwa.company.com
    - Target SS:   https://secretserver.company.com
  Credentials: environment variables only
  Output: local ./output/ (gitignored)

NETWORK REQUIREMENTS
  Outbound 443: PVWA, Secret Server
  SS RPC: outbound to managed endpoints (for heartbeat/rotation validation)
```

---

## Security Notes

- **Credentials**: `CYBERARK_USERNAME`, `CYBERARK_PASSWORD`, `SS_CLIENT_ID`, `SS_CLIENT_SECRET` via env vars. Passwords zeroed after auth.
- **SS token refresh**: proactive re-auth 60s before expiry — avoids mid-migration token expiry.
- **config.json**: gitignored — NEVER commit.
- **Audit logs**: CyberArk audit logs are archived to `output/reports/cyberark_audit_archive/` before migration. They do NOT transfer to SS. New SS audit trail begins at import date.
- **PSM recordings**: Cannot migrate. Document loss in compliance report before P3.
- **Permission escalation**: Agent 03 flags members who gain more access post-collapse. All escalations MUST be reviewed before P3 proceeds.
- **Atomic state + SHA-256 chain**: same as Option A.

---

## Decision Log

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Permission model | 22→4 (LOSSY, documented) | SS does not support granular permissions; collapse is unavoidable; escalation detection mitigates risk |
| Audit log handling | Archive CyberArk logs; do NOT transfer | SS audit log format incompatible; transferring would create false provenance; new trail starts at migration |
| PSM recordings | Not migrated | SS has no PSM equivalent; recordings remain on CyberArk archive storage |
| Integration approach | Full OAuth2 re-architecture | CCP/AAM patterns have no direct SS equivalent; clean rewrite is safer than shim layer |
| Folder hierarchy | "Imported" root + per-safe children | Preserves safe grouping in SS folder structure; easy to identify migrated vs native SS secrets |
| Template auto-create | Yes for standard platforms | Reduces manual work for 8 standard mappings; custom platforms still require manual creation |
| Token refresh | Proactive at 60s before expiry | SS tokens have short TTL; reactive refresh risks mid-operation expiry on large batches |
| Failed password retrieval | Skip account (not import empty) | Importing with empty secret is worse than not importing — operators notice missing accounts |

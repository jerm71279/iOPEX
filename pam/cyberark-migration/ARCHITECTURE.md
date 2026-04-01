# CyberArk Migration — Architecture

## System Overview

15-agent AI orchestrator executing CyberArk PAS on-premises → Privilege Cloud migration. The coordinator sequences agents through 8 phases (P0–P7), gating each phase on prior agent output. State is persisted atomically with SHA-256 audit chain for crash recovery and compliance. Source: CyberArk PVWA REST API. Target: Privilege Cloud REST API + OAuth2.

---

## Component Map

```
coordinator.py              Phase sequencer — runs agents in order, validates AgentResult gates
cli.py                      Entry point: preflight / start / run / advance / status / agent

core/
  base.py                   AgentBase ABC + AgentResult (status, data, errors, approval)
  state.py                  MigrationState — atomic JSON writes, fcntl locking, .bak recovery
  logging.py                AuditLogger — SHA-256 hash chain, SIEM-ready JSONL
  cyberark_client.py        PVWA REST client (source) — context manager, env var creds
  cloud_client.py           Privilege Cloud REST client (target) — OAuth2 client_credentials
  source_adapters.py        7 vendor adapters (BeyondTrust, SS, HashiCorp, AWS, Azure, GCP)

agents/
  agent_01_discovery.py     Scout     — safe/account/platform enumeration + NHI pre-classify
  agent_02_gap_analysis.py  Analyst   — 10-domain readiness, 4 compliance frameworks
  agent_03_permissions.py   Mapper    — 22-permission 1:1 mapping, 7 sensitive flags
  agent_04_etl.py           Mover     — 7-step ETL pipeline, watchdog, emergency unfreeze
  agent_05_heartbeat.py     Validator — 10 post-migration checks
  agent_06_integration.py   Rewirer   — CCP/AAM code scan + repoint to Privilege Cloud
  agent_07_compliance.py    Auditor   — PCI-DSS, NIST, HIPAA, SOX evidence generation
  agent_08_runbook.py       Gatekeeper— phase gates + human approval workflow
  agent_09_dependency_mapper.py  Mapper — 6-scanner dependency graph, ETL gate
  agent_10_staging.py       Tester    — 10 staging assertions, hard-blocks production
  agent_11_source_adapter.py     Importer — multi-vendor source normalization
  agent_12_nhi_handler.py   Classifier— 7 NHI subtypes, weighted 3-signal scoring
  agent_13_platform_plugins.py   Porter — custom platform export/import
  agent_14_onboarding.py    Onboarder — 10-step service account pipeline
  agent_15_hybrid_fleet.py  Balancer  — on-prem + cloud CPM routing during P6

config.example.json         Connection template (copy → config.json, never commit)
agent_config.json           Agent thresholds, batch sizes, watchdog timeout
output/                     Runtime (logs/, reports/, state/, state/raw/) — gitignored
```

---

## Data Flow

```
PHASE P1 — DISCOVERY
  PVWA API → Agent 01 (Scout) → raw inventory (output/state/raw/)
           → Agent 09 (Mapper) → dependency graph
           → Agent 12 (Classifier) → NHI classifications
           → Agent 11 (Importer) → normalize multi-vendor sources
           → Agent 02 (Analyst) → gap analysis report
           → Agent 03 (Mapper) → permission map (22→22)
  Gate: gap score ≥ threshold + human approval → advance to P2

PHASE P2 — INFRASTRUCTURE
  → Agent 13 (Porter) → platform plugins exported + imported
  → Agent 10 (Tester) → 10 staging assertions
  Gate: all assertions pass + human approval → advance to P3

PHASE P3 — POLICY MIGRATION
  → Agent 03 (Mapper) re-run → safe creation in Privilege Cloud
  → Agent 14 (Onboarder) → onboarding pipeline configured
  Gate: human approval → advance to P4

PHASE P4 — PILOT ETL
  → Agent 04 (Mover) → FREEZE → EXPORT → TRANSFORM →
                        SAFE CREATION → IMPORT → HEARTBEAT → UNFREEZE
  → Agent 05 (Validator) → 10 post-migration checks
  Gate: heartbeat pass + human approval → advance to P5

PHASE P5 — PRODUCTION WAVES
  Waves 1–5: Agent 04 + 05 repeat per wave
  → Agent 06 (Rewirer) → integration repointing
  → Agent 14 (Onboarder) → new account onboarding
  → Agent 07 (Auditor) → compliance evidence per wave

PHASE P6 — PARALLEL RUNNING
  → Agent 15 (Balancer) → hybrid fleet routing
  → Agent 05 (Validator) continuous
  → Agent 06 (Rewirer) → remaining integrations
  → Agent 07 (Auditor) → final compliance package

PHASE P7 — DECOMMISSION
  → Agent 07 (Auditor) → final audit report + sign-off
```

---

## Key Interfaces

| Interface | Type | Direction | Notes |
|-----------|------|-----------|-------|
| PVWA REST API | HTTP/JSON | Outbound (source) | `/PasswordVault/api/`; LDAP/Windows auth; no SAML |
| Privilege Cloud API | HTTP/JSON | Outbound (target) | `/PasswordVault/api/`; OAuth2 client_credentials |
| CyberArk Identity | HTTP/JSON | Outbound (auth) | `{identity_url}/oauth2/platformtoken` |
| CLI | stdin/stdout | Inbound | `cli.py` — human operator interface |
| State file | JSON/disk | Internal | `output/state/migration_state.json` — atomic writes |
| Audit log | JSONL/disk | Internal | SHA-256 hash chain; SIEM-exportable |
| Vendor APIs | HTTP/JSON | Outbound (P1) | BeyondTrust, SS, HashiCorp, AWS, Azure, GCP |

---

## Deployment Topology

```
LOCAL / ON-PREM EXECUTION (recommended)
  Python 3.12+ on migration workstation with network access to:
    - Source PVWA: https://pvwa.company.com
    - Target Privilege Cloud: https://company.privilegecloud.cyberark.com
    - CyberArk Identity: https://company.id.cyberark.cloud
  Credentials: environment variables (never config.json)
  Output: local ./output/ directory (gitignored)

NETWORK REQUIREMENTS
  Outbound 443: PVWA, Privilege Cloud, CyberArk Identity
  Inbound: none required
  CPM network: outbound to all managed endpoints (for heartbeat validation)
```

---

## Security Notes

- **Credentials**: `CYBERARK_USERNAME`, `CYBERARK_PASSWORD`, `PCLOUD_CLIENT_ID`, `PCLOUD_CLIENT_SECRET` via env vars only. Passwords zeroed from memory after auth.
- **config.json**: gitignored — NEVER commit. Contains live connection URLs.
- **HTTPS enforced**: Privilege Cloud and CyberArk Identity require TLS. PVWA enforced in production.
- **Atomic state writes**: temp file + fsync + os.replace + fcntl locking + .bak backup. No partial writes.
- **SHA-256 audit chain**: every log entry chained to previous — tamper-evident. SIEM-ready JSONL.
- **Error sanitization**: passwords/secrets/tokens stripped from all error messages before logging.
- **Signal handlers**: SIGTERM/SIGINT trigger safe shutdown — vault unfreeze before exit.
- **ETL watchdog**: auto-unfreeze at 120 min. Emergency unfreeze on any pipeline exception.

---

## Decision Log

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Permission model | 22→22 (1:1, no loss) | Privilege Cloud uses identical 22-permission model — no translation layer needed |
| Auth: Privilege Cloud | OAuth2 client_credentials | Preferred by CyberArk for programmatic access; supports token refresh without user interaction |
| Auth: PVWA source | LDAP/Windows/RADIUS | SAML not supported for API access (requires browser) |
| State persistence | JSON + atomic writes | Simple, inspectable, crash-recoverable; avoids DB dependency on migration workstation |
| ETL freeze strategy | Per-safe freeze | Minimizes blast radius — only migrating safe is frozen, not entire vault |
| Watchdog timer | 120 min default | Covers longest expected ETL batch; configurable via `agent_config.json` |
| NHI detection | 3-signal weighted | Single signal too many false negatives; 3 signals (platform + name + safe) gives high confidence |
| Multi-vendor support | Agent 11 + source_adapters.py | Customers often have secondary vaults; normalize at source rather than during ETL |

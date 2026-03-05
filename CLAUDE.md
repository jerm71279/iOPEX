# iOPEX PAM Migration Project

## Overview
CyberArk PAS on-prem migration project with two target paths: Option A (Privilege Cloud) and Option B (Delinea Secret Server). Each has its own 15-agent AI orchestration system, plus shared consulting and scripting toolkits.

## Contents
- `CyberArk migration/` — **15-Agent AI Orchestrator: CyberArk → Privilege Cloud** (Option A)
- `Secret Server migration/` — **15-Agent AI Orchestrator: CyberArk → Secret Server** (Option B)
- `PAM_Consulting_Agent/` — Consulting toolkit (assessment, discovery, validation)
- `pam-migration-assistant/` — Standalone migration scripts
- `Enhanced_ETL_Migration_v2.docx` — Detailed migration plan
- `CyberArk_Migration_Comparison.docx` — Option A vs Option B comparison

## 15-Agent AI Orchestrator — Option A (Privilege Cloud)

**Location:** `CyberArk migration/`
**Python:** 3.12+ | **Dependencies:** `requests`, `urllib3`, `python-docx`

### Architecture
```
coordinator.py              Main orchestrator — sequences agents per phase, signal handlers
cli.py                      CLI entry point
.gitignore                  Excludes config.json, credentials, output/, __pycache__/

core/
  base.py                   AgentBase ABC + AgentResult (status validation, approval timeout)
  state.py                  MigrationState — atomic writes, file locking, backup recovery
  logging.py                AuditLogger — SHA-256 hash chain, SIEM-ready JSONL
  cyberark_client.py        CyberArk PVWA REST client (context manager, env var credentials)
  cloud_client.py           Privilege Cloud REST client (OAuth2 + legacy auth)
  source_adapters.py        Multi-vendor source adapters (CyberArk, BeyondTrust, SS, HashiCorp, AWS, Azure, GCP)

agents/
  agent_01_discovery.py     Discovery & Dependency Mapping (Applications API, multi-signal NHI)
  agent_02_gap_analysis.py  Gap Analysis (10 domains, 4 compliance frameworks)
  agent_03_permissions.py   Permission Mapping (22 individual permissions via Safe Members API)
  agent_04_etl.py           ETL Orchestration (dependency/staging/NHI gates, watchdog, linked accounts)
  agent_05_heartbeat.py     Heartbeat & Validation (10 post-migration checks)
  agent_06_integration.py   Integration Repointing (CCP/AAM code scanning + replacement)
  agent_07_compliance.py    Compliance & Audit (PCI-DSS, NIST 800-53, HIPAA, SOX)
  agent_08_runbook.py       Runbook Execution (phase gates + human approvals)
  agent_09_dependency_mapper.py  Dependency Mapper (IIS, Windows services, scheduled tasks, Jenkins, scripts, configs)
  agent_10_staging.py       Staging Validation (10 assertions, rollback, hard-blocks production)
  agent_11_source_adapter.py     Multi-Vendor Source Adapter (BeyondTrust, SS, HashiCorp, cloud vaults)
  agent_12_nhi_handler.py   NHI Handler (7 NHI subtypes, weighted classification, per-type strategies)
  agent_13_platform_plugins.py   Platform Plugin Validator (export/import custom platforms)
  agent_14_onboarding.py    App Onboarding Factory (10-step pipeline for new service accounts)
  agent_15_hybrid_fleet.py  Hybrid Fleet Manager (mixed on-prem + cloud during parallel running)

config.example.json         Connection config template (OAuth2 + legacy, env var comments)
agent_config.json           Agent-specific settings
```

### Quick Start
```bash
cd "CyberArk migration"
cp config.example.json config.json
export CYBERARK_USERNAME="svc-migration"
export CYBERARK_PASSWORD="..."
export PCLOUD_CLIENT_ID="..."
export PCLOUD_CLIENT_SECRET="..."
python3 cli.py preflight
python3 cli.py start my-migration-001
python3 cli.py run P1 --dry-run
python3 cli.py run P1
python3 cli.py status
```

### Key Technical Details

**Authentication:**
- On-prem PVWA: CyberArk/LDAP/RADIUS/Windows auth (no SAML — requires browser)
- Privilege Cloud: OAuth2 via CyberArk Identity (`{identity_url}/oauth2/platformtoken`, client_credentials grant) or legacy PVWA logon
- Credentials via environment variables (recommended): `CYBERARK_USERNAME`, `CYBERARK_PASSWORD`, `PCLOUD_CLIENT_ID`, `PCLOUD_CLIENT_SECRET`
- Passwords zeroed from memory after authentication

**Permission Model:**
- Privilege Cloud uses the same 22 individual safe permissions as on-prem CyberArk
- Agent 03 maps permissions 1:1 via the Safe Members API — no role simplification
- 7 security-sensitive permissions flagged for human review (ManageSafe, ManageSafeMembers, AccessWithoutConfirmation, etc.)

**ETL Pipeline (Agent 04):**
- 7 steps with real API calls: FREEZE → EXPORT → TRANSFORM → SAFE CREATION → IMPORT → HEARTBEAT → UNFREEZE
- Password retrieval via `POST /Accounts/{id}/Password/Retrieve`
- Linked account migration via `POST /Accounts/{id}/LinkAccount`
- Watchdog timer auto-unfreezes on timeout (default 120 min)
- Emergency unfreeze on any pipeline exception

**Security Features:**
- Atomic state writes (temp file + fsync + os.replace + fcntl locking + .bak backup)
- SIGTERM/SIGINT signal handlers for safe shutdown
- Error sanitization — strips passwords/secrets/tokens from error messages
- SHA-256 hash chain in audit logs for tamper evidence
- HTTPS enforced for Privilege Cloud
- `.gitignore` excludes config.json, *.pem, *.key, .env, output/

**NHI Detection (Multi-Signal):**
- Signal 1: Platform-based (UnixSSHKeys, WinServiceAccount, AWSAccessKeys, etc.)
- Signal 2: Name patterns (^svc[_-], ^app[_-], service.?account, etc.)
- Signal 3: Safe name patterns (appcred, automation, cicd, pipeline, etc.)

**State Machine:**
- JSON-backed with atomic writes and corruption recovery
- Raw data separated to `output/state/raw/` (not in main state file)
- Append-only lists capped (steps: 5000, errors: 1000, approvals: 500)
- Resume after crash — coordinator picks up from last completed step

### Migration Phases
| Phase | Duration | Focus | Agents |
|-------|----------|-------|--------|
| P0 | — | Environment Setup | manual |
| P1 | 3-4 weeks | Discovery, Dependency Mapping, NHI Classification | 11, 01, 09, 12, 02, 03 |
| P2 | 2-3 weeks | Infrastructure, Platform Validation, Staging | 13, 10 |
| P3 | 2-3 weeks | Safe & Policy Migration, App Onboarding Setup | 03, 14 |
| P4 | 1-2 weeks | Pilot Migration | 04, 05 |
| P5 | 4-6 weeks | Production Batches (Waves 1-5) | 04, 05, 06, 14, 07 |
| P6 | 4-6 weeks | Parallel Running & Cutover | 15, 05, 06, 07 |
| P7 | 2-3 weeks | Decommission & Close-Out | 07 |

### Test Environment (Decision Pending)
No dedicated sandbox exists. Options under evaluation:
- **A. Lab Instance** — CyberArk PVWA dev/lab + Privilege Cloud test tenant (low effort, high fidelity)
- **B. Mock API Server** — Flask/FastAPI emulating PVWA/Cloud APIs (medium effort)
- **C. Unit Test Fixtures** — pytest with mocked API clients (medium effort, good for CI/CD)
- **D. Docker Harness** — Mock API containers with pre-seeded data (high effort)
- **E. Hybrid (Recommended)** — A for integration testing + C for regression/CI

See `CyberArk migration/README.md` for full decision matrix.

## 15-Agent AI Orchestrator — Option B (Secret Server)

**Location:** `Secret Server migration/`
**Python:** 3.12+ | **Dependencies:** `requests`, `urllib3`, `python-docx`

### Architecture
```
coordinator.py              Main orchestrator — sequences agents per phase, signal handlers
cli.py                      CLI entry point (status/start/run/advance/agent/preflight/agents)
build_docx.py               Styled .docx documentation generator (APM Terminals format, 22 sections)
.gitignore                  Excludes config.json, credentials, output/, __pycache__/

core/
  base.py                   AgentBase ABC + AgentResult (same as Option A)
  state.py                  MigrationState — atomic writes, file locking (same as Option A)
  logging.py                AuditLogger — SHA-256 hash chain (same as Option A)
  cyberark_client.py        CyberArk PVWA REST client (same source system)
  secret_server_client.py   Delinea Secret Server REST client (OAuth2 + legacy, folders/secrets/templates)
  source_adapters.py        Multi-vendor source adapters (same as Option A)

agents/
  agent_01_discovery.py     Discovery & Dependency Mapping (same source discovery)
  agent_02_gap_analysis.py  Gap Analysis (10 domains + SS template readiness + permission model risk)
  agent_03_permissions.py   Permission Translation — 22→4 LOSSY (escalation detection, loss tracking)
  agent_04_etl.py           ETL — Safe→Folder, Platform→Template, Account→Secret (dependency/staging/NHI gates)
  agent_05_heartbeat.py     Validation (10 checks + SS heartbeat API + RPC + audit continuity)
  agent_06_integration.py   Integration Repointing (CCP/AAM → SS REST API + OAuth2)
  agent_07_compliance.py    Compliance (PCI-DSS, NIST, HIPAA, SOX + SS-specific risks)
  agent_08_runbook.py       Runbook Execution (SS-specific phase gates)
  agent_09_dependency_mapper.py  Dependency Mapper (same scanners as Option A)
  agent_10_staging.py       Staging Validation (10 assertions against SS staging instance)
  agent_11_source_adapter.py     Multi-Vendor Source Adapter (same as Option A)
  agent_12_nhi_handler.py   NHI Handler (same classification as Option A)
  agent_13_platform_plugins.py   Platform Plugin Validator (CyberArk platforms → SS templates, auto-create)
  agent_14_onboarding.py    App Onboarding Factory (SS folders/templates/secrets pipeline)
  agent_15_hybrid_fleet.py  Hybrid Fleet Manager (on-prem CyberArk + SS during parallel running)

config.example.json         CyberArk source + Secret Server target config
agent_config.json           Agent settings (thresholds, batch sizes, platform→template map)
requirements.txt            Python dependencies
output/                     Runtime output (logs/, reports/, state/, state/raw/)
```

### Quick Start
```bash
cd "Secret Server migration"
cp config.example.json config.json
export CYBERARK_USERNAME="svc-migration"
export CYBERARK_PASSWORD="..."
export SS_CLIENT_ID="..."
export SS_CLIENT_SECRET="..."
python3 cli.py preflight
python3 cli.py start my-migration-001
python3 cli.py run P1 --dry-run
python3 cli.py run P1
python3 cli.py status
```

### Key Differences from Option A (Privilege Cloud)
| Aspect | Privilege Cloud | Secret Server |
|--------|----------------|---------------|
| Permission model | 22→22 (1:1) | **22→4 roles (LOSSY)** |
| Data structure | Safe→Safe | Safe→Folder (hierarchical) |
| Platforms | Platform→Platform | Platform→Secret Template |
| API surface | Same `/PasswordVault/api/` | Different `/api/v1/` |
| Audit logs | Can migrate | **Do NOT transfer** |
| PSM recordings | Can migrate | **Cannot migrate** |
| Integration rework | Similar patterns | **Full re-architecture (OAuth2)** |
| CPM/RPC | CPM plugins carry over | RPC plugins must be rebuilt per template |

### Key Technical Details

**Authentication:**
- On-prem PVWA: CyberArk/LDAP/RADIUS/Windows auth (no SAML — requires browser)
- Secret Server: OAuth2 via `/oauth2/token` (client_credentials grant, recommended) or legacy (password grant)
- Credentials via environment variables (recommended): `CYBERARK_USERNAME`, `CYBERARK_PASSWORD`, `SS_CLIENT_ID`, `SS_CLIENT_SECRET`
- Passwords zeroed from memory after authentication
- Proactive token refresh: re-authenticates when token is within 60s of expiry

**Permission Model (22→4 — LOSSY):**
- CyberArk uses 22 individual safe permissions; Secret Server collapses to 4 roles (Owner, Edit, View, List)
- **Owner** requires BOTH ManageSafe AND ManageSafeMembers
- **Edit** requires ANY of: AddAccounts, UpdateAccountContent, UpdateAccountProperties, DeleteAccounts, RenameAccounts, UnlockAccounts
- **View** requires ANY of: UseAccounts, RetrieveAccounts
- **List** requires ANY of: ListAccounts, ViewSafeMembers, ViewAuditLog
- **9 permissions have NO SS equivalent** (always lost): AccessWithoutConfirmation, SpecifyNextAccountContent, BackupSafe, CreateFolders, DeleteFolders, MoveAccountsAndFolders, RequestsAuthorizationLevel1/2, InitiateCPMAccountManagementOperations
- Escalation detection: flags members who get MORE access than they had (e.g., View→Edit when only UnlockAccounts triggered Edit; admin-only→full Owner when ManageSafe/ManageSafeMembers had no data access)
- Agent 03 produces a detailed loss report per member — MUST be reviewed before P3

**ETL Pipeline (Agent 04):**
- 7 steps with real API calls: FREEZE → EXPORT → TRANSFORM → FOLDER CREATION → IMPORT → HEARTBEAT → UNFREEZE
- Transform: userName→username slug, address→machine slug, platformId→template lookup, platformAccountProperties→notes
- Folder hierarchy: Parent "Imported" folder at root, then per-safe child folders
- Password retrieval via `POST /Accounts/{id}/Password/Retrieve` — failed retrievals are skipped (not imported with empty secrets)
- Secret creation via `POST /api/v1/secrets` with template ID + field items
- Heartbeat via `POST /api/v1/secrets/{id}/heartbeat`
- Watchdog timer auto-unfreezes on timeout (default 120 min)
- Emergency unfreeze on any pipeline exception

**Platform → Template Mapping:**
- WinServerLocal → Windows Account
- WinDomain → Active Directory Account
- UnixSSH → Unix Account (SSH)
- UnixSSHKeys → Unix Account (SSH Key Rotation)
- Oracle/MSSql/MySQL → database-specific templates
- AzureServicePrincipal → Azure Service Principal
- AWSAccessKeys → Amazon IAM Key
- Custom platforms require manual SS template creation (flagged by Agent 02)

**Security Features:**
- Atomic state writes (temp file + fsync + os.replace + fcntl locking + .bak backup)
- SIGTERM/SIGINT signal handlers for safe shutdown
- Error sanitization — strips passwords/secrets/tokens from error messages
- SHA-256 hash chain in audit logs for tamper evidence
- Proactive token refresh (re-auth 60s before expiry)
- `.gitignore` excludes config.json, *.pem, *.key, .env, output/

**NHI Detection (Multi-Signal):**
- Signal 1: Platform-based (UnixSSHKeys, WinServiceAccount, AWSAccessKeys, etc.)
- Signal 2: Name patterns (^svc[_-], ^app[_-], service.?account, etc.)
- Signal 3: Safe name patterns (appcred, automation, cicd, pipeline, etc.)

**State Machine:**
- JSON-backed with atomic writes and corruption recovery
- Raw data separated to `output/state/raw/` (not in main state file)
- Append-only lists capped (steps: 5000, errors: 1000, approvals: 500)
- Resume after crash — coordinator picks up from last completed step

**SS-Specific Compliance Risks:**
1. **Audit Log Discontinuity** (HIGH) — CyberArk logs do NOT transfer to SS
2. **Permission Model Simplification** (HIGH) — 22→4 collapse with escalation risk
3. **PSM Session Recording Loss** (MEDIUM) — Cannot migrate to SS

### Migration Phases (SS-specific naming)
| Phase | Duration | Focus | Agents |
|-------|----------|-------|--------|
| P0 | — | Environment Setup | manual |
| P1 | 3-4 weeks | Discovery, Dependency Mapping, NHI Classification | 11, 01, 09, 12, 02, 03 |
| P2 | 2-3 weeks | Infrastructure, Template Validation, Staging | 13, 10 |
| P3 | 2-3 weeks | Folder & Template Migration, App Onboarding Setup | 03, 14 |
| P4 | 1-2 weeks | Pilot Migration | 04, 05 |
| P5 | 4-6 weeks | Production Batches (Waves 1-5) | 04, 05, 06, 14, 07 |
| P6 | 4-6 weeks | Parallel Running & Cutover | 15, 05, 06, 07 |
| P7 | 2-3 weeks | Decommission & Close-Out | 07 |

### Test Environment (Decision Pending)
No dedicated sandbox exists. Options under evaluation:
- **A. Lab Instance** — CyberArk PVWA dev/lab + Secret Server test instance (low effort, high fidelity)
- **B. Mock API Server** — Flask/FastAPI emulating PVWA + SS APIs (medium effort)
- **C. Unit Test Fixtures** — pytest with mocked API clients (medium effort, good for CI/CD)
- **D. Docker Harness** — Mock API containers with pre-seeded data (high effort)
- **E. Hybrid (Recommended)** — A for integration testing + C for regression/CI

See `Secret Server migration/README.md` for full decision matrix.

## PAM Consulting Agent
Located in `PAM_Consulting_Agent/`:

### Scripts
```bash
python3 scripts/pam_assessor.py --interactive
python3 scripts/pam_autodiscovery.py --url https://pvwa.company.com --user admin
python3 scripts/nhi_discovery.py --audit-file audit.csv --output nhis.json
python3 scripts/migration_validator.py --source cyberark.csv --target secretserver.csv
cd scripts && streamlit run web_app.py --server.port 8501
```

## PAM Migration Assistant (Standalone Scripts)
Located in `pam-migration-assistant/`:

```bash
python3 scripts/ccp_code_scanner.py /path/to/code --output results.json
python3 scripts/nhi_discovery.py --audit-file audit.csv --output nhis.csv
python3 scripts/integration_mapper.py --scan /path/to/code --output integrations.csv
python3 scripts/wave_classifier.py --accounts accounts.csv --nhis nhis.csv --output waves.csv
python3 scripts/code_converter.py results.json --language python --output converted/
python3 scripts/generate_wrapper.py --language python --output pam_wrapper.py
```

### Reference Docs
- `references/api_mapping.md` — CyberArk to Secret Server API translation
- `references/permission_matrix.md` — Permission translation guide
- `references/nhi_discovery.md` — NHI identification guide

## Running Tests
```bash
cd pam-migration-assistant && python3 -m pytest tests/ -v
```

## Notes
- Config files with credentials (`config.json`) must never be committed
- Set credentials via environment variables, not config files
- All timestamps are UTC ISO 8601 (`datetime.now(timezone.utc)`)
- Audit logs are JSONL format with SHA-256 hash chain for tamper evidence

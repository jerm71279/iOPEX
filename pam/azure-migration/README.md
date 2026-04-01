# iOPEX PAM Migration Project

## Overview

CyberArk PAS (on-prem) to KeeperPAM migration project. Contains the operational runbook, a multi-agent AI orchestration system, a consulting assessment toolkit, and standalone migration scripts.

## Project Structure

```
iOPEX/
  CyberArk migration/          # Multi-Agent AI Orchestrator (PRIMARY)
  PAM_Consulting_Agent/         # Consulting toolkit (assessment, discovery, validation)
  pam-migration-assistant/      # Standalone migration scripts
  Enhanced_ETL_Migration_v2.docx
```

**OneDrive docs** (`/mnt/c/Users/1/OneDrive/Documents/iOPEX/`):
- `iOPEX_PAM_Migration_Runbook.docx` — Operational runbook (Phases P0-P7)
- `Agentic_AI_Migration_System.pptx` — System architecture deck
- `README.md` — System overview

---

## Multi-Agent AI Orchestrator

**Location:** `CyberArk migration/`
**Python:** 3.12+ | **Dependencies:** `requests`, `urllib3`

### Quick Start

```bash
cd "CyberArk migration"
cp config.example.json config.json     # Fill in CyberArk credentials
# Set credentials via environment variables (recommended):
export CYBERARK_USERNAME="svc-migration"
export CYBERARK_PASSWORD="..."
export KEEPERPAM_CLIENT_ID="..."
export KEEPERPAM_CLIENT_SECRET="..."

python3 cli.py agents                  # List all multi-agents
python3 cli.py preflight               # Run all preflight checks
python3 cli.py start my-migration-001  # Initialize migration
python3 cli.py run P1 --dry-run        # Simulate Phase 1
python3 cli.py run P1                  # Execute Phase 1
python3 cli.py status                  # Check progress
python3 cli.py advance                 # Move to next phase
```

### Architecture

```
coordinator.py                  Main orchestrator — sequences agents per phase, signal handlers
cli.py                          CLI entry point (status/start/run/advance/agent/preflight/agents)
.gitignore                      Excludes config.json, credentials, output/, __pycache__/

core/
  base.py                       AgentBase ABC + AgentResult dataclass (status validation, approval timeout)
  state.py                      MigrationState — atomic writes, file locking, backup recovery
  logging.py                    AuditLogger — SHA-256 hash chain, SIEM-ready JSONL
  cyberark_client.py            CyberArk PVWA REST client (context manager, env var credentials)
  keeper_client.py              KeeperPAM REST client (OAuth2)
  source_adapters.py            Multi-vendor source adapters (CyberArk, BeyondTrust, SS, HashiCorp, AWS, Azure, GCP)

agents/
  agent_01_discovery.py         Discovery & Dependency Mapping (Applications API, multi-signal NHI)
  agent_02_gap_analysis.py      Gap Analysis (10 domains, 4 compliance frameworks)
  agent_03_permissions.py       Permission Mapping (22 individual permissions via Safe Members API)
  agent_04_etl.py               Migration Pipeline Orchestration (dependency/staging/NHI gates, watchdog, linked accounts)
  agent_05_heartbeat.py         Heartbeat & Validation (10 post-migration checks)
  agent_06_integration.py       Integration Repointing (CCP/AAM code scanning + replacement)
  agent_07_compliance.py        Compliance & Audit (PCI-DSS, NIST 800-53, HIPAA, SOX)
  agent_08_runbook.py           Runbook Execution (phase gates + human approvals)
  agent_09_dependency_mapper.py Dependency Mapper (IIS, Windows services, scheduled tasks, Jenkins, scripts, configs)
  agent_10_staging.py           Staging Validation (10 assertions, rollback, hard-blocks production)
  agent_11_source_adapter.py    Multi-Vendor Source Adapter (BeyondTrust, SS, HashiCorp, cloud vaults)
  agent_12_nhi_handler.py       NHI Handler (7 NHI subtypes, weighted classification, per-type strategies)
  agent_13_platform_plugins.py  Platform Plugin Validator (export/import custom platforms)
  agent_14_onboarding.py        App Onboarding Factory (10-step pipeline for new service accounts)
  agent_15_hybrid_fleet.py      Hybrid Fleet Manager (mixed on-prem + cloud during parallel running)

config.example.json             Connection config template (OAuth2 + legacy, env var comments)
agent_config.json               Agent-specific settings (thresholds, batch sizes, rate limits)
requirements.txt                Python dependencies
output/                         Runtime output (logs/, reports/, state/, state/raw/)
```

### Agent Interface

Every agent inherits from `AgentBase` and implements two methods:

```python
class AgentBase(ABC):
    def preflight(self) -> AgentResult:
        """Validate prerequisites (connectivity, permissions, data)."""

    def run(self, phase: str, input_data: dict) -> AgentResult:
        """Execute agent logic. Returns AgentResult with status/data/errors/metrics."""
```

`AgentResult.status` is one of: `"success"` | `"failed"` | `"needs_approval"` | `"partial"`

Helper properties:
- `result.succeeded` — True only for `"success"`
- `result.passed` — Same as `succeeded` (used for preflight checks)
- `result.partial_success` — True for `"success"` or `"partial"`
- `result.needs_human` — True for `"needs_approval"`

Human approval gates include a configurable timeout (default 30 minutes) and fail-safe deny in non-interactive mode (no TTY).

### Agent Registry

| Key | Class | Agent ID | Phases |
|-----|-------|----------|--------|
| `01-discovery` | `DiscoveryAgent` | `agent_01_discovery` | P1 |
| `02-gap-analysis` | `GapAnalysisAgent` | `agent_02_gap_analysis` | P1 |
| `03-permissions` | `PermissionMappingAgent` | `agent_03_permissions` | P1, P3 |
| `04-etl` | `ETLOrchestrationAgent` | `agent_04_etl` | P4, P5 |
| `05-heartbeat` | `HeartbeatAgent` | `agent_05_heartbeat` | P4, P5, P6 |
| `06-integration` | `IntegrationRepointingAgent` | `agent_06_integration` | P5, P6 |
| `07-compliance` | `ComplianceAgent` | `agent_07_compliance` | P5, P6, P7 |
| `08-runbook` | `RunbookAgent` | `agent_08_runbook` | All |
| `09-dependency-mapper` | `DependencyMapperAgent` | `agent_09_dependency_mapper` | P1 |
| `10-staging` | `StagingValidationAgent` | `agent_10_staging` | P2 |
| `11-source-adapter` | `SourceAdapterAgent` | `agent_11_source_adapter` | P1 |
| `12-nhi-handler` | `NHIHandlerAgent` | `agent_12_nhi_handler` | P1 |
| `13-platform-plugins` | `PlatformPluginAgent` | `agent_13_platform_plugins` | P2 |
| `14-onboarding` | `OnboardingAgent` | `agent_14_onboarding` | P3, P5 |
| `15-hybrid-fleet` | `HybridFleetAgent` | `agent_15_hybrid_fleet` | P6 |

### Phase Execution Map

| Phase | Name | Agents Run | Human Gate |
|-------|------|-----------|------------|
| P0 | Environment Setup | *(manual)* | — |
| P1 | Discovery, Dependency Mapping, NHI Classification | 11, 01, 09, 12, 02, 03 | Review discovery + deps + NHI + gaps + permissions |
| P2 | Infrastructure, Platform Validation, Staging | 13, 10 | Approve staging results |
| P3 | Safe & Policy Migration, App Onboarding Setup | 03, 14 | Approve safe/policy plan |
| P4 | Pilot Migration | 04, 05 | Approve pilot results |
| P5 | Production Batches | 04, 05, 06, 14, 07 | Approve each wave |
| P6 | Parallel Running & Cutover | 15, 05, 06, 07 | Approve cutover |
| P7 | Decommission & Close-Out | 07 | Final sign-off |

### Data Flow

```
Agent 11 (Source Adapter)  →  normalized account inventory from any source vendor
       ↓
Agent 01 (Discovery)  →  discovery manifest (accounts, safes, platforms, NHIs, integrations, applications)
       ↓
Agent 09 (Dependency Mapper)  →  dependency graph (app→account, NHI chains, integration mappings)
       ↓
Agent 12 (NHI Handler)  →  NHI classification, weighted risk scores, rotation policies
       ↓
Agent 02 (Gap Analysis)  →  maturity scores, compliance gaps, recommendations
       ↓
Agent 03 (Permissions)  →  individual permission translations, sensitive holders, exceptions
       ↓
Agent 13 (Platform Plugins)  →  platform validation, custom plugin deployment
       ↓
Agent 10 (Staging)  →  10-assertion staging validation, rollback, production gate
       ↓
Agent 14 (Onboarding)  →  new app onboarding pipeline (folder/permissions/secret/rotation/heartbeat)
       ↓
Agent 04 (Migration Pipeline)  →  batch migration results (per wave: freeze/export/transform/import/heartbeat/unfreeze)
       ↓
Agent 05 (Heartbeat)  →  10-check validation report (count, heartbeat, permissions, folders, metadata, etc.)
       ↓
Agent 06 (Integration)  →  CCP/AAM scan results, replacement code templates, change registry
       ↓
Agent 07 (Compliance)  →  compliance report (PCI-DSS, NIST, HIPAA, SOX control mapping)
       ↓
Agent 15 (Hybrid Fleet)  →  parallel-run orchestration, traffic routing, cutover decisions
       ↓
Agent 08 (Runbook)  →  phase gate management, advance/block decisions
```

### CLI Commands

| Command | Description |
|---------|-------------|
| `python3 cli.py status` | Show migration status and phase breakdown |
| `python3 cli.py start <id>` | Start new migration with given ID |
| `python3 cli.py run <P#>` | Run all agents for a phase |
| `python3 cli.py run <P#> --dry-run` | Simulate phase without API calls |
| `python3 cli.py advance` | Advance to next phase |
| `python3 cli.py agent <key>` | Run a single agent (e.g., `01-discovery`) |
| `python3 cli.py agent <key> --phase P#` | Run agent for a specific phase |
| `python3 cli.py preflight` | Run all agent preflight checks |
| `python3 cli.py agents` | List all available agents |

The coordinator (`coordinator.py`) accepts the same commands via `--start`, `--phase`, `--status`, `--advance`, `--resume`, `--dry-run`.

### Credential Management

Credentials should be provided via **environment variables** (recommended) rather than stored in `config.json`. The config file should only contain URLs, timeouts, and non-sensitive settings.

| Environment Variable | Purpose |
|---------------------|---------|
| `CYBERARK_USERNAME` | On-prem PVWA service account username |
| `CYBERARK_PASSWORD` | On-prem PVWA service account password |
| `KEEPERPAM_CLIENT_ID` | KeeperPAM OAuth2 client ID |
| `KEEPERPAM_CLIENT_SECRET` | KeeperPAM OAuth2 client secret |

Passwords are **zeroed from memory** immediately after the authentication attempt. On token expiry (HTTP 401), credentials are re-read from environment variables for re-authentication.

### Configuration

**`config.json`** (copy from `config.example.json`):

| Key | Purpose |
|-----|---------|
| `cyberark_on_prem.base_url` | On-prem PVWA URL |
| `cyberark_on_prem.auth_type` | `"CyberArk"` / `"LDAP"` / `"RADIUS"` / `"Windows"` (no SAML — requires browser) |
| `cyberark_on_prem.verify_ssl` | SSL cert verification (default: `true`) |
| `cyberark_on_prem.timeout` | Request timeout seconds (default: `30`) |
| `cyberark_on_prem.rate_limit` | Seconds between requests (default: `0.1`) |
| `cyberark_on_prem.batch_size` | Pagination size (default: `1000`, max: `1000`) |
| `keeperpam.base_url` | KeeperPAM tenant URL |
| `keeperpam.auth_method` | `"oauth2"` (KeeperPAM uses OAuth2 only) |
| `keeperpam.batch_size` | Import pagination size (default: `500`, max: `1000`) |
| `servicenow.instance_url` | ServiceNow instance for change requests |
| `output_dir` | Output directory (default: `"./output"`) |
| `log_level` | Logging level (default: `"INFO"`) |
| `environment` | Environment context: `"dev"` / `"staging"` / `"prod"` |

**OAuth2 authentication** (KeeperPAM):
```
Token endpoint: https://<tenant>.keepersecurity.com/oauth2/token
Grant type: client_credentials
```

**`agent_config.json`** (agent-specific tuning):

| Agent | Key Settings |
|-------|-------------|
| `agent_01_discovery` | `scan_directories`, `integration_types`, `include_audit_logs`, `audit_log_days` |
| `agent_02_gap_analysis` | `compliance_frameworks`, `maturity_threshold`, `auto_score` |
| `agent_03_permissions` | *(uses ALL_PERMISSIONS list — 22 individual permissions, no role mapping)* |
| `agent_04_etl` | `batch_size` (500), `freeze_window_minutes` (120), `rate_limit_per_minute` (100), `backoff_strategy`, `watchdog_timeout_minutes`, `wave_order`, `pilot_size` (50) |
| `agent_05_heartbeat` | `count_variance_threshold` (0.01), `success_threshold` (0.95), `heartbeat_check_interval_seconds` |
| `agent_06_integration` | `supported_languages`, `generate_dual_backend_wrapper`, `scan_directories` |
| `agent_07_compliance` | `frameworks` (data-driven check definitions), `audit_retention_days`, `siem_export` |
| `agent_08_runbook` | `require_approval_for_phases`, `auto_advance`, `notification_channels` |
| `agent_09_dependency_mapper` | `scan_iis_logs`, `iis_log_paths`, `deep_scan_directories`, `dependency_confidence_threshold` |
| `agent_10_staging` | `staging_safe_prefix`, `test_account_count`, `assertion_timeout_seconds`, `auto_rollback` |
| `agent_11_source_adapter` | `source_type` (cyberark/beyondtrust/hashicorp/aws/azure/gcp), `source_config`, `normalize_names` |
| `agent_12_nhi_handler` | `nhi_confidence_threshold` (0.6), `platform_weight`, `name_weight`, `dependency_weight`, `rotation_defaults` |
| `agent_13_platform_plugins` | `custom_plugin_dir`, `platform_mapping_overrides`, `validate_connection_components` |
| `agent_14_onboarding` | `parent_folder`, `pending_requests`, `default_rotation_days` (30), `verify_heartbeat` |
| `agent_15_hybrid_fleet` | `parallel_read_percentage` (10), `cutover_threshold` (0.99), `rollback_on_failure`, `traffic_routing_mode` |

### Security Features

#### Secrets Management
- Credentials loaded from **environment variables** (preferred) with config.json fallback
- Passwords **zeroed from memory** after authentication (`self._password = None`)
- Error messages **sanitized** via `_safe_error()` — strips passwords, secrets, tokens from HTTP error text
- `config.json` excluded via `.gitignore` — only `config.example.json` is committed
- HTTPS enforced for KeeperPAM connections

#### Atomic State Writes
State persistence uses a crash-safe write sequence:
1. Write to temporary file in same directory (`tempfile.mkstemp`)
2. `os.fsync()` to flush to disk
3. `os.replace()` for POSIX atomic rename
4. File locking via `fcntl.flock(LOCK_EX)` prevents concurrent writes
5. Automatic backup (`.bak`) before every write
6. Corruption recovery: falls back to backup if main state file is corrupted

#### Signal Handlers
The coordinator registers `SIGTERM` and `SIGINT` handlers that:
1. Log the emergency shutdown event
2. Save current state to disk
3. Exit cleanly with appropriate exit code (128 + signal number)

#### Tamper-Evident Audit Logging
Every audit log entry includes a `chain_hash` field — a running SHA-256 hash that chains each event to its predecessor. Tampering with or deleting log entries breaks the hash chain, making modifications detectable during compliance audits.

#### Watchdog Timer
The migration pipeline starts a `threading.Timer` watchdog at the beginning of each batch. If the pipeline stalls or crashes mid-batch, the watchdog fires after `watchdog_timeout_minutes` (default: 120) and triggers `_emergency_unfreeze()` to re-enable CPM management for all frozen accounts, preventing indefinite safe lockout.

#### Approval Timeouts
Human-in-the-loop gates have a configurable timeout (default: 30 minutes). If no response is received before the deadline, the gate auto-denies (fail-safe). In non-interactive mode (no TTY attached), approvals are automatically denied.

### State Machine

Migration state persists to `output/state/migration_state.json` via atomic writes. Tracks:
- Current phase (P0-P7)
- Phase statuses (pending / in_progress / completed)
- Completed steps (capped at 5,000 entries)
- Agent results (keyed by `agent_id:phase`, raw data stripped)
- Human approvals (capped at 500 entries)
- Batch progress (wave/batch status for P5)
- Errors (capped at 1,000 entries)

**Raw data separation**: Large datasets (raw accounts, safes, platforms, applications) are stored in `output/state/raw/{agent_id}_{phase}.json` — not in the main state file. This keeps the state file small and fast to load.

This enables **resume after interruption** — restart the coordinator and it picks up where it left off.

### Permission Mapping (Agent 03)

KeeperPAM uses the **same individual permission model** as on-prem CyberArk. Agent 03 maps all 22 safe member permissions directly via the Safe Members API — there is no role-based simplification or permission loss.

**All 22 CyberArk Safe Permissions** (mapped 1:1):
```
UseAccounts              RetrieveAccounts         ListAccounts
AddAccounts              UpdateAccountContent     UpdateAccountProperties
InitiateCPMAccountManagementOperations            SpecifyNextAccountContent
RenameAccounts           DeleteAccounts           UnlockAccounts
ManageSafe               ManageSafeMembers        BackupSafe
ViewAuditLog             ViewSafeMembers          AccessWithoutConfirmation
CreateFolders            DeleteFolders            MoveAccountsAndFolders
RequestsAuthorizationLevel1                       RequestsAuthorizationLevel2
```

**Security-sensitive permissions** flagged for human review:

| Permission | Risk |
|-----------|------|
| `ManageSafe` | Full safe admin — can modify safe properties |
| `ManageSafeMembers` | Can grant/revoke access to other users |
| `AccessWithoutConfirmation` | Bypasses dual-control approval workflow |
| `SpecifyNextAccountContent` | Can set the next password value |
| `InitiateCPMAccountManagementOperations` | Can trigger CPM verify/change/reconcile |
| `RequestsAuthorizationLevel1` | Dual-control authorization level 1 |
| `RequestsAuthorizationLevel2` | Dual-control authorization level 2 |

Built-in members (`Master`, `Batch`, `Backup Users`, `DR Users`, `Auditors`, `Operators`) are automatically skipped.

Phase P1 produces the analysis report. Phase P3 applies permissions to KeeperPAM via `add_safe_member()` / `update_safe_member()`, handling 409 conflicts (member already exists) by falling back to update.

### Migration Pipeline (Agent 04)

Each batch executes 7 steps in sequence with **real API calls**:

```
1. FREEZE         — Disable CPM automatic management (PATCH /Accounts/{id})
2. EXPORT         — Pull full account details + retrieve passwords
3. TRANSFORM      — Map fields to KeeperPAM format, preserve all properties
4. SAFE CREATION  — Create target safes if they don't exist
5. IMPORT         — Push accounts with retry + exponential backoff (rate-limited)
6. HEARTBEAT      — Trigger verification (POST /Accounts/{id}/Verify)
7. UNFREEZE       — Re-enable CPM management for all frozen accounts
```

**Key implementation details:**
- **Password retrieval**: `POST /Accounts/{id}/Password/Retrieve` — accounts where retrieval fails are skipped (not imported with empty secrets)
- **Safe creation**: Target safes are auto-created with `ManagingCPM=PasswordManager` and retention defaults before import
- **Linked accounts**: Logon/reconcile account relationships are recreated via `POST /Accounts/{id}/LinkAccount`
- **Field preservation**: `platformAccountProperties`, `remoteMachinesAccess`, `secretType`, `secretManagement` are all preserved during transform
- **Failure threshold**: >10% batch failure = batch marked as `"failed"`, otherwise `"partial"`
- **Both clients** use context managers (`with CyberArkClient() as source:`) to prevent connection leaks
- **Emergency unfreeze**: On any exception during the pipeline, all frozen accounts are automatically unfrozen

**Watchdog**: If the pipeline stalls mid-batch, auto-UNFREEZE fires after `watchdog_timeout_minutes` (default: 120) to prevent indefinite safe lockout.

**Wave classification** (5 waves by risk):

| Wave | Risk | Accounts |
|------|------|----------|
| 1 | LOW | Test/Dev/Sandbox |
| 2 | MEDIUM | Standard user accounts |
| 3 | MEDIUM-HIGH | Infrastructure/network/admin |
| 4 | HIGH | NHIs without CCP/AAM |
| 5 | CRITICAL | NHIs with CCP/AAM (uses Applications API data for classification) |

### Validation Checks (Agent 05)

10 post-migration checks run after every batch:

1. **Count comparison** — Source vs target account counts within threshold
2. **Heartbeat status** — All imported accounts have valid credentials
3. **Permission mapping** — Translations applied correctly, exceptions flagged
4. **Folder structure** — Safe-to-folder hierarchy preserved
5. **Metadata integrity** — Descriptions and custom fields intact
6. **Group assignments** — Group/role memberships translated
7. **Password policies** — Rotation policies applied in target
8. **Access patterns** — No unexpected permission escalations
9. **Audit continuity** — Audit trail preserved across migration
10. **Recording preservation** — PSM recordings archived

### Compliance Frameworks (Agent 07)

Maps migration actions to controls in 4 frameworks using **data-driven check definitions** (no lambdas — serializable config):

| Framework | Control Groups |
|-----------|---------------|
| **PCI-DSS v4.0** | Access control (8.x), Audit trail (10.x), Change management (6.x) |
| **NIST 800-53 Rev5** | IA-2/4/5, AC-2/3/6, AU-2/3/6/11, CA-7, SI-4 |
| **HIPAA Security Rule** | 164.312(a)(1), 164.312(b), 164.312(c)(1), 164.312(d) |
| **SOX IT Controls** | CC6.1-3, CC7.1-2, CC8.1 |

Generates JSON reports to `output/reports/`.

### Audit Logging

All agent actions are logged as structured JSON events (JSONL format) to `output/logs/<agent_id>.audit.jsonl`:

```json
{
  "timestamp": "2026-03-03T03:16:47.853Z",
  "agent_id": "agent_01_discovery",
  "environment": "prod",
  "action": "discovery_start",
  "details": {"phase": "P1"},
  "user": "maverick",
  "session_id": "6a410ecc",
  "result": "success",
  "chain_hash": "a3f8c2...e91d04"
}
```

Every event includes a `chain_hash` — a running SHA-256 hash linking each event to its predecessor. Tampering with log entries breaks the chain, making modifications detectable during compliance audits.

Human review gate decisions are logged with `action: "human_review:<gate>"`, `approved: true/false`, `reviewer`.

---

## Test Environment & Sandbox (Next Steps Decision Point)

The system currently has **no dedicated virtual test environment**. Before running the migration pipeline for the first time, a decision is needed on the testing approach.

### What Exists Today

| Capability | What It Does | Limitations |
|-----------|-------------|-------------|
| `--dry-run` mode | Skips agent execution entirely, prints what *would* run | Does not simulate data flow, API calls, or transformation logic |
| `environment` config | Stamps `"dev"` / `"staging"` / `"prod"` into audit log entries | Metadata only — does not change runtime behavior |
| P4 Pilot (Wave 1) | Limits first batch to 50 low-risk test/dev/sandbox accounts | Hits **real APIs** — not a sandbox |

### Decision: Choose a Testing Strategy

| Option | Description | Effort | Fidelity |
|--------|-------------|--------|----------|
| **A. CyberArk Lab Instance** | Point `config.json` at a dedicated CyberArk PVWA dev/lab instance + KeeperPAM test tenant. This is the standard approach for most PAM migrations. | Low (config only) | High — real APIs, real behavior |
| **B. Mock API Server** | Build a lightweight Flask/FastAPI service that emulates CyberArk PVWA and KeeperPAM REST APIs with synthetic data. Runs locally. | Medium (~2-3 days) | Medium — tests pipeline logic, misses edge cases |
| **C. Unit Test Fixtures** | pytest suite with `unittest.mock` patching `CyberArkClient` and `KeeperClient` methods using recorded API responses. | Medium (~2-3 days) | Medium — good for CI/CD, no integration testing |
| **D. Docker Test Harness** | Docker Compose environment with mock API containers + pre-seeded state data. Full pipeline simulation in isolation. | High (~5-7 days) | High — closest to real without real CyberArk |
| **E. Hybrid (Recommended)** | Option A for integration testing + Option C for CI/CD regression testing. Use separate config files per environment. | Medium | High — covers both unit and integration |

### Recommended Approach: Hybrid (Option E)

**For integration testing** — use separate config files per environment:
```bash
python3 cli.py run P4 --config config.dev.json    # Dev PVWA + test KeeperPAM tenant
python3 cli.py run P5 --config config.prod.json   # Prod PVWA + prod KeeperPAM tenant
```

**For CI/CD and regression** — build pytest fixtures with mocked API responses:
```bash
python3 -m pytest tests/ -v                        # Run with mock clients
```

**Wave 1 is the built-in canary** — the wave classifier puts `test`, `dev`, `sandbox`, `poc`, `lab`, `demo` accounts into Wave 1 precisely so they serve as a safe first-run before touching production data.

### What Would Be Needed for Each Option

**Option A (Lab Instance)**:
- CyberArk PVWA dev/lab environment (most orgs already have one)
- Non-production KeeperPAM tenant (request from Keeper Security)
- Populate with test accounts, safes, and platforms
- Create `config.dev.json` pointing to lab URLs

**Option B (Mock API Server)**:
- Flask/FastAPI app emulating `/PasswordVault/api/*` endpoints
- Synthetic data generator (accounts, safes, members, platforms)
- Response recording/replay capability
- ~500-800 lines of Python

**Option C (Unit Test Fixtures)**:
- pytest with `unittest.mock.patch` on `CyberArkClient` and `KeeperClient`
- Recorded API response fixtures (JSON files)
- Test cases for each agent's `preflight()` and `run()` methods
- ~1,000-1,500 lines of test code

**Option D (Docker Harness)**:
- `docker-compose.yml` with mock API containers
- Pre-seeded state data volumes
- Health check endpoints
- CI pipeline integration

---

## PAM Consulting Agent

**Location:** `PAM_Consulting_Agent/`

Assessment and discovery toolkit used as the foundation for the multi-agent system. Contains:

### Key Scripts

| Script | Purpose | Lines |
|--------|---------|-------|
| `scripts/pam_autodiscovery.py` | Automated PAM discovery via CyberArk API | 322 |
| `scripts/pam_assessor.py` | Interactive 10-domain security assessment | 376 |
| `scripts/migration_validator.py` | 10-check migration validation | 1,139 |
| `scripts/nhi_discovery.py` | Non-human identity discovery from audit logs | 947 |
| `scripts/ccp_code_scanner.py` | CyberArk CCP/AAM code pattern scanner | 421 |
| `scripts/code_converter.py` | Generate Secret Server replacement code | 617 |
| `scripts/generate_wrapper.py` | Dual-backend PAM abstraction wrapper | 576 |
| `scripts/web_app.py` | Streamlit web interface | 783 |

### Subdirectories

```
scripts/
  autodiscovery/
    connectors/      CyberArkConnector, BaseConnector ABC
    collectors/      Account, Policy, Config, Component, Audit collectors
    analyzers/       Coverage, Health, NHI analyzers
    mappers/         QuestionMapper (discovery → assessment)
  assessment/
    questionnaire.py 10 domains, 50 questions (L1-L4 maturity)
    scoring.py       MaturityScorer, quick wins
    compliance.py    6-framework compliance mapper
    reporter.py      Markdown/JSON report generation
  utils/
    audit_logger.py  Structured JSON audit logging
    progress.py      ProgressTracker + ProgressBar
    input_validator.py Input validation (URLs, emails, paths, safe names)
config/
  settings.yaml      Multi-environment config
```

### Running

```bash
# Interactive assessment
python3 scripts/pam_assessor.py --interactive

# Automated discovery
python3 scripts/pam_autodiscovery.py --url https://pvwa.company.com --user admin

# NHI discovery
python3 scripts/nhi_discovery.py --audit-file audit.csv --output nhis.json

# Migration validation
python3 scripts/migration_validator.py --source cyberark.csv --target secretserver.csv

# Web interface
cd scripts && streamlit run web_app.py --server.port 8501
```

---

## PAM Migration Assistant (Standalone Scripts)

**Location:** `pam-migration-assistant/`

```bash
# Scan codebase for CyberArk dependencies
python3 scripts/ccp_code_scanner.py /path/to/code --output results.json

# Discover NHIs from audit logs
python3 scripts/nhi_discovery.py --audit-file audit.csv --output nhis.csv

# Map integration dependencies
python3 scripts/integration_mapper.py --scan /path/to/code --output integrations.csv

# Classify accounts into migration waves
python3 scripts/wave_classifier.py --accounts accounts.csv --nhis nhis.csv --output waves.csv

# Generate replacement code
python3 scripts/code_converter.py results.json --language python --output converted/

# Generate dual-backend wrapper
python3 scripts/generate_wrapper.py --language python --output pam_wrapper.py
```

### Reference Docs
- `references/api_mapping.md` — CyberArk to Secret Server API translation
- `references/permission_matrix.md` — Permission translation guide
- `references/nhi_discovery.md` — NHI identification guide

### Tests
```bash
cd pam-migration-assistant && python3 -m pytest tests/ -v
```

---

## Operational Runbook

**File:** `/mnt/c/Users/1/OneDrive/Documents/iOPEX/iOPEX_PAM_Migration_Runbook.docx`

Covers all 8 phases (P0-P7) with step-by-step instructions, checklists, and inline AI recommendations (REC-02 through REC-07):

| Phase | Name | Key Activities |
|-------|------|---------------|
| P0 | Environment Setup | Migration server, credentials, config.json, env vars |
| P1 | Discovery & Dependency Mapping | Run dependency-mapper.py, IIS log scan, manifest build |
| P2 | Infrastructure Preparation | KeeperPAM tenant, network, service accounts |
| P3 | Safe & Policy Migration | Platform policies, safe structure, master policy |
| P4 | Pilot Migration | Wave 1 test batch, PSM recording test, ServiceNow CHG |
| P5 | Production Batches | Waves 1-5, batch pipeline, CCP repointing, compliance |
| P6 | Parallel Running & Cutover | Dual operation, cutover decision, DNS/firewall |
| P7 | Decommission & Close-Out | On-prem teardown, credential rotation, final audit |

### Inline Recommendations

| Rec | Phase | Topic |
|-----|-------|-------|
| REC-02 | P1 | IIS logs miss AAM agent-mode apps — supplement with AD, CMDB, Vault audit |
| REC-03 | P4 | Test PSM recording archive before pilot (4-item checklist) |
| REC-04 | P4 | Coordinator failsafe — auto-unfreeze if API down >15 min |
| REC-05 | P5 | CCP change registry — track every config change for rollback |
| REC-06 | P0 | Security hardening — HISTCONTROL, exclude config from backups, rotate creds |
| REC-07 | P5 | API rate limits — configurable throttling, backoff on 429, benchmark step |

---

## Key Technical Details

### CyberArk REST API Endpoints Used

**On-Prem PVWA (Source):**

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/Auth/{type}/Logon` | POST | Authentication (CyberArk/LDAP/RADIUS/Windows) |
| `/Auth/Logoff` | POST | Session termination |
| `/Accounts` | GET | Account enumeration (paginated, count-based) |
| `/Accounts/{id}` | GET | Full account details (includes linked accounts) |
| `/Accounts/{id}` | PATCH | Update account properties (JSON Patch format) |
| `/Accounts/{id}/Password/Retrieve` | POST | Password retrieval (requires UseAccounts + RetrieveAccounts) |
| `/Accounts/{id}/Activities` | GET | Per-account activity logs |
| `/Safes` | GET | Safe enumeration (system safes filtered by default) |
| `/Safes/{name}/Members` | GET | Safe member/permission enumeration (URL-encoded) |
| `/Safes/{name}/Members/{member}` | PUT | Update safe member permissions |
| `/Platforms/Targets` | GET | Platform enumeration (v12+, falls back to `/Platforms`) |
| `/Platforms/{id}/Export` | POST | Export platform as ZIP package |
| `/Applications` | GET | CCP/AAM application enumeration |
| `/Applications/{id}/Authentications` | GET | Application authentication methods |
| `/Activities` | GET | Audit log retrieval (paginated) |
| `/Server/Verify` | GET | Version and health info |
| `/ComponentsMonitoringDetails` | GET | Component health monitoring |

**KeeperPAM (Target):**

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `{identity_url}/oauth2/platformtoken` | POST | OAuth2 token (client_credentials grant) |
| `/Auth/CyberArk/Logon` | POST | Legacy authentication |
| `/Safes` | POST | Safe creation |
| `/Safes/{name}` | GET | Safe lookup |
| `/Safes/{name}/Members` | POST | Add safe member with individual permissions |
| `/Safes/{name}/Members/{member}` | PUT | Update safe member permissions |
| `/Accounts` | POST | Account import |
| `/Accounts/{id}` | GET | Account details |
| `/Accounts/{id}` | DELETE | Account deletion (rollback) |
| `/Accounts/{id}/Verify` | POST | Password verification (heartbeat) |
| `/Accounts/{id}/Password/Retrieve` | POST | Password retrieval |
| `/Accounts/{id}/LinkAccount` | POST | Link logon/reconcile/index account |
| `/Platforms/Targets` | GET | Platform enumeration |
| `/Platforms/Import` | POST | Platform package import (ZIP upload) |

### NHI Detection (Multi-Signal)

Non-Human Identity detection uses 3 independent signals (most reliable first):

**Signal 1 — Platform-based** (most reliable):
Accounts on these platforms are definitionally non-human:
```
UnixSSHKeys, WinServiceAccount, WinScheduledTask,
AzureServicePrincipal, AWSAccessKeys, HashiCorpVault
```

**Signal 2 — Name-based patterns:**
```
^svc[_-]  ^app[_-]  ^api[_-]  ^bot[_-]  ^sys[_-]
^batch[_-]  ^task[_-]  ^auto[_-]  ^cron[_-]  ^rpa[_-]
service.?account  daemon  scheduler
```

**Signal 3 — Safe name patterns:**
```
appcred  servicecred  automation  cicd  pipeline
appidentit  machineidentit
```

Each NHI classification records its `detection_method` (e.g., `platform:AWSAccessKeys`, `name_pattern:^svc[_-]`, `safe_pattern:cicd`).

### Integration Detection Patterns

| Type | Patterns |
|------|----------|
| CCP/AAM | `AIMWebService`, `GetPassword`, `AppID=`, `CentralCredentialProvider`, `CredentialProvider`, `AIM agent` |
| SIEM | `syslog`, `Splunk`, `QRadar`, `Sentinel`, `CEF format` |
| Ticketing | `ServiceNow`, `SNOW`, `Jira`, `Remedy`, `change.request` |
| PSM | `PSMConnect`, `PSMServer`, `PSM recording`, `session.recording` |
| CI/CD | `Jenkins`, `Azure DevOps`, `GitLab`, `pipeline`, `Ansible vault` |
| Database | `OracleDB`, `MSSQL`, `PostgreSQL`, `MySQL`, `database rotation` |

Integration detection uses 3 sources: **Applications API** (most authoritative for CCP/AAM), **safe name patterns**, and **audit log analysis** (application access patterns).

### System Safes (Filtered by Default)

The following safes are automatically excluded from discovery and migration:
```
System, VaultInternal, VaultInternal_Node1, VaultInternal_Node2,
Notification Engine, PVWAConfig, PVWAReports, PVWATaskDefinitions,
PVWATicketingSystem, PVWAPrivateUserPrefs, PVWAPublicData,
PasswordManager, PasswordManager_ADInternal, PasswordManager_Info,
PasswordManagerShared, AccountsFeedADAccounts, AccountsFeedDiscovery,
PSM, PSMRecordings, PSMUniversalConnectors, PSMLiveSessions,
SharedAuth_Internal, PasswordManager_Pending
```

---

## Notes

- Config files with credentials (`config.json`) must never be committed — use `config.example.json` as template and set credentials via environment variables
- All timestamps are UTC ISO 8601 (`datetime.now(timezone.utc)`)
- Audit logs are JSONL format with SHA-256 hash chain for tamper evidence
- The state machine enables crash recovery via atomic writes (temp file + fsync + rename) with backup
- Raw data (accounts, safes, members, platforms) stored in `output/state/raw/` separate from the state file
- Append-only lists in state are capped (steps: 5000, errors: 1000, approvals: 500) to prevent unbounded growth
- HTTPS is enforced for all KeeperPAM connections
- SAML authentication is not supported (requires browser-based redirect flow)

# CyberArk → Delinea Secret Server Migration

Multi-Agent AI Orchestrator for migrating CyberArk PAS on-premises to Delinea Secret Server.

## Key Differences from Privilege Cloud Migration (Option B)

| Aspect | Privilege Cloud (Option B) | Secret Server (Option A) |
|--------|---------------------------|--------------------------|
| Permission model | 22 → 22 (1:1) | **22 → 4 folder roles + 200+ system role perms** |
| Data structure | Safe → Safe | Safe → Folder (hierarchical) |
| Platforms | Platform → Platform | Platform → Secret Template |
| API surface | Same `/PasswordVault/api/` | Different `/api/v1/` |
| Audit logs | Can migrate | **Do NOT transfer** |
| PSM recordings | Can migrate | **Cannot migrate** |
| Integration rework | Similar patterns | **Full re-architecture (OAuth2)** |
| CPM | CPM plugins carry over | RPC plugins must be rebuilt per template |

---

## Quick Start

```bash
cd "Secret Server migration"
cp config.example.json config.json     # Fill in CyberArk + Secret Server URLs
# Set credentials via environment variables (recommended):
export CYBERARK_USERNAME="svc-migration"
export CYBERARK_PASSWORD="..."
export SS_CLIENT_ID="..."
export SS_CLIENT_SECRET="..."

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
build_docx.py                   Styled .docx documentation generator (APM Terminals format)
.gitignore                      Excludes config.json, credentials, output/, __pycache__/

core/
  base.py                       AgentBase ABC + AgentResult dataclass (status validation, approval timeout)
  state.py                      MigrationState — atomic writes, file locking, backup recovery
  logging.py                    AuditLogger — SHA-256 hash chain, SIEM-ready JSONL
  cyberark_client.py            CyberArk PVWA REST client (context manager, env var credentials)
  secret_server_client.py       Delinea Secret Server REST client (OAuth2 + legacy, folders/secrets/templates)
  source_adapters.py            Multi-vendor source adapters (CyberArk, BeyondTrust, SS, HashiCorp, AWS, Azure, GCP)

agents/
  agent_01_discovery.py         Discovery & Dependency Mapping (Applications API, multi-signal NHI)
  agent_02_gap_analysis.py      Gap Analysis (10 domains + SS template readiness + permission model risk)
  agent_03_permissions.py       Permission Translation — 22→4 LOSSY (escalation detection, loss tracking)
  agent_04_etl.py               Migration Pipeline — Safe→Folder, Platform→Template, Account→Secret (dependency/staging/NHI gates)
  agent_05_heartbeat.py         Heartbeat & Validation (10 checks + SS heartbeat API + RPC + audit continuity)
  agent_06_integration.py       Integration Repointing (CCP/AAM → SS REST API + OAuth2 replacement code)
  agent_07_compliance.py        Compliance & Audit (PCI-DSS, NIST 800-53, HIPAA, SOX + SS-specific risks)
  agent_08_runbook.py           Runbook Execution (SS-specific phase gates + human approvals)
  agent_09_dependency_mapper.py Dependency Mapper (IIS, Windows services, scheduled tasks, Jenkins, scripts, configs)
  agent_10_staging.py           Staging Validation (10 assertions against SS staging instance, rollback)
  agent_11_source_adapter.py    Multi-Vendor Source Adapter (BeyondTrust, SS, HashiCorp, cloud vaults)
  agent_12_nhi_handler.py       NHI Handler (7 NHI subtypes, weighted classification, per-type strategies)
  agent_13_platform_plugins.py  Platform Plugin Validator (CyberArk platforms → SS templates, auto-create)
  agent_14_onboarding.py        App Onboarding Factory (SS folders/templates/secrets pipeline)
  agent_15_hybrid_fleet.py      Hybrid Fleet Manager (on-prem CyberArk + SS during parallel running)

config.example.json             CyberArk source + Secret Server target config template
agent_config.json               Agent-specific settings (thresholds, batch sizes, platform→template map)
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
| P1 | Discovery, Dependency Mapping, NHI Classification | 11, 01, 09, 12, 02, 03 | Review discovery + deps + NHI + gaps + permission loss (22→4) |
| P2 | Infrastructure, Template Validation, Staging | 13, 10 | Approve staging results |
| P3 | Folder & Template Migration, App Onboarding Setup | 03, 14 | Approve folder structure and permission mapping plan |
| P4 | Pilot Migration | 04, 05 | Approve pilot results before production waves |
| P5 | Production Batches | 04, 05, 06, 14, 07 | Approve all production batch results |
| P6 | Parallel Running & Cutover | 15, 05, 06, 07 | Approve cutover (decommission CyberArk read-only) |
| P7 | Decommission & Close-Out | 07 | Final sign-off (confirm CyberArk audit archive complete) |

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
Agent 02 (Gap Analysis)  →  maturity scores, compliance gaps, template coverage, permission model risk
       ↓
Agent 03 (Permissions)  →  22→4 role translations, escalation risks, lost permissions, loss report
       ↓
Agent 13 (Platform Plugins)  →  template validation, custom plugin deployment
       ↓
Agent 10 (Staging)  →  10-assertion staging validation, rollback, production gate
       ↓
Agent 14 (Onboarding)  →  new app onboarding pipeline (folder/permissions/secret/rotation/heartbeat)
       ↓
Agent 04 (Migration Pipeline)  →  batch migration results (per wave: freeze/export/transform/folders/import/heartbeat/unfreeze)
       ↓
Agent 05 (Heartbeat)  →  10-check validation report (count, heartbeat, permissions, folders, RPC, audit)
       ↓
Agent 06 (Integration)  →  CCP/AAM scan results, SS REST API replacement code templates, change registry
       ↓
Agent 07 (Compliance)  →  compliance report (PCI-DSS, NIST, HIPAA, SOX) + SS-specific risk tracking
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
| `SS_CLIENT_ID` | Secret Server OAuth2 client ID |
| `SS_CLIENT_SECRET` | Secret Server OAuth2 client secret |
| `SS_USERNAME` | Secret Server username (legacy auth only) |
| `SS_PASSWORD` | Secret Server password (legacy auth only) |

Passwords are **zeroed from memory** immediately after the authentication attempt. On token expiry (HTTP 401), credentials are re-read from environment variables for re-authentication. Proactive re-auth triggers when the token is within 60 seconds of expiry.

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
| `secret_server.base_url` | Secret Server URL (e.g., `https://secretserver.company.com/SecretServer`) |
| `secret_server.auth_method` | `"oauth2"` (modern, recommended) or `"legacy"` (username/password grant) |
| `secret_server.batch_size` | Import pagination size (default: `500`, max: `1000`) |
| `secret_server.default_folder_id` | Root folder ID for imports (default: `-1` for root) |
| `secret_server.inherit_permissions` | Folders inherit parent permissions (default: `true`) |
| `servicenow.instance_url` | ServiceNow instance for change requests |
| `output_dir` | Output directory (default: `"./output"`) |
| `log_level` | Logging level (default: `"INFO"`) |
| `environment` | Environment context: `"dev"` / `"staging"` / `"prod"` |

**OAuth2 authentication** (modern Secret Server):
```
Token URL: {base_url}/oauth2/token
Grant type: client_credentials
Format: https://secretserver.company.com/SecretServer
```

**Legacy authentication** (username/password):
```
Token URL: {base_url}/oauth2/token
Grant type: password
Uses SS_USERNAME + SS_PASSWORD environment variables
```

**`agent_config.json`** (agent-specific tuning):

| Agent | Key Settings |
|-------|-------------|
| `agent_01_discovery` | `scan_directories`, `integration_types`, `include_audit_logs`, `audit_log_days` |
| `agent_02_gap_analysis` | `compliance_frameworks`, `maturity_threshold`, `auto_score` |
| `agent_03_permissions` | `skip_members` (built-in accounts to skip) |
| `agent_04_etl` | `batch_size` (500), `freeze_window_minutes` (120), `rate_limit_per_minute` (100), `watchdog_timeout_minutes`, `wave_order`, `default_parent_folder` ("Imported"), `platform_template_map` |
| `agent_05_heartbeat` | `count_variance_threshold` (0.01), `success_threshold` (0.95) |
| `agent_06_integration` | `supported_languages`, `scan_directories` |
| `agent_07_compliance` | `frameworks` (data-driven check definitions) |
| `agent_08_runbook` | `require_approval_for_phases`, `auto_advance` |
| `agent_09_dependency_mapper` | `scan_iis_logs`, `iis_log_paths`, `deep_scan_directories`, `dependency_confidence_threshold` |
| `agent_10_staging` | `staging_folder_prefix`, `test_secret_count`, `assertion_timeout_seconds`, `auto_rollback` |
| `agent_11_source_adapter` | `source_type` (cyberark/beyondtrust/hashicorp/aws/azure/gcp), `source_config`, `normalize_names` |
| `agent_12_nhi_handler` | `nhi_confidence_threshold` (0.6), `platform_weight`, `name_weight`, `dependency_weight`, `rotation_defaults` |
| `agent_13_platform_plugins` | `template_mapping_overrides`, `validate_rpc_components`, `custom_launcher_dir` |
| `agent_14_onboarding` | `parent_folder`, `pending_requests`, `default_rotation_days` (30), `verify_heartbeat` |
| `agent_15_hybrid_fleet` | `parallel_read_percentage` (10), `cutover_threshold` (0.99), `rollback_on_failure`, `traffic_routing_mode` |

---

### Security Features

#### Secrets Management
- Credentials loaded from **environment variables** (preferred) with config.json fallback
- Passwords **zeroed from memory** after authentication (`self._client_secret = None`, `self._password = None`)
- Error messages **sanitized** via `_safe_error()` — strips passwords, secrets, tokens from HTTP error text
- `config.json` excluded via `.gitignore` — only `config.example.json` is committed

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

#### Proactive Token Refresh
The Secret Server client re-authenticates when the token is within 60 seconds of expiry, preventing mid-operation authentication failures.

---

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

---

### Permission Translation (Agent 03) — LOSSY

CyberArk uses 22 individual safe member permissions. Secret Server uses a 4-tier role model (Owner, Edit, View, List). This translation is inherently **LOSSY** — 9 CyberArk permissions have NO Secret Server equivalent, and some members will receive MORE access than they had before.

**All 22 CyberArk Safe Permissions**:
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

**Secret Server 4-Tier Role Model**:

| SS Role | Grants | CyberArk Trigger Permissions |
|---------|--------|------------------------------|
| **Owner** | Full admin — manage folder and member access | Requires BOTH `ManageSafe` AND `ManageSafeMembers` |
| **Edit** | Create/modify/delete secrets in the folder | Any of: `AddAccounts`, `UpdateAccountContent`, `UpdateAccountProperties`, `DeleteAccounts`, `RenameAccounts`, `UnlockAccounts` |
| **View** | View and retrieve secret values | Any of: `UseAccounts`, `RetrieveAccounts` |
| **List** | See that secrets exist (no value access) | Any of: `ListAccounts`, `ViewSafeMembers`, `ViewAuditLog` |

**Permissions with NO Secret Server Equivalent (Always Lost)**:

| CyberArk Permission | Why It's Lost |
|---------------------|---------------|
| `AccessWithoutConfirmation` | SS uses Workflow templates instead of dual-control bypass |
| `SpecifyNextAccountContent` | SS RPC sets passwords automatically — no manual setter |
| `BackupSafe` | Folder backup is a server-level operation in SS |
| `CreateFolders` | SS folder permissions are inherited, not per-member |
| `DeleteFolders` | SS folder permissions are inherited, not per-member |
| `MoveAccountsAndFolders` | SS move is a separate admin permission, not folder-level |
| `RequestsAuthorizationLevel1` | SS uses Workflow templates — different approval model |
| `RequestsAuthorizationLevel2` | SS uses Workflow templates — different approval model |
| `InitiateCPMAccountManagementOperations` | SS RPC is all-or-nothing per template, not per-member |

**Escalation Risks (Over-Provisioning)**:

| Scenario | CyberArk Original | SS Result | Risk |
|----------|-------------------|-----------|------|
| View→Edit escalation | UseAccounts + RetrieveAccounts + UnlockAccounts | Edit role (full create/modify/delete) | Member gets secret creation and deletion — only had view + unlock |
| Admin-only→Full Owner | ManageSafe + ManageSafeMembers (no data permissions) | Owner role (full secret access) | Admin who could not see passwords now has full access to all secrets |

Built-in members (`Master`, `Batch`, `Backup Users`, `DR Users`, `Auditors`, `Operators`) are automatically skipped.

Phase P1 produces the analysis report. Phase P3 applies permissions to Secret Server via `set_folder_permission()` with `folderAccessRoleName` and `secretAccessRoleName`, handling 409 conflicts (already exists) by skipping.

---

### Migration Pipeline (Agent 04)

Each batch executes 7 steps in sequence with **real API calls**:

```
1. FREEZE           — Disable CPM automatic management (PATCH /Accounts/{id})
2. EXPORT           — Pull full account details + retrieve passwords from CyberArk
3. TRANSFORM        — Map CyberArk fields to Secret Server schema
4. FOLDER CREATION  — Create folder hierarchy in Secret Server (/Imported/{SafeName})
5. IMPORT           — Push secrets with retry + rate limiting (POST /api/v1/secrets)
6. HEARTBEAT        — Trigger password verification (POST /api/v1/secrets/{id}/heartbeat)
7. UNFREEZE         — Re-enable CPM management for all frozen accounts
```

**Field mapping (CyberArk → Secret Server)**:

| CyberArk Field | Secret Server Field | Notes |
|----------------|--------------------|-|
| `name` | `name` | Secret display name |
| `userName` | `username` (slug) | Template field item |
| `address` | `machine` (slug) | Template field item |
| `_password` | `password` (slug) | Retrieved via CyberArk API, set via template field |
| `safeName` | `folderId` | Mapped via folder creation step |
| `platformId` | `secretTemplateId` | Mapped via platform→template lookup |
| `platformAccountProperties` | `notes` (slug) | Preserved as key: value text in notes field |

**Key implementation details:**
- **Password retrieval**: `POST /Accounts/{id}/Password/Retrieve` — accounts where retrieval fails are skipped (not imported with empty secrets)
- **Folder hierarchy**: Parent "Imported" folder created at root, then per-safe child folders underneath
- **Template lookup**: Pre-caches all SS template IDs at batch start. Unmapped platforms cause transform failure.
- **Conflict handling**: HTTP 409 on import treated as idempotent success (already exists)
- **Failure threshold**: >10% batch failure = batch marked as `"failed"`, otherwise `"partial"`
- **Both clients** use context managers (`with CyberArkClient() as source, SecretServerClient() as target:`) to prevent connection leaks
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

---

### Platform → Template Mapping

CyberArk Platforms must be mapped to Secret Server Templates before migration. The migration pipeline agent uses this mapping during the transform step.

| CyberArk Platform | Secret Server Template | Notes |
|-------------------|----------------------|-------|
| `WinServerLocal` | Windows Account | Local administrator accounts |
| `WinDomain` | Active Directory Account | Domain service accounts |
| `WinServiceAccount` | Windows Service Account | Windows service credentials |
| `UnixSSH` | Unix Account (SSH) | Standard SSH password auth |
| `UnixSSHKeys` | Unix Account (SSH Key Rotation) | SSH key-based authentication |
| `Oracle` | Oracle Account | Oracle database credentials |
| `MSSql` | SQL Server Account | Microsoft SQL Server |
| `MySQL` | MySQL Account | MySQL database credentials |
| `AzureServicePrincipal` | Azure Service Principal | Azure AD app registrations |
| `AWSAccessKeys` | Amazon IAM Key | AWS IAM access keys |
| *(custom)* | *(custom template required)* | Must create SS template before migration |

Custom CyberArk platforms that do not appear in this mapping require manual Secret Server template creation. Agent 02 (Gap Analysis) identifies these gaps during Phase P1.

---

### Validation Checks (Agent 05)

10 post-migration checks run after every batch:

1. **Count comparison** — Source account count vs target secret count within threshold
2. **Heartbeat status** — All imported secrets have valid credentials (`POST /api/v1/secrets/{id}/heartbeat`)
3. **Permission mapping** — 22→4 translations applied, escalation risks flagged
4. **Folder structure** — Safe→Folder hierarchy preserved (`/Imported/{SafeName}`)
5. **Metadata integrity** — Descriptions and custom fields intact (preserved in notes field)
6. **Group assignments** — User/group folder permission mappings verified
7. **Password policies** — WARNING: RPC must be manually configured per Secret Server template
8. **Access patterns** — Flags >30% Edit/Owner roles as potential over-provisioning from role collapse
9. **Audit continuity** — WARNING: CyberArk audit history does NOT migrate to Secret Server
10. **Recording preservation** — WARNING: PSM session recordings cannot be migrated to SS

---

### Integration Repointing (Agent 06)

CyberArk CCP/AAM integrations require a **full re-architecture** to use Secret Server's REST API. This is NOT a URL swap.

| CyberArk Pattern | Secret Server Replacement |
|-------------------|--------------------------|
| `GET /AIMWebService/api/Accounts?AppID=X&Safe=Y&Object=Z` | `POST /oauth2/token` + `GET /api/v1/secrets/{id}/fields/password` |
| AppID-based authentication | OAuth2 client credentials (Bearer token) |
| psPAS / `Get-PASAccount` (PowerShell) | `Thycotic.SecretServer` module / `Get-TssSecret` |
| `CyberArk.AIM.NetPasswordSDK` (.NET) | `HttpClient` + OAuth2 + `/api/v1/secrets` |
| `com.cyberark.aim` (Java) | `HttpClient` + OAuth2 + `/api/v1/secrets` |

Agent 06 scans configured directories for CyberArk CCP patterns and generates language-specific replacement code templates (Python, PowerShell, C#, Java).

---

### Compliance Frameworks (Agent 07)

Maps migration actions to controls in 4 frameworks using **data-driven check definitions** (no lambdas — serializable config):

| Framework | Control Groups |
|-----------|---------------|
| **PCI-DSS v4.0** | Access control (8.x), Audit trail (10.x), Change management (6.x), Permission integrity (22→4 loss risk) |
| **NIST 800-53 Rev5** | IA-2/4/5, AC-2/3/6, AU-2/3/6/11, CA-7, SI-4 |
| **HIPAA Security Rule** | 164.312(a)(1), 164.312(b), 164.312(c)(1), 164.312(d) |
| **SOX IT Controls** | CC6.1-3, CC7.1-2, CC8.1 |

Generates JSON reports to `output/reports/`.

**SS-Specific Compliance Risks** (documented in every compliance report):

| Risk | Severity | Description | Mitigation |
|------|----------|-------------|------------|
| Audit Log Discontinuity | HIGH | CyberArk audit history does NOT transfer to SS | Maintain CyberArk read-only for audit retention; document gap for auditors |
| Permission Model Simplification | HIGH | 22→4 collapse with escalation risk | Review Agent 03 loss report; consider SS Workflow templates for dual-control |
| PSM Session Recording Loss | MEDIUM | PSM recordings cannot migrate to SS | Archive recordings before decommission; maintain CyberArk read-only |

---

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
| P4 Pilot (Wave 1) | Limits first batch to low-risk test/dev/sandbox accounts | Hits **real APIs** — not a sandbox |

### Decision: Choose a Testing Strategy

| Option | Description | Effort | Fidelity |
|--------|-------------|--------|----------|
| **A. Lab Instance** | Point `config.json` at a CyberArk PVWA dev/lab + Secret Server test instance | Low (config only) | High — real APIs, real behavior |
| **B. Mock API Server** | Build a Flask/FastAPI service emulating PVWA + SS APIs with synthetic data | Medium (~2-3 days) | Medium — tests pipeline logic, misses edge cases |
| **C. Unit Test Fixtures** | pytest suite with `unittest.mock` patching `CyberArkClient` and `SecretServerClient` using recorded API responses | Medium (~2-3 days) | Medium — good for CI/CD, no integration testing |
| **D. Docker Test Harness** | Docker Compose environment with mock API containers + pre-seeded state data | High (~5-7 days) | High — closest to real without real CyberArk/SS |
| **E. Hybrid (Recommended)** | Option A for integration testing + Option C for CI/CD regression testing | Medium | High — covers both unit and integration |

### Recommended Approach: Hybrid (Option E)

**For integration testing** — use separate config files per environment:
```bash
python3 cli.py run P4 --config config.dev.json    # Dev PVWA + test SS instance
python3 cli.py run P5 --config config.prod.json   # Prod PVWA + prod SS instance
```

**For CI/CD and regression** — build pytest fixtures with mocked API responses:
```bash
python3 -m pytest tests/ -v                        # Run with mock clients
```

**Wave 1 is the built-in canary** — the wave classifier puts `test`, `dev`, `sandbox`, `poc`, `lab`, `demo` accounts into Wave 1 precisely so they serve as a safe first-run before touching production data.

### What Would Be Needed for Each Option

**Option A (Lab Instance)**:
- CyberArk PVWA dev/lab environment (most orgs already have one)
- Secret Server test instance (on-prem or cloud-hosted)
- Populate with test accounts, safes, folders, and templates
- Create `config.dev.json` pointing to lab URLs

**Option B (Mock API Server)**:
- Flask/FastAPI app emulating `/PasswordVault/api/*` + `/api/v1/*` endpoints
- Synthetic data generator (accounts, safes, folders, secrets, templates)
- Response recording/replay capability
- ~500-800 lines of Python

**Option C (Unit Test Fixtures)**:
- pytest with `unittest.mock.patch` on `CyberArkClient` and `SecretServerClient`
- Recorded API response fixtures (JSON files)
- Test cases for each agent's `preflight()` and `run()` methods
- ~1,000-1,500 lines of test code

**Option D (Docker Harness)**:
- `docker-compose.yml` with mock API containers
- Pre-seeded state data volumes
- Health check endpoints
- CI pipeline integration

---

## API Endpoints

### CyberArk On-Prem PVWA (Source)

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/Auth/{type}/Logon` | POST | Authentication (CyberArk/LDAP/RADIUS/Windows) |
| `/Auth/Logoff` | POST | Session termination |
| `/Accounts` | GET | Account enumeration (paginated, count-based) |
| `/Accounts/{id}` | GET | Full account details (includes linked accounts) |
| `/Accounts/{id}` | PATCH | Update account properties (JSON Patch format) |
| `/Accounts/{id}/Password/Retrieve` | POST | Password retrieval (requires UseAccounts + RetrieveAccounts) |
| `/Safes` | GET | Safe enumeration (system safes filtered by default) |
| `/Safes/{name}/Members` | GET | Safe member/permission enumeration (URL-encoded) |
| `/Platforms/Targets` | GET | Platform enumeration (v12+, falls back to `/Platforms`) |
| `/Applications` | GET | CCP/AAM application enumeration |
| `/Applications/{id}/Authentications` | GET | Application authentication methods |
| `/Activities` | GET | Audit log retrieval (paginated) |
| `/Server/Verify` | GET | Version and health info |
| `/ComponentsMonitoringDetails` | GET | Component health monitoring |

### Delinea Secret Server (Target)

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/oauth2/token` | POST | OAuth2 token (client_credentials or password grant) |
| `/api/v1/folders` | GET | Folder enumeration (hierarchical, getAllChildren) |
| `/api/v1/folders` | POST | Folder creation (parent ID, permission inheritance) |
| `/api/v1/folders/{id}` | GET | Folder details |
| `/api/v1/folder-permissions` | GET | Folder permission enumeration |
| `/api/v1/folder-permissions` | POST | Set folder permission (folderAccessRoleName + secretAccessRoleName) |
| `/api/v1/folder-permissions/{id}` | PUT | Update folder permission |
| `/api/v1/secrets` | GET | Secret enumeration (paginated, take/skip) |
| `/api/v1/secrets` | POST | Secret creation (template ID + field items) |
| `/api/v1/secrets/{id}` | GET | Full secret details |
| `/api/v1/secrets/{id}` | DELETE | Secret deletion (rollback) |
| `/api/v1/secrets/{id}/fields/password` | GET | Password retrieval |
| `/api/v1/secrets/{id}/fields/password` | PUT | Password update |
| `/api/v1/secrets/{id}/heartbeat` | POST | Trigger heartbeat (password verification via RPC) |
| `/api/v1/secrets/{id}/state` | GET | Heartbeat/RPC status |
| `/api/v1/secret-templates` | GET | Template enumeration |
| `/api/v1/secret-templates` | POST | Template creation |
| `/api/v1/secret-templates/{id}` | GET | Template details |
| `/api/v1/users` | GET | User enumeration |
| `/api/v1/groups` | GET | Group enumeration |
| `/api/v1/roles` | GET | Role enumeration |
| `/api/v1/distributed-engine/sites` | GET | Distributed engine site enumeration |
| `/api/v1/version` | GET | Server version and health |

---

## NHI Detection (Multi-Signal)

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

---

## Integration Detection Patterns

| Type | Patterns |
|------|----------|
| CCP/AAM | `AIMWebService`, `GetPassword`, `AppID=`, `CentralCredentialProvider`, `CredentialProvider`, `AIM agent` |
| SIEM | `syslog`, `Splunk`, `QRadar`, `Sentinel`, `CEF format` |
| Ticketing | `ServiceNow`, `SNOW`, `Jira`, `Remedy`, `change.request` |
| PSM | `PSMConnect`, `PSMServer`, `PSM recording`, `session.recording` |
| CI/CD | `Jenkins`, `Azure DevOps`, `GitLab`, `pipeline`, `Ansible vault` |
| Database | `OracleDB`, `MSSQL`, `PostgreSQL`, `MySQL`, `database rotation` |

Integration detection uses 3 sources: **Applications API** (most authoritative for CCP/AAM), **safe name patterns**, and **audit log analysis** (application access patterns).

---

## System Safes (Filtered by Default)

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

## Documentation Generation

Generate the styled .docx (APM Terminals format — dark navy headers, alternating row shading, 22 sections):

```bash
python3 build_docx.py
```

Output: `Secret_Server_Migration_Agent_System_Documentation.docx` (also copies to OneDrive)

---

## Notes

- Config files with credentials (`config.json`) must never be committed — use `config.example.json` as template and set credentials via environment variables
- All timestamps are UTC ISO 8601 (`datetime.now(timezone.utc)`)
- Audit logs are JSONL format with SHA-256 hash chain for tamper evidence
- The state machine enables crash recovery via atomic writes (temp file + fsync + rename) with backup
- Raw data (accounts, safes, members, platforms) stored in `output/state/raw/` separate from the state file
- Append-only lists in state are capped (steps: 5000, errors: 1000, approvals: 500) to prevent unbounded growth
- SAML authentication is not supported for CyberArk source (requires browser-based redirect flow)

# Secret Server Migration — Option B (Delinea Secret Server)

15-agent AI orchestrator for migrating CyberArk PAS on-premises → Delinea Secret Server.

## Stack
- **Language**: Python 3.12+
- **Dependencies**: `requests`, `urllib3`, `python-docx`
- **Auth source**: CyberArk PVWA (LDAP/RADIUS/Windows)
- **Auth target**: Secret Server OAuth2 (`/oauth2/token`, client_credentials grant)
- **State**: JSON-backed atomic writes with SHA-256 audit chain
- **Credentials**: Environment variables (never config files)

## Key Files
```
coordinator.py              Main orchestrator — sequences agents per phase
cli.py                      CLI entry point
core/
  base.py                   AgentBase ABC + AgentResult
  state.py                  MigrationState — atomic writes, file locking
  logging.py                AuditLogger — SHA-256 hash chain, SIEM-ready JSONL
  cyberark_client.py        PVWA REST client (source)
  secret_server_client.py   Delinea SS REST client (target, OAuth2 + legacy)
  source_adapters.py        Multi-vendor adapters
agents/                     15 agents (agent_01 through agent_15)
config.example.json         Connection config template (copy → config.json, never commit)
agent_config.json           Agent settings + platform→template mapping
output/                     Runtime output — gitignored
```

## Run Commands
```bash
cp config.example.json config.json   # then edit with real URLs
python3 cli.py preflight
python3 cli.py start my-migration-001
python3 cli.py run P1 --dry-run
python3 cli.py run P1
python3 cli.py status
```

## Key Differences vs Option A (Privilege Cloud)
| Aspect | Option A | Option B |
|--------|----------|----------|
| Permission model | 22 → 22 (1:1) | **22 → 4 roles (LOSSY)** |
| Data structure | Safe → Safe | Safe → Folder (hierarchical) |
| Platforms | Platform → Platform | Platform → Secret Template |
| Audit logs | Can migrate | **Do NOT transfer** |
| PSM recordings | Can migrate | **Cannot migrate** |
| Integration rework | Similar | **Full re-architecture (OAuth2)** |

## Permission Loss (22 → 4 Roles)
- **9 permissions have NO SS equivalent** (always lost): AccessWithoutConfirmation, SpecifyNextAccountContent, BackupSafe, CreateFolders, DeleteFolders, MoveAccountsAndFolders, RequestsAuthorizationLevel1/2, InitiateCPMAccountManagementOperations
- Agent 03 produces loss report per member — **MUST be reviewed before P3**
- Escalation detection: flags members getting MORE access than they had

## Platform → Template Mapping
WinServerLocal → Windows Account | WinDomain → Active Directory Account
UnixSSH → Unix Account (SSH) | UnixSSHKeys → Unix Account (SSH Key Rotation)
Oracle/MSSql/MySQL → DB-specific templates | AzureServicePrincipal → Azure Service Principal
Custom platforms require manual SS template creation (flagged by Agent 02)

## Environment Variables
See `.env` — required: `CYBERARK_USERNAME`, `CYBERARK_PASSWORD`, `SS_CLIENT_ID`, `SS_CLIENT_SECRET`

## CRISP-E Persona

> **C (Context):** iOPEX is executing a CyberArk PAS on-premises → Delinea Secret Server migration. This is a cross-vendor migration — the permission model is LOSSY (22→4 roles), audit logs cannot transfer, PSM recordings are lost, and all integrations require full OAuth2 re-architecture. Every decision has a documented compliance consequence.
> **R (Role):** You are the Secret Server Migration Orchestrator — a 15-agent AI system that sequences discovery, gap analysis, lossy permission translation, ETL, and integration repointing from CyberArk to Secret Server.
> **I (Intent):** Execute the migration with zero secret loss and full documentation of every permission compromise. The Agent 03 loss report MUST be human-reviewed before P3. No silent data loss is acceptable.
> **S (Scope):** Source: CyberArk PVWA on-prem. Target: Delinea Secret Server. Covers P0–P7. Does NOT cover post-migration BAU or Secret Server RPC plugin rebuilds (manual).
> **P (Persona/Style):** Conservative, compliance-first, explicit about lossy operations. Always surfaces permission loss counts and escalation risks before proceeding. Never silently drops data.
> **E (Examples):** "Run permission mapping" → Agent 03 produces per-member loss report showing 9 lost permissions and any escalation risks. "ETL status" → reports FREEZE/EXPORT/TRANSFORM/FOLDER CREATION/IMPORT/HEARTBEAT/UNFREEZE with folder hierarchy and template mappings applied.

## Security Rules
- `config.json` is gitignored — NEVER commit it
- Set credentials via env vars, not config files
- Proactive token refresh: re-auth 60s before SS token expiry

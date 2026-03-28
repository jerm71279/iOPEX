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

## Security Rules
- `config.json` is gitignored — NEVER commit it
- Set credentials via env vars, not config files
- Proactive token refresh: re-auth 60s before SS token expiry

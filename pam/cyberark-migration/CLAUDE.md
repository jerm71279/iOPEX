# CyberArk Migration — Option A (Privilege Cloud)

15-agent AI orchestrator for migrating CyberArk PAS on-premises → CyberArk Privilege Cloud.

## Stack
- **Language**: Python 3.12+
- **Dependencies**: `requests`, `urllib3`, `python-docx`
- **Auth source**: CyberArk PVWA (LDAP/RADIUS/Windows)
- **Auth target**: Privilege Cloud OAuth2 (CyberArk Identity `/oauth2/platformtoken`)
- **State**: JSON-backed atomic writes with SHA-256 audit chain
- **Credentials**: Environment variables (never config files)

## Key Files
```
coordinator.py              Main orchestrator — sequences agents per phase
cli.py                      CLI entry point
core/
  base.py                   AgentBase ABC + AgentResult
  state.py                  MigrationState — atomic writes, file locking, backup recovery
  logging.py                AuditLogger — SHA-256 hash chain, SIEM-ready JSONL
  cyberark_client.py        PVWA REST client (source system)
  cloud_client.py           Privilege Cloud REST client (target)
  source_adapters.py        Multi-vendor adapters (BeyondTrust, SS, HashiCorp, AWS, Azure, GCP)
agents/                     15 agents (agent_01 through agent_15)
config.example.json         Connection config template (copy → config.json, never commit)
agent_config.json           Agent-specific settings (thresholds, batch sizes)
output/                     Runtime output (logs/, reports/, state/) — gitignored
```

## Run Commands
```bash
cp config.example.json config.json   # then edit with real URLs
python3 cli.py preflight             # verify connectivity
python3 cli.py start my-migration-001
python3 cli.py run P1 --dry-run
python3 cli.py run P1
python3 cli.py status
```

## Migration Phases
| Phase | Focus | Agents |
|-------|-------|--------|
| P1 | Discovery, Dependency Mapping, NHI Classification | 11, 01, 09, 12, 02, 03 |
| P2 | Infrastructure, Platform Validation, Staging | 13, 10 |
| P3 | Safe & Policy Migration, App Onboarding Setup | 03, 14 |
| P4 | Pilot Migration | 04, 05 |
| P5 | Production Batches (Waves 1–5) | 04, 05, 06, 14, 07 |
| P6 | Parallel Running & Cutover | 15, 05, 06, 07 |
| P7 | Decommission & Close-Out | 07 |

## Key Technical Details
- Permission model: 22 → 22 (1:1, no loss)
- ETL: FREEZE → EXPORT → TRANSFORM → SAFE CREATION → IMPORT → HEARTBEAT → UNFREEZE
- NHI detection: 3 signals (platform type, name patterns, safe name patterns)
- Watchdog: auto-unfreezes vault on timeout (120 min default) or any exception
- Audit logs: JSONL + SHA-256 hash chain (tamper-evident, SIEM-ready)

## Environment Variables
See `.env` — required: `CYBERARK_USERNAME`, `CYBERARK_PASSWORD`, `PCLOUD_CLIENT_ID`, `PCLOUD_CLIENT_SECRET`

## Security Rules
- `config.json` is gitignored — NEVER commit it
- Set credentials via env vars, not config files
- All timestamps UTC ISO 8601
- Passwords zeroed from memory after auth

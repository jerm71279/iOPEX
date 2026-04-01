# Runbook P2 — Platform Validation & Staging
## CyberArk → KeeperPAM Migration | SHIFT System

**Scope:** Validate platform/record type parity between source and target. Run a full mini-ETL against the KeeperPAM staging tenant. All 10 assertions must pass before P3.
**Duration:** 2–3 weeks
**Prerequisite:** P1 complete, YC-P1 gate approved.
**Who runs this:** iOPEX delivery engineer

**Agent sequence:** `13-platform-plugins` → `10-staging`

---

## P2 Checklist

- [ ] KeeperPAM staging tenant provisioned (separate from production)
- [ ] Staging tenant URL added to config
- [ ] Platform/record type comparison complete
- [ ] All missing custom platforms imported to staging
- [ ] Staging ETL run complete
- [ ] All 10 staging assertions passed
- [ ] Staging data rolled back (clean)

---

## Step 1 — Configure Staging Tenant

The staging run requires a dedicated KeeperPAM tenant (NOT production). Add to `config.json`:

```json
{
  "keeperpam": {
    "base_url": "https://keepersecurity.com",
    "auth_method": "oauth2",
    "verify_ssl": true,
    "timeout": 30,
    "batch_size": 500
  },
  "keeperpam_staging": {
    "base_url": "https://staging.keepersecurity.com",
    "auth_method": "oauth2",
    "verify_ssl": true,
    "timeout": 30,
    "batch_size": 100
  }
}
```

> **Critical:** Agent 10 has a hard check — if staging URL matches production URL, it **HARD BLOCKs** and refuses to run. This prevents staging data contaminating production.

---

## Run P2 (Full Automated Sequence)

```bash
# Dry run
az containerapp exec \
  --name "$APP_NAME" --resource-group "$RG" \
  --command "python3 cli.py run P2 --dry-run"

# Live run
az containerapp exec \
  --name "$APP_NAME" --resource-group "$RG" \
  --command "python3 cli.py run P2"
```

---

## Agent 13 — Platform Plugin Validator

Compares CyberArk platforms used by migrating accounts against KeeperPAM record types.

```bash
az containerapp exec \
  --name "$APP_NAME" --resource-group "$RG" \
  --command "python3 cli.py agent 13-platform-plugins"
```

### What it does (P2):
1. Reads platform list from P1 discovery data
2. Calls CyberArk `GET /Platforms/Targets` to get source platform definitions
3. Calls KeeperPAM `GET /record-types` to list available target record types
4. Compares: identifies missing record types in KeeperPAM
5. For missing built-in platforms — exports from CyberArk and imports to KeeperPAM
6. For custom platforms — flags for manual rebuild (cannot auto-migrate)

**Built-in platform → KeeperPAM record type mapping:**
| CyberArk Platform | KeeperPAM Record Type |
|-------------------|-----------------------|
| WinServerLocal | Windows Account |
| WinDomain | Active Directory Account |
| UnixSSH | Unix Account (SSH) |
| UnixSSHKeys | Unix Account (SSH Key Rotation) |
| Oracle | Oracle Database Account |
| MSSql | SQL Server Account |
| MySQL | MySQL Account |
| AWSAccessKeys | Amazon IAM Key |
| AzureServicePrincipal | Azure Service Principal |

**Review results:**
```bash
az containerapp exec \
  --name "$APP_NAME" --resource-group "$RG" \
  --command "cat output/reports/agent_13_platform_plugins_P2.json | python3 -c \"
import json, sys
data = json.load(sys.stdin)
print('Source platforms:', data.get('source_platform_count'))
print('Target record types:', data.get('target_record_type_count'))
print('Missing (auto-imported):', data.get('auto_imported_count'))
missing_custom = data.get('manual_rebuild_required', [])
if missing_custom:
    print(f'MANUAL REBUILD REQUIRED ({len(missing_custom)}):')
    for p in missing_custom:
        print(f'  - {p}')
\""
```

**⚠ Custom platforms flagged as `manual_rebuild_required` must be rebuilt as KeeperPAM record types by the client before P3.**

---

## Agent 10 — Staging Validation

Runs a stratified 10-account sample through the full ETL pipeline against the staging KeeperPAM tenant. Executes 10 assertions. **Hard blocks P3 if any assertion fails.**

```bash
az containerapp exec \
  --name "$APP_NAME" --resource-group "$RG" \
  --command "python3 cli.py agent 10-staging"
```

### Staging ETL pipeline (mini-version of P4/P5):
1. **Sample** — stratified 10 accounts across all wave tiers
2. **FREEZE** — disable CPM rotation on sample accounts (source)
3. **EXPORT** — retrieve passwords via PVWA Retrieve API
4. **TRANSFORM** — map CyberArk account format to KeeperPAM record format
5. **IMPORT** — create records in staging KeeperPAM tenant
6. **HEARTBEAT** — trigger rotation check on imported records
7. **VALIDATE** — run 10 assertions
8. **ROLLBACK** — always delete staging data regardless of pass/fail
9. **UNFREEZE** — re-enable CPM on source accounts

### 10 Assertions (all must pass):
| # | Assertion | Checks |
|---|-----------|--------|
| A-01 | Account count parity | Imported count = exported count |
| A-02 | Vault creation | All target vaults exist |
| A-03 | Permission assignment | Members assigned with correct permissions |
| A-04 | Heartbeat pass rate | ≥ 95% of records pass rotation check |
| A-05 | Password retrieval | Retrieve returns non-empty value |
| A-06 | Linked account integrity | Linked records maintain relationship |
| A-07 | Platform/record type assignment | All records have correct record type |
| A-08 | Audit event creation | Migration events logged in KeeperPAM |
| A-09 | Orphan detection | No orphaned records without vault |
| A-10 | Rollback clean | All staging records removed after test |

**View results:**
```bash
az containerapp exec \
  --name "$APP_NAME" --resource-group "$RG" \
  --command "cat output/reports/agent_10_staging_P2.json | python3 -c \"
import json, sys
data = json.load(sys.stdin)
assertions = data.get('assertions', {})
passed = sum(1 for v in assertions.values() if v.get('passed'))
print(f'Assertions passed: {passed}/10')
for name, result in assertions.items():
    status = 'PASS' if result.get('passed') else 'FAIL'
    print(f'  [{status}] {name}: {result.get(\\\"detail\\\", \\\"\\\")}')
\""
```

### If assertions fail:

| Assertion | Failure | Fix |
|-----------|---------|-----|
| A-01 Account count | Import errors | Check KeeperPAM record creation errors in audit log |
| A-02 Vault creation | Auth/permission issue | Verify KeeperPAM OAuth2 scopes include vault management |
| A-03 Permissions | Member API mismatch | Verify member payload format against KeeperPAM API docs |
| A-04 Heartbeat | Rotation engine not configured | KeeperPAM rotation policy setup required |
| A-05 Password retrieval | Record type field mismatch | Check password field name in KeeperPAM record type |
| A-07 Record type | Missing record type | Re-run Agent 13 to import missing platform |
| A-10 Rollback | Partial delete | Manual cleanup via KeeperPAM admin console |

**If any assertion fails, fix the root cause and re-run Agent 10.** Do not advance to P3 until 10/10 pass.

---

## P2 Output Files

| File | Contents |
|------|----------|
| `output/reports/agent_13_platform_plugins_P2.json` | Platform comparison + import results |
| `output/reports/agent_10_staging_P2.json` | 10-assertion staging results |
| `output/logs/audit.jsonl` | Appended staging ETL events |

---

## P2 Troubleshooting

| Issue | Cause | Fix |
|-------|-------|-----|
| Hard block: staging = production URL | Config error | Set separate `keeperpam_staging.base_url` |
| Agent 13 import fails | KeeperPAM record type import API not verified | Manually create record type via admin console |
| A-04 Heartbeat fails | KeeperPAM rotation not configured for record type | Work with KeeperPAM admin to set rotation policy |
| A-05 Password retrieval empty | Password field name differs in KeeperPAM | Check record type field definitions |
| Agent 10 crashes mid-run | Container restart | State auto-recovers; re-run agent (rollback is idempotent) |

---

## Yellow Checkpoint YC-P2

**Gate before advancing to P3. Requires:**
- [ ] All 10 staging assertions passing (10/10)
- [ ] All custom platforms rebuilt as KeeperPAM record types
- [ ] Staging data confirmed rolled back (no test records in KeeperPAM)
- [ ] Migration lead sign-off
- [ ] Client infrastructure team confirmation that staging run did not disrupt production

```bash
# After approval, advance to P3
az containerapp exec \
  --name "$APP_NAME" --resource-group "$RG" \
  --command "python3 cli.py advance"
```

---

## Next Step

→ **[P3_safe_migration.md](P3_safe_migration.md)** — Create all KeeperPAM vaults, apply permissions, set up app onboarding pipeline.

# Runbook P4 — Pilot Migration (Wave 1)
## CyberArk → KeeperPAM Migration | SHIFT System

**Scope:** Live ETL of Wave 1 (test/dev accounts). First production password migration. Heartbeat validation.
**Duration:** 1–2 weeks
**Prerequisite:** P3 complete, YC-P3 approved, all vaults created in KeeperPAM.
**Who runs this:** iOPEX delivery engineer (client on standby)

**Agent sequence:** `04-etl` → `05-heartbeat`

---

## P4 Checklist

- [ ] Wave 1 account list confirmed (test/dev accounts only)
- [ ] Client change management ticket open for maintenance window
- [ ] Rollback plan documented and agreed
- [ ] Both CyberArk admin and KeeperPAM admin on standby during ETL run
- [ ] Watchdog timer setting confirmed (default: 120 min auto-unfreeze)
- [ ] Agent 13 re-run confirmed — no platform drift since P2

---

## Agent 13 — Platform Re-Validation (P4 Pre-Check)

Re-run platform validation to confirm no drift since P2.

```bash
az containerapp exec \
  --name "$APP_NAME" --resource-group "$RG" \
  --command "python3 cli.py agent 13-platform-plugins --phase P4"
```

Expected: 0 new missing record types. If any appear, import before running ETL.

---

## Agent 04 — ETL Orchestration (Pilot)

The ETL pipeline. **This migrates real passwords.** 7-step execution:

```bash
# Dry run — verifies account selection and transformation, NO API writes to KeeperPAM
az containerapp exec \
  --name "$APP_NAME" --resource-group "$RG" \
  --command "python3 cli.py agent 04-etl --phase P4 --dry-run"

# Review dry-run output, then execute pilot
az containerapp exec \
  --name "$APP_NAME" --resource-group "$RG" \
  --command "python3 cli.py agent 04-etl --phase P4"
```

### ETL Pipeline — 7 Steps:

| Step | Action | Reversible? |
|------|--------|-------------|
| 1 FREEZE | Disable CPM rotation on Wave 1 accounts (source) | Yes — UNFREEZE |
| 2 EXPORT | Retrieve passwords via `POST /Accounts/{id}/Password/Retrieve` | N/A |
| 3 TRANSFORM | Map CyberArk account fields to KeeperPAM record fields | N/A |
| 4 VAULT VERIFY | Confirm target vaults exist (created in P3) | N/A |
| 5 IMPORT | Create records in KeeperPAM via `POST /records` | Yes — delete records |
| 6 HEARTBEAT | Trigger rotation check on imported records | N/A |
| 7 UNFREEZE | Re-enable CPM on source accounts | N/A |

### Field transformation (CyberArk → KeeperPAM):
| CyberArk Field | KeeperPAM Field |
|----------------|-----------------|
| userName | username |
| address | host / machine |
| platformId | recordType |
| safeName | vault |
| platformAccountProperties | custom notes |
| name | record title |

### Watchdog timer:
The ETL runs a background watchdog timer (default 120 min). If the pipeline does not complete within the window, the watchdog automatically unfreezes source accounts. This prevents accounts being locked out of rotation indefinitely.

```bash
# Check watchdog setting in agent_config.json
grep -A3 "watchdog" agent_config.json
```

To extend: set `"watchdog_minutes": 240` in `agent_config.json` for large batches.

### Monitor ETL progress:
```bash
# In a separate terminal — tail audit log
az containerapp exec \
  --name "$APP_NAME" --resource-group "$RG" \
  --command "tail -f output/logs/audit.jsonl"

# Check current step
az containerapp exec \
  --name "$APP_NAME" --resource-group "$RG" \
  --command "python3 cli.py status"
```

### Review ETL results:
```bash
az containerapp exec \
  --name "$APP_NAME" --resource-group "$RG" \
  --command "cat output/reports/agent_04_etl_P4.json | python3 -c \"
import json, sys
data = json.load(sys.stdin)
print('Accounts processed:', data.get('accounts_processed'))
print('Successfully imported:', data.get('imported_count'))
print('Failed imports:', data.get('failed_count'))
print('Skipped (no password):', data.get('skipped_count'))
print('Linked accounts:', data.get('linked_count'))
steps = data.get('steps', {})
for step, result in steps.items():
    status = 'OK' if result.get('success') else 'FAIL'
    print(f'  [{status}] {step}')
\""
```

### ETL rollback (if needed):
```bash
# If ETL fails mid-run, emergency unfreeze all frozen accounts
# The coordinator handles SIGTERM/SIGINT automatically
# Manual emergency unfreeze:
az containerapp exec \
  --name "$APP_NAME" --resource-group "$RG" \
  --command "python3 -c \"
from core.cyberark_client import CyberArkClient
import json
config = json.load(open('config.json'))
with CyberArkClient(config['cyberark_on_prem']) as client:
    # Unfreeze all accounts in Wave 1
    client.unfreeze_all_wave1_accounts()
\""
```

---

## Agent 05 — Heartbeat Validation

Runs 10 post-migration checks against all Wave 1 imported records.

```bash
az containerapp exec \
  --name "$APP_NAME" --resource-group "$RG" \
  --command "python3 cli.py agent 05-heartbeat --phase P4"
```

### 10 Validation Categories:
| # | Check | Pass Condition |
|---|-------|----------------|
| 1 | Record count parity | Imported = expected |
| 2 | Vault assignment | Every record in correct vault |
| 3 | Permission parity | Members assigned, count matches |
| 4 | Password rotation | ≥ 95% pass rotation check |
| 5 | Password retrieval | Retrieve returns non-empty |
| 6 | Linked record integrity | Linked accounts intact |
| 7 | Record type assignment | Correct record type on all records |
| 8 | Audit event presence | Migration events in KeeperPAM audit |
| 9 | Orphan records | 0 records without vault |
| 10 | Source account state | Source accounts still accessible |

**Overall pass threshold:** 95% or higher on rotation check; 100% on structural checks (1, 2, 3, 6, 7, 9).

**Review heartbeat results:**
```bash
az containerapp exec \
  --name "$APP_NAME" --resource-group "$RG" \
  --command "cat output/reports/agent_05_heartbeat_P4.json | python3 -c \"
import json, sys
data = json.load(sys.stdin)
overall = data.get('overall_pass_rate', 0)
print(f'Overall pass rate: {overall:.1%}')
cats = data.get('categories', {})
for name, result in cats.items():
    status = 'PASS' if result.get('passed') else 'FAIL'
    detail = result.get('detail', '')
    print(f'  [{status}] {name}: {detail}')
\""
```

### If heartbeat fails:

| Failure | Likely Cause | Action |
|---------|-------------|--------|
| Check 4 rotation < 95% | KeeperPAM rotation engine not connected to host | Network path issue — escalate to client infra team |
| Check 5 retrieval empty | Password field mismatch in record type | Fix record type field mapping, re-run ETL for failed records |
| Check 6 linked records | Linked account import failed | Identify failed linked accounts in ETL report, re-import |
| Check 9 orphan records | Vault creation failed for some safes | Re-run Agent 03 for failed vaults |

**Threshold-based outcome:**
- ≥ 95% pass: **PROCEED to P5**
- 90–95% pass: **REVIEW** — document failures, get client approval to proceed
- < 90% pass: **BLOCK** — do not proceed to P5, investigate and re-run

---

## P4 Output Files

| File | Contents |
|------|----------|
| `output/reports/agent_13_platform_plugins_P4.json` | Platform re-validation |
| `output/reports/agent_04_etl_P4.json` | ETL pipeline results |
| `output/reports/agent_05_heartbeat_P4.json` | 10-category heartbeat results |
| `output/logs/audit.jsonl` | All migration events (SHA-256 chain) |

---

## Yellow Checkpoint YC-P4

**Gate before advancing to P5. Requires:**
- [ ] Heartbeat pass rate ≥ 95%
- [ ] All structural checks (1, 2, 3, 6, 7, 9) = 100%
- [ ] Client confirmed Wave 1 apps still functioning (smoke test by app team)
- [ ] Migration lead sign-off
- [ ] Client sign-off on pilot results
- [ ] No escalated permissions applied without written approval

```bash
# After approval, advance to P5
az containerapp exec \
  --name "$APP_NAME" --resource-group "$RG" \
  --command "python3 cli.py advance"
```

---

## Next Step

→ **[P5_production.md](P5_production.md)** — Production batch migration, Waves 1–5. Integration repointing. Compliance evidence collection.

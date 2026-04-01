# Runbook P3 — Vault Creation, Permission Apply & App Onboarding Setup
## CyberArk → KeeperPAM Migration | SHIFT System

**Scope:** Create all KeeperPAM vaults mirroring CyberArk safes. Apply all 22 permissions per member. Set up application onboarding pipeline for new service accounts.
**Duration:** 2–3 weeks
**Prerequisite:** P2 complete, YC-P2 gate approved, all staging assertions 10/10.
**Who runs this:** iOPEX delivery engineer + client security team (permission review)

**Agent sequence:** `03-permissions` → `14-onboarding`

---

## P3 Checklist

- [ ] All KeeperPAM vaults created (count matches CyberArk safe count)
- [ ] All permissions applied — flagged permissions reviewed and approved
- [ ] Permission loss report reviewed and signed off
- [ ] App onboarding pipeline initialized
- [ ] Onboarding request queue populated with known new apps

---

## P3 vs P1 — Agent 03 Behavior

Agent 03 runs in two phases:
- **P1:** Analysis only — maps permissions, flags sensitive members, produces report. No writes.
- **P3:** Apply — creates vaults and applies permissions via KeeperPAM Members API. **This writes to production KeeperPAM.**

---

## Run P3 (Full Automated Sequence)

```bash
# Dry run first — validates vault creation + permission payloads without writing
az containerapp exec \
  --name "$APP_NAME" --resource-group "$RG" \
  --command "python3 cli.py run P3 --dry-run"

# Review dry-run output, then run live
az containerapp exec \
  --name "$APP_NAME" --resource-group "$RG" \
  --command "python3 cli.py run P3"
```

---

## Agent 03 — Permission Mapping (P3 Apply)

```bash
az containerapp exec \
  --name "$APP_NAME" --resource-group "$RG" \
  --command "python3 cli.py agent 03-permissions --phase P3"
```

### What it does in P3:
1. Reads permission inventory from P1 output
2. Creates KeeperPAM vaults for all CyberArk safes (if not already created)
3. Calls KeeperPAM Members API to add each member with their exact permissions
4. Handles 409 Conflict (member already exists) → falls back to update
5. Produces final permission apply report

### Vault creation:
- CyberArk Safe → KeeperPAM Vault (Shared Folder)
- Safe properties preserved: name, description, retention settings
- Managing CPM → KeeperPAM rotation engine equivalent

### Permission mapping (1:1 — no loss):
All 22 CyberArk permissions map directly to KeeperPAM's individual permission model.

**7 security-sensitive permissions — require human review before apply:**
| Permission | Risk | Review Required |
|------------|------|----------------|
| ManageSafe | Full vault admin | Security lead sign-off |
| ManageSafeMembers | Add/remove members | Security lead sign-off |
| AccessWithoutConfirmation | Bypass dual control | CISO sign-off |
| DeleteAccounts | Irreversible delete | Security lead sign-off |
| UnlockAccounts | Unlock locked accounts | Manager sign-off |
| BackupSafe | Full safe export | CISO sign-off |
| SpecifyNextAccountContent | Override next password | Manager sign-off |

**Review flagged members before running live:**
```bash
az containerapp exec \
  --name "$APP_NAME" --resource-group "$RG" \
  --command "cat output/reports/agent_03_permissions_P1.json | python3 -c \"
import json, sys
data = json.load(sys.stdin)
for m in data.get('flagged_members', []):
    print(f'Safe: {m[\\\"safe\\\"]}')
    print(f'  Member: {m[\\\"member\\\"]}')
    print(f'  Sensitive permissions: {m[\\\"flagged_permissions\\\"]}')
    print()
\""
```

Document each flagged member and get explicit sign-off from the client's security team before running the live apply.

**Review apply results:**
```bash
az containerapp exec \
  --name "$APP_NAME" --resource-group "$RG" \
  --command "cat output/reports/agent_03_permissions_P3.json | python3 -c \"
import json, sys
data = json.load(sys.stdin)
print('Vaults created:', data.get('vaults_created'))
print('Members applied:', data.get('members_applied'))
print('Members updated:', data.get('members_updated'))
print('Failed:', data.get('failed_count'))
errors = data.get('errors', [])
if errors:
    print('Errors:')
    for e in errors[:10]:
        print(f'  {e}')
\""
```

---

## Agent 14 — Application Onboarding Factory (P3 Setup)

Sets up the onboarding infrastructure in KeeperPAM for new service accounts discovered during P1.

```bash
az containerapp exec \
  --name "$APP_NAME" --resource-group "$RG" \
  --command "python3 cli.py agent 14-onboarding --phase P3"
```

### 10-step onboarding pipeline:
| Step | Action |
|------|--------|
| 1 | Create dedicated vault for application |
| 2 | Apply vault permissions (least privilege) |
| 3 | Create AppID / Application Identity in KeeperPAM |
| 4 | Create credential record |
| 5 | Assign record type (platform equivalent) |
| 6 | Configure rotation policy |
| 7 | Set CPM/rotation engine assignment |
| 8 | Initial password set |
| 9 | Heartbeat verification |
| 10 | Generate retrieval instructions for app team |

### Configure onboarding requests:

Add pending onboarding requests to `agent_config.json`:
```json
{
  "agent_14_onboarding": {
    "pending_requests": [
      {
        "app_name": "MyApp",
        "account_name": "svc-myapp-prod",
        "target_address": "db-prod.client.internal",
        "safe_name": "MyApp-Prod",
        "platform_id": "WinDomain",
        "username": "svc-myapp-prod"
      }
    ]
  }
}
```

**Review onboarding results:**
```bash
az containerapp exec \
  --name "$APP_NAME" --resource-group "$RG" \
  --command "cat output/reports/agent_14_onboarding_P3.json | python3 -c \"
import json, sys
data = json.load(sys.stdin)
for r in data.get('results', []):
    steps = len(r.get('steps_completed', []))
    status = 'SUCCESS' if r.get('success') else 'FAILED'
    print(f'[{status}] {r[\\\"app_name\\\"]}: {steps}/10 steps')
    if r.get('errors'):
        for e in r['errors']:
            print(f'  ERROR: {e}')
    if r.get('retrieval_instructions'):
        print(f'  Instructions: {r[\\\"retrieval_instructions\\\"][:100]}...')
\""
```

---

## P3 Output Files

| File | Contents |
|------|----------|
| `output/reports/agent_03_permissions_P3.json` | Vault creation + permission apply results |
| `output/reports/agent_14_onboarding_P3.json` | App onboarding results |
| `output/logs/audit.jsonl` | All vault/member creation events (SHA-256 chain) |

---

## P3 Troubleshooting

| Issue | Cause | Fix |
|-------|-------|-----|
| Vault creation 409 | Vault already exists | Expected — agent falls back to verify existing vault |
| Member add 403 | KeeperPAM OAuth2 missing vault management scope | Verify client app scope includes member management |
| 0 vaults created | `keeperpam.base_url` missing from config | Add to `config.json` |
| Onboarding step 9 fails | Rotation engine not configured for record type | Work with KeeperPAM admin |
| Permission apply fails for specific safe | Safe name has special characters | Check URL encoding in vault name |

---

## Yellow Checkpoint YC-P3

**Gate before advancing to P4. Requires:**
- [ ] All CyberArk safes represented as KeeperPAM vaults (count verified)
- [ ] All flagged sensitive permissions reviewed and approved in writing
- [ ] Permission apply error rate < 1%
- [ ] App onboarding pipeline tested end-to-end
- [ ] Client security team sign-off on permission report
- [ ] Compliance team sign-off (permissions preserved, no escalation without approval)

```bash
# After approval, advance to P4
az containerapp exec \
  --name "$APP_NAME" --resource-group "$RG" \
  --command "python3 cli.py advance"
```

---

## Next Step

→ **[P4_pilot.md](P4_pilot.md)** — Pilot ETL run with Wave 1 (test/dev accounts). First live password migration.

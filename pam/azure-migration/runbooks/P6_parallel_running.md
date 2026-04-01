# Runbook P6 — Parallel Running & Cutover
## CyberArk → KeeperPAM Migration | SHIFT System

**Scope:** Both CyberArk on-prem and KeeperPAM run simultaneously. Fleet management tracks per-account migration status. Final cutover when all accounts verified in KeeperPAM.
**Duration:** 4–6 weeks
**Prerequisite:** P5 complete, all waves migrated, all integrations repointed.
**Who runs this:** iOPEX delivery engineer + client operations team

**Agent sequence:** `15-hybrid-fleet` → `05-heartbeat` → `06-integration` → `07-compliance`

---

## P6 Checklist

- [ ] All 5 waves migrated (P5 complete)
- [ ] All application integrations repointed to KeeperPAM
- [ ] Hybrid fleet map initialized
- [ ] Weekly heartbeat schedule agreed with client
- [ ] Cutover criteria defined and documented
- [ ] Rollback plan documented (point-in-time: can revert to CyberArk)

---

## Parallel Running Concept

During P6, both systems operate simultaneously:
- **CyberArk on-prem:** Still active. CPM rotation may be running (configurable).
- **KeeperPAM:** Primary for all migrated accounts. Rotation engine active.
- **Agent 15:** Tracks every account's state, routes credential retrieval, detects split-brain scenarios.

The parallel period exists to:
1. Confirm all integrations are using KeeperPAM (not CyberArk)
2. Catch any accounts missed during P5 migration
3. Build operational confidence in KeeperPAM before CyberArk is decommissioned
4. Provide a safety net for rapid rollback

---

## Agent 15 — Hybrid Fleet Manager

Initialize the fleet map from P5 ETL results. Tracks every account's migration status.

```bash
# P5 run: Initialize fleet map
az containerapp exec \
  --name "$APP_NAME" --resource-group "$RG" \
  --command "python3 cli.py agent 15-hybrid-fleet --phase P5"
```

```bash
# P6 run: Verify target retrieval and detect stuck accounts (run weekly)
az containerapp exec \
  --name "$APP_NAME" --resource-group "$RG" \
  --command "python3 cli.py agent 15-hybrid-fleet --phase P6"
```

### Migration Status Lifecycle per Account:

| Status | Meaning | Action |
|--------|---------|--------|
| `on_prem` | Only in CyberArk | Migrate (should not exist after Wave 5) |
| `migrating` | ETL in progress | Monitor |
| `parallel` | In both systems | Verify KeeperPAM version, remove from CyberArk |
| `cloud_primary` | KeeperPAM primary, CyberArk fallback | Verify apps using KeeperPAM, prepare decommission |
| `migrated` | KeeperPAM only | Complete |
| `stuck` | No rotation for 48h+ | Investigate — escalate |

### View fleet status:
```bash
az containerapp exec \
  --name "$APP_NAME" --resource-group "$RG" \
  --command "cat output/reports/agent_15_hybrid_fleet_P6.json | python3 -c \"
import json, sys
data = json.load(sys.stdin)
by_status = data.get('by_status', {})
print('Fleet Status Summary:')
for status, count in by_status.items():
    print(f'  {status:20s}: {count}')
stuck = data.get('stuck_accounts', [])
if stuck:
    print(f'STUCK ACCOUNTS ({len(stuck)}):')
    for a in stuck[:10]:
        print(f'  {a[\\\"account_name\\\"]} (last rotation: {a[\\\"last_rotation_attempt\\\"]})')
\""
```

### Stuck account resolution:
A stuck account is one with no successful rotation in 48+ hours. Causes:

| Cause | Fix |
|-------|-----|
| Network path blocked | Open firewall from KeeperPAM rotation engine to target host |
| Credential mismatch | Manually reset password in KeeperPAM, trigger rotation |
| Record type mismatch | Re-map to correct record type |
| Host unreachable | Verify host is online; update record with new address |
| Rotation policy not set | Configure rotation policy in KeeperPAM admin |

---

## Agent 05 — Heartbeat Validation (P6 Weekly)

Run weekly throughout the parallel period to track ongoing health.

```bash
az containerapp exec \
  --name "$APP_NAME" --resource-group "$RG" \
  --command "python3 cli.py agent 05-heartbeat --phase P6"
```

Track heartbeat trend weekly:

| Week | Target Pass Rate | Gate Action |
|------|-----------------|-------------|
| Week 1 | ≥ 95% | Continue parallel running |
| Week 2 | ≥ 97% | Address any remaining stuck accounts |
| Week 3 | ≥ 99% | Begin cutover preparation |
| Week 4+ | 100% | Ready for cutover |

---

## Agent 06 — Integration Verification (P6)

Re-scan codebases to confirm ALL CyberArk integration patterns are gone.

```bash
az containerapp exec \
  --name "$APP_NAME" --resource-group "$RG" \
  --command "python3 cli.py agent 06-integration --phase P6"
```

**P6 pass condition:** 0 CyberArk integration patterns detected across all scanned directories.

If patterns remain:
- Identify which app team has not completed repointing
- Escalate with the specific file and line number from the scan report
- Do not cutover until 0 patterns remain

---

## Agent 07 — Compliance (P6 — Ongoing Evidence)

```bash
az containerapp exec \
  --name "$APP_NAME" --resource-group "$RG" \
  --command "python3 cli.py agent 07-compliance --phase P6"
```

P6 compliance focuses on:
- Dual-system access logging continuity
- Segregation of duties during parallel running
- Evidence that CyberArk access is restricted (not expanded) during parallel period
- SOX: evidence that privileged access controls are maintained throughout transition

---

## Cutover Decision

Cutover is the point at which CyberArk on-prem is frozen (read-only) and KeeperPAM becomes the sole authoritative PAM system.

**Cutover criteria (all must be met):**

| Criterion | Target | Source |
|-----------|--------|--------|
| Fleet `migrated` status | 100% of accounts | Agent 15 fleet report |
| Heartbeat pass rate | 100% | Agent 05 report |
| Integration repointing | 0 CyberArk patterns | Agent 06 scan |
| Stuck accounts | 0 | Agent 15 report |
| Compliance gaps | 0 HIGH/CRITICAL | Agent 07 report |
| App team confirmations | 100% of impacted teams | Signed-off tickets |

**When criteria are met, schedule the cutover window:**

```bash
# Final heartbeat before cutover
az containerapp exec \
  --name "$APP_NAME" --resource-group "$RG" \
  --command "python3 cli.py agent 05-heartbeat --phase P6"

# Final fleet check
az containerapp exec \
  --name "$APP_NAME" --resource-group "$RG" \
  --command "python3 cli.py agent 15-hybrid-fleet --phase P6"

# Final integration scan
az containerapp exec \
  --name "$APP_NAME" --resource-group "$RG" \
  --command "python3 cli.py agent 06-integration --phase P6"
```

**All pass → proceed with cutover.**

### Cutover execution:
1. Notify all stakeholders — maintenance window start
2. Freeze CyberArk: disable CPM on ALL remaining accounts
3. Set CyberArk to read-only mode (or revoke write permissions from migration service account)
4. Update DNS / load balancer aliases from PVWA to KeeperPAM where applicable
5. Confirm all app teams verify their credentials are being retrieved from KeeperPAM
6. Run final Agent 05 heartbeat — must be 100%
7. Declare cutover complete

```bash
# Post-cutover final heartbeat
az containerapp exec \
  --name "$APP_NAME" --resource-group "$RG" \
  --command "python3 cli.py agent 05-heartbeat --phase P6"
```

---

## P6 Output Files

| File | Contents |
|------|----------|
| `output/reports/agent_15_hybrid_fleet_P5.json` | Initial fleet map |
| `output/reports/agent_15_hybrid_fleet_P6.json` | Weekly fleet status |
| `output/reports/agent_05_heartbeat_P6.json` | Weekly heartbeat |
| `output/reports/agent_06_integration_P6.json` | Integration re-scan results |
| `output/reports/agent_07_compliance_P6.json` | Parallel running compliance evidence |

---

## P6 Troubleshooting

| Issue | Cause | Fix |
|-------|-------|-----|
| Split-brain: both CPM rotate same account | Hybrid mode not set to exclusive | Set `HYBRID_MODE=exclusive` in `agent_config.json` |
| Stuck accounts increasing week-over-week | Systemic rotation failure | Network / firewall audit required |
| App team reports wrong password | Old credentials cached | Force rotation in KeeperPAM; app team flushes cache |
| Integration scan still finding patterns | App deployed with old code | App team re-deployment required |
| CyberArk PVWA showing access attempts post-cutover | App still using CyberArk | Agent 06 re-scan to identify source |

---

## Yellow Checkpoint YC-P6

**Gate before advancing to P7 (decommission). Requires:**
- [ ] 100% of accounts at `migrated` status in fleet report
- [ ] 100% heartbeat pass rate
- [ ] 0 CyberArk integration patterns in final scan
- [ ] 0 stuck accounts
- [ ] Cutover completed and confirmed by all app teams
- [ ] CISO / security lead sign-off
- [ ] Client executive sign-off
- [ ] Change management ticket closed

```bash
# Advance to P7
az containerapp exec \
  --name "$APP_NAME" --resource-group "$RG" \
  --command "python3 cli.py advance"
```

---

## Next Step

→ **[P7_decommission.md](P7_decommission.md)** — CyberArk on-prem decommission, final audit report, project close-out.

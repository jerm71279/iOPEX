# Runbook P5 — Production Migration (Waves 1–5)
## CyberArk → KeeperPAM Migration | SHIFT System

**Scope:** Full production ETL across all 5 waves. Integration repointing. New app onboarding. Compliance evidence collection.
**Duration:** 4–6 weeks
**Prerequisite:** P4 complete, YC-P4 approved, pilot heartbeat ≥ 95%.
**Who runs this:** iOPEX delivery engineer (client teams on standby per wave)

**Agent sequence (per wave):** `04-etl` → `05-heartbeat` → `06-integration` → `14-onboarding` → `07-compliance`

---

## Wave Schedule

Plan wave execution windows with the client. Each wave should run in a scheduled maintenance window.

| Wave | Tier | Typical Accounts | Suggested Window |
|------|------|-----------------|-----------------|
| 1 | Test/Dev | Lowest risk | Off-hours, any day |
| 2 | Standard Users | Medium risk | Weekend window |
| 3 | Infrastructure | High risk | Weekend, with rollback plan |
| 4 | NHIs | High risk | Dedicated weekend window |
| 5 | Critical/Privileged | Highest risk | Board-approved window, all hands on deck |

---

## Per-Wave Execution

Repeat this sequence for each wave. Wave 1 was completed in P4; start P5 from Wave 2 (or re-run Wave 1 if P4 was a subset).

### Run the wave:

```bash
WAVE=2  # Change per wave

az containerapp exec \
  --name "$APP_NAME" --resource-group "$RG" \
  --command "python3 cli.py run P5 --dry-run"

# After dry-run review:
az containerapp exec \
  --name "$APP_NAME" --resource-group "$RG" \
  --command "python3 cli.py run P5"
```

The coordinator runs all P5 agents in sequence for the configured wave set.

---

## Agent 04 — ETL Orchestration (Production Waves)

Same 7-step pipeline as P4 pilot, at full production scale.

```bash
az containerapp exec \
  --name "$APP_NAME" --resource-group "$RG" \
  --command "python3 cli.py agent 04-etl --phase P5"
```

**Batch sizing recommendations by wave:**

| Wave | Recommended Batch | Rationale |
|------|------------------|-----------|
| 1–2 | 500 accounts | Stable, low-risk |
| 3 | 200 accounts | More complex, infrastructure-critical |
| 4 (NHI) | 100 accounts | Complex dependencies, more validation needed |
| 5 (Critical) | 50 accounts | Maximum caution, individual verification |

Adjust in `agent_config.json`:
```json
{
  "agent_04_etl": {
    "batch_size": 200,
    "watchdog_minutes": 180
  }
}
```

**Monitor per-batch progress:**
```bash
az containerapp exec \
  --name "$APP_NAME" --resource-group "$RG" \
  --command "tail -f output/logs/audit.jsonl | grep -E '(IMPORT|FREEZE|UNFREEZE|batch)'"
```

**Cumulative ETL results:**
```bash
az containerapp exec \
  --name "$APP_NAME" --resource-group "$RG" \
  --command "cat output/reports/agent_04_etl_P5.json | python3 -c \"
import json, sys
data = json.load(sys.stdin)
print('Wave:', data.get('wave'))
print('Accounts processed:', data.get('accounts_processed'))
print('Imported:', data.get('imported_count'))
print('Failed:', data.get('failed_count'))
print('Skipped:', data.get('skipped_count'))
\""
```

---

## Agent 05 — Heartbeat Validation (Post-Wave)

Run after every wave's ETL completes.

```bash
az containerapp exec \
  --name "$APP_NAME" --resource-group "$RG" \
  --command "python3 cli.py agent 05-heartbeat --phase P5"
```

**YC-P5 gate applies after every wave.** Do not start the next wave until the current wave's heartbeat meets threshold.

| Wave | Minimum Pass Rate | Notes |
|------|------------------|-------|
| 1–2 | 95% | Standard threshold |
| 3 | 97% | Infrastructure accounts are higher stakes |
| 4 | 97% | NHI rotation failures can cascade |
| 5 | 99% | Critical accounts — near-zero tolerance |

---

## Agent 06 — Integration Repointing (CCP/AAM)

Scans application codebases for CyberArk CCP/AAM patterns and generates KeeperPAM replacement code.

```bash
az containerapp exec \
  --name "$APP_NAME" --resource-group "$RG" \
  --command "python3 cli.py agent 06-integration --phase P5"
```

**Configure scan directories** in `agent_config.json`:
```json
{
  "agent_06_integration": {
    "scan_directories": [
      "/mnt/app-source/backend",
      "/mnt/app-source/scripts",
      "/mnt/config-repo"
    ],
    "output_replacements": true,
    "languages": ["python", "powershell", "csharp", "java"]
  }
}
```

**Review scan results:**
```bash
az containerapp exec \
  --name "$APP_NAME" --resource-group "$RG" \
  --command "cat output/reports/agent_06_integration_P5.json | python3 -c \"
import json, sys
data = json.load(sys.stdin)
print('Files scanned:', data.get('files_scanned'))
print('Integrations found:', data.get('integration_count'))
print('Replacements generated:', data.get('replacements_generated'))
findings = data.get('findings', [])
for f in findings[:10]:
    print(f'  {f[\\\"file\\\"]}: {f[\\\"pattern\\\"]} (line {f[\\\"line\\\"]})')
\""
```

**Distribute replacement code artifacts** to application teams. Each team must:
1. Review the generated replacement code
2. Test against KeeperPAM staging
3. Deploy to production apps
4. Confirm via Agent 06 re-scan (0 CyberArk patterns remaining)

**Integration repointing is NOT complete until all app teams confirm.**

---

## Agent 14 — Application Onboarding (P5 Production)

Processes new application onboarding requests that were queued during P3 or discovered during Wave ETL.

```bash
az containerapp exec \
  --name "$APP_NAME" --resource-group "$RG" \
  --command "python3 cli.py agent 14-onboarding --phase P5"
```

Add new onboarding requests as they come in during P5:
```json
{
  "agent_14_onboarding": {
    "pending_requests": [
      {
        "app_name": "NewApp-Prod",
        "account_name": "svc-newapp-db",
        "target_address": "db-prod.client.internal",
        "safe_name": "NewApp-Prod",
        "platform_id": "MSSql",
        "username": "svc-newapp-db"
      }
    ]
  }
}
```

---

## Agent 07 — Compliance & Audit

Collects compliance evidence after each wave. Maps every migration action to PCI-DSS, NIST 800-53, HIPAA, and SOX controls.

```bash
az containerapp exec \
  --name "$APP_NAME" --resource-group "$RG" \
  --command "python3 cli.py agent 07-compliance --phase P5"
```

**Compliance frameworks covered:**
| Framework | Key Controls Evidenced |
|-----------|----------------------|
| PCI-DSS | Req 7 (least privilege), Req 10 (audit logging), Req 8 (ID management) |
| NIST 800-53 | AC-2, AC-3, AC-6, AU-2, AU-9, IA-5 |
| HIPAA | Access controls, audit controls, integrity |
| SOX | Segregation of duties, privileged access management, audit trail |

**Review compliance evidence:**
```bash
az containerapp exec \
  --name "$APP_NAME" --resource-group "$RG" \
  --command "cat output/reports/agent_07_compliance_P5.json | python3 -c \"
import json, sys
data = json.load(sys.stdin)
for framework, controls in data.get('controls_evidenced', {}).items():
    print(f'{framework}: {len(controls)} controls evidenced')
gaps = data.get('compliance_gaps', [])
if gaps:
    print(f'GAPS ({len(gaps)}):')
    for g in gaps:
        print(f'  [{g[\\\"risk\\\"]}] {g[\\\"control\\\"]}: {g[\\\"finding\\\"]}')
\""
```

---

## P5 Output Files

| File | Contents |
|------|----------|
| `output/reports/agent_04_etl_P5.json` | Full ETL results per wave |
| `output/reports/agent_05_heartbeat_P5.json` | Heartbeat results per wave |
| `output/reports/agent_06_integration_P5.json` | Integration scan + replacement artifacts |
| `output/reports/agent_07_compliance_P5.json` | Compliance evidence per framework |
| `output/reports/agent_14_onboarding_P5.json` | New app onboarding results |
| `output/logs/audit.jsonl` | Complete audit trail (SHA-256 chain) |
| `output/reports/integration_replacements/` | Per-language replacement code files |

---

## P5 Troubleshooting

| Issue | Cause | Fix |
|-------|-------|-----|
| ETL rate-limited by KeeperPAM | Too many requests per second | Increase `rate_limit` in config (0.5s between calls) |
| Agent 06 scan misses files | Binary/compiled assets | Document as manual review item |
| Heartbeat < threshold after Wave 4 | NHI rotation endpoint not accessible | Check network path from KeeperPAM to target systems |
| Agent 07 missing controls | Audit log gap during wave | Review audit.jsonl for gaps; supplement with PVWA export |
| State corruption mid-wave | Container restart | Re-run failed agent; state auto-recovers from last checkpoint |

---

## Wave Completion Gate (YC-P5 — per wave)

Before starting each subsequent wave:
- [ ] ETL failure rate < 1%
- [ ] Heartbeat pass rate meets wave threshold
- [ ] Application team confirmed integration repointing complete (for apps in this wave)
- [ ] Compliance agent run and evidence collected
- [ ] Migration lead sign-off
- [ ] No open P4/P5 incidents

After all 5 waves complete:
- [ ] Total account count in KeeperPAM = total source account count (±1% tolerance)
- [ ] All integration repointing confirmed by all app teams
- [ ] Full compliance evidence set collected

```bash
# After all waves complete, advance to P6
az containerapp exec \
  --name "$APP_NAME" --resource-group "$RG" \
  --command "python3 cli.py advance"
```

---

## Next Step

→ **[P6_parallel_running.md](P6_parallel_running.md)** — Parallel running (both systems live), fleet management, final cutover.

# Runbook P7 — Decommission & Close-Out
## CyberArk → KeeperPAM Migration | SHIFT System

**Scope:** CyberArk on-prem decommission. Final audit report. Compliance evidence package. Project close-out documentation.
**Duration:** 2–3 weeks
**Prerequisite:** P6 complete, YC-P6 approved, cutover confirmed.
**Who runs this:** iOPEX delivery engineer + client operations + compliance team

**Agent sequence:** `07-compliance`

---

## P7 Checklist

- [ ] CyberArk CPM service stopped on all servers
- [ ] CyberArk PVWA access revoked for all migration service accounts
- [ ] Backup of CyberArk vault exported and archived (per client retention policy)
- [ ] Final compliance report generated
- [ ] Audit log archive transferred to client
- [ ] Knowledge transfer to client operations team complete
- [ ] Project close-out document signed

---

## Step 1 — Final Compliance Report

Agent 07 generates the complete compliance evidence package covering the full migration lifecycle (P0–P7).

```bash
az containerapp exec \
  --name "$APP_NAME" --resource-group "$RG" \
  --command "python3 cli.py agent 07-compliance --phase P7"
```

### What the P7 compliance run produces:

| Evidence Item | Framework | Control |
|--------------|-----------|---------|
| Full audit log with SHA-256 chain | All | Audit integrity |
| Permission preservation evidence | PCI-DSS | Req 7.1 |
| Zero-data-loss confirmation | NIST | AU-9 |
| Segregation of duties log | SOX | SOD evidence |
| NHI migration evidence | NIST | IA-5 |
| Parallel running access controls | SOX | Privileged access |
| Cutover timestamp and confirmation | All | Change management |
| Human approval gate log | SOX | Management approval |

**Review final compliance report:**
```bash
az containerapp exec \
  --name "$APP_NAME" --resource-group "$RG" \
  --command "cat output/reports/agent_07_compliance_P7.json | python3 -c \"
import json, sys
data = json.load(sys.stdin)
print('Migration ID:', data.get('migration_id'))
print('Total phases covered:', data.get('phases_covered'))
print('Total accounts migrated:', data.get('total_accounts_migrated'))
print('Zero data loss confirmed:', data.get('zero_data_loss'))
print('Compliance frameworks evidenced:')
for fw in data.get('frameworks_evidenced', []):
    controls = data['controls_evidenced'].get(fw, [])
    print(f'  {fw}: {len(controls)} controls')
gaps = data.get('open_gaps', [])
if gaps:
    print(f'OPEN GAPS ({len(gaps)}):')
    for g in gaps:
        print(f'  [{g[\\\"risk\\\"]}] {g[\\\"control\\\"]}: {g[\\\"finding\\\"]}')
else:
    print('Open gaps: 0 (clean)')
\""
```

**All open compliance gaps must be resolved before final sign-off.**

---

## Step 2 — Archive Audit Logs

The SHA-256 hash-chained audit log is the tamper-evident record of the entire migration. Archive it permanently.

```bash
# Copy audit log to Azure Storage (long-term archive)
STORAGE_ACCOUNT="<envName>store"
CONTAINER="migration-audit-logs"
MIGRATION_ID=$(python3 cli.py status | grep "Migration ID" | awk '{print $3}')

az storage blob upload \
  --account-name "$STORAGE_ACCOUNT" \
  --container-name "$CONTAINER" \
  --name "${MIGRATION_ID}/audit.jsonl" \
  --file output/logs/audit.jsonl \
  --auth-mode login

# Verify upload
az storage blob show \
  --account-name "$STORAGE_ACCOUNT" \
  --container-name "$CONTAINER" \
  --name "${MIGRATION_ID}/audit.jsonl" \
  --auth-mode login \
  --query "{size:properties.contentLength, md5:properties.contentSettings.contentMd5}" \
  --output table
```

**Retention:** Keep audit logs for minimum 7 years (PCI-DSS requirement). Configure blob lifecycle policy:
```bash
az storage account management-policy create \
  --account-name "$STORAGE_ACCOUNT" \
  --policy '{
    "rules": [{
      "name": "archive-after-90d",
      "type": "Lifecycle",
      "definition": {
        "actions": {"baseBlob": {"tierToArchive": {"daysAfterModificationGreaterThan": 90}}},
        "filters": {"blobTypes": ["blockBlob"], "prefixMatch": ["migration-audit-logs/"]}
      }
    }]
  }'
```

---

## Step 3 — Archive All Migration Reports

```bash
# Upload all reports to Azure Storage
az storage blob upload-batch \
  --account-name "$STORAGE_ACCOUNT" \
  --destination "$CONTAINER/${MIGRATION_ID}/reports" \
  --source output/reports/ \
  --auth-mode login

echo "Reports archived: $(az storage blob list \
  --account-name "$STORAGE_ACCOUNT" \
  --container-name "$CONTAINER" \
  --prefix "${MIGRATION_ID}/reports/" \
  --auth-mode login --query 'length(@)' --output tsv) files"
```

---

## Step 4 — CyberArk On-Prem Decommission

Work with the client's CyberArk admin and infrastructure team.

### Decommission checklist (client-executed):

| Step | Action | Team | Verified |
|------|--------|------|---------|
| 1 | Stop CyberArk CPM services on all CPM servers | Infra | |
| 2 | Stop CyberArk PVWA application pool on all PVWA servers | Infra | |
| 3 | Revoke migration service account (`svc-iopex-migration`) | CyberArk admin | |
| 4 | Revoke all user access to PVWA | CyberArk admin | |
| 5 | Export full CyberArk vault backup (DR copy) | CyberArk admin | |
| 6 | Archive PSM session recordings (if applicable) | CyberArk admin | |
| 7 | Power off CyberArk server VMs (do not delete immediately) | Infra | |
| 8 | Update DNS: remove PVWA CNAME/A records (or redirect) | Networking | |
| 9 | Close firewall rules to PVWA (inbound 443 from client network) | Security | |
| 10 | Schedule VM deletion after 90-day hold period | Infra | |

> **Do not delete CyberArk VMs immediately.** Hold for 90 days post-cutover as a safety net. After 90 days with no retrieval requests against CyberArk, decommission fully.

---

## Step 5 — Migration Service Account Cleanup

Remove all iOPEX migration service accounts and credentials from the client environment:

```bash
# Remove KeeperPAM OAuth2 client used for migration
# (Client KeeperPAM admin action — do in KeeperPAM admin console)
# The migration client ID should be DIFFERENT from operational client IDs

# Rotate or revoke Azure AD service accounts used by the Container App
az containerapp update \
  --name "$APP_NAME" --resource-group "$RG" \
  --remove-env-vars "CYBERARK_USERNAME" "CYBERARK_PASSWORD"

# Archive Key Vault migration secrets (soft delete, don't purge yet)
az keyvault secret set-attributes \
  --vault-name "<kv-name>" \
  --name "CYBERARK-USERNAME" \
  --enabled false

az keyvault secret set-attributes \
  --vault-name "<kv-name>" \
  --name "CYBERARK-PASSWORD" \
  --enabled false
```

---

## Step 6 — Knowledge Transfer

Before project close-out, deliver to client operations team:

| Deliverable | Format | Contents |
|------------|--------|----------|
| KeeperPAM Operations Runbook | DOCX | Day-to-day PAM operations in KeeperPAM |
| Incident Response Playbook | DOCX | PAM-related incident scenarios and response |
| Onboarding Guide | DOCX | How to onboard new applications using Agent 14 |
| Architecture Diagram | PPTX | Final as-built KeeperPAM architecture |
| Audit Log Verification Guide | DOCX | How to verify SHA-256 chain integrity |
| Contact Matrix | DOCX | KeeperPAM support, iOPEX contacts, client PAM team |

Run the onboarding demo with client operations team:
```bash
az containerapp exec \
  --name "$APP_NAME" --resource-group "$RG" \
  --command "python3 cli.py agent 14-onboarding --phase P5"
```

Walk through the 10-step pipeline with a test application.

---

## Step 7 — Final Migration Status Report

```bash
az containerapp exec \
  --name "$APP_NAME" --resource-group "$RG" \
  --command "python3 cli.py status"
```

**Expected final status:**
```
Migration ID : shift-YYYYMMDD-001
Phase        : P7
Status       : complete
Started      : YYYY-MM-DDTHH:MM:SSZ
Completed    : YYYY-MM-DDTHH:MM:SSZ
Total phases : P0-P7 (all complete)
Accounts     : NNNN migrated / 0 failed / 0 pending
```

---

## P7 Output Files

| File | Contents |
|------|----------|
| `output/reports/agent_07_compliance_P7.json` | Final compliance evidence package |
| `output/logs/audit.jsonl` | Complete migration audit trail |
| Azure Storage archive | All reports + audit log (7-year retention) |

---

## Yellow Checkpoint YC-P7 — Final Project Close-Out

**All must be complete before project is closed:**

| Item | Owner | Status |
|------|-------|--------|
| Compliance report — 0 open gaps | iOPEX + Client Compliance | |
| Audit log archived to Azure Storage | iOPEX | |
| CyberArk CPM and PVWA services stopped | Client Infra | |
| Migration service accounts revoked | Client Security | |
| 90-day CyberArk hold period confirmed | Client Infra | |
| Knowledge transfer sessions complete | iOPEX | |
| Final migration summary signed | Client Executive | |
| SHIFT project closure ticket closed | iOPEX PMO | |

---

## Post-Migration Monitoring Recommendations

Advise the client to monitor for 30 days post-cutover:

| Metric | Tool | Threshold |
|--------|------|-----------|
| KeeperPAM rotation failures | KeeperPAM dashboard | 0 unresolved |
| Failed password retrievals | KeeperPAM audit | < 0.1% |
| Any PVWA access attempts | CyberArk PVWA logs (still running in hold period) | Alert on any access |
| New app onboarding requests | Agent 14 queue | Respond within SLA |

---

## Migration Complete

The CyberArk on-prem → KeeperPAM migration is complete. All privileged credentials are under KeeperPAM governance. The SHA-256 audit chain provides tamper-evident proof of the full migration lifecycle for compliance purposes.

**Total scope completed:**
- P0 through P7 — all 8 phases
- 15 agents executed
- 7 Yellow Checkpoint gates approved
- Full compliance evidence package delivered

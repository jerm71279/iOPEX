# Secret Rotation Procedure
## CyberArk → KeeperPAM Migration | SHIFT System

**Document ID:** SEC-ROT-001
**Last Updated:** 2026-03-30
**Owner:** Migration Security Lead
**Applies To:** All SHIFT system credentials stored in Azure Key Vault

---

## When to Rotate

Rotate all credentials under any of the following conditions:

| Trigger | Scope | Priority |
|---------|-------|----------|
| Suspected or confirmed compromise | All credentials | IMMEDIATE — within 1 hour |
| Scheduled rotation (every 90 days) | All credentials | PLANNED |
| End of migration (post-P7) | All credentials | PLANNED — before decommission |
| Personnel change (team member offboarding) | All credentials | Within 24 hours |
| Failed login anomaly detected in Key Vault audit logs | Affected credential | Within 4 hours |
| Container App redeployment to new subscription | All credentials | Before first run |

---

## Credential Inventory

| Secret Name (Key Vault) | Environment Variable | Credential Type | Rotation Owner |
|-------------------------|----------------------|-----------------|----------------|
| `CyberArkPassword` | `CYBERARK_PASSWORD` | CyberArk service account password | Client CyberArk admin |
| `KeeperPamClientSecret` | `KEEPERPAM_CLIENT_SECRET` | KeeperPAM OAuth2 client secret | Client KeeperPAM admin |
| `AppInsightsConnectionString` | `APPLICATIONINSIGHTS_CONNECTION_STRING` | App Insights instrumentation key | Azure subscription owner |

---

## 1. Rotating the CyberArk Service Account Password (CYBERARK_PASSWORD)

### Prerequisites
- Access to CyberArk PVWA with User Management permissions
- Azure CLI authenticated (`az login`) with Key Vault write access
- Scheduled during a maintenance window (no active ETL run)

### Steps

**Step 1 — Pause any active migration run**

```bash
# Check if a migration run is active
az containerapp exec \
  --name shift-migration-app \
  --resource-group <rg-name> \
  --command "cat /app/output/state/migration_state.json | python3 -c 'import sys,json; s=json.load(sys.stdin); print(s[\"status\"])'"
```

If status is `running`, wait for the current phase to complete or trigger a graceful pause before continuing.

**Step 2 — Generate new password in CyberArk**

1. Log in to CyberArk PVWA as an admin.
2. Navigate to **Administration > Users**.
3. Select the migration service account (e.g., `svc-shift-migration`).
4. Click **Change Password** — use a 24+ character random password meeting CyberArk complexity requirements.
5. Record the new password securely (e.g., in a local password manager — NOT in a file).
6. Click **Save**.

**Step 3 — Update Key Vault secret**

```bash
# Update the secret value
az keyvault secret set \
  --vault-name <keyvault-name> \
  --name CyberArkPassword \
  --value "<new-password>"

# Verify the new version was created
az keyvault secret list-versions \
  --vault-name <keyvault-name> \
  --name CyberArkPassword \
  --output table
```

**Step 4 — Restart Container App to pick up new secret**

```bash
# Trigger a new revision (forces secret reload)
az containerapp update \
  --name shift-migration-app \
  --resource-group <rg-name> \
  --revision-suffix "rotated-$(date +%Y%m%d)"
```

**Step 5 — Verify preflight passes with new credential**

```bash
az containerapp exec \
  --name shift-migration-app \
  --resource-group <rg-name> \
  --command "python3 cli.py preflight"
```

Expected output: `Preflight checks passed` with CyberArk connectivity confirmed.

**Step 6 — Update this register**

Record the rotation in the credentials log (section at end of this document).

---

## 2. Rotating the KeeperPAM OAuth2 Client Secret (KEEPERPAM_CLIENT_SECRET)

### Prerequisites
- Access to KeeperPAM Admin Console with Application/OAuth2 management permissions
- Azure CLI authenticated with Key Vault write access

### Steps

**Step 1 — Pause any active migration run** (same as Step 1 above)

**Step 2 — Regenerate client secret in KeeperPAM Admin Console**

1. Log in to the KeeperPAM Admin Console.
2. Navigate to **Applications** (or **OAuth2 Clients**, depending on version).
3. Find the application registered for SHIFT (`shift-migration-app` or similar).
4. Click **Rotate Secret** or **Generate New Secret**.
5. Copy the new client secret — it will only be shown once.

> Note: The old secret is immediately invalidated when the new one is generated. Ensure the Container App is not actively running an ETL phase before rotating.

**Step 3 — Update Key Vault secret**

```bash
az keyvault secret set \
  --vault-name <keyvault-name> \
  --name KeeperPamClientSecret \
  --value "<new-client-secret>"
```

**Step 4 — Restart Container App**

```bash
az containerapp update \
  --name shift-migration-app \
  --resource-group <rg-name> \
  --revision-suffix "rotated-$(date +%Y%m%d)"
```

**Step 5 — Verify KeeperPAM authentication**

```bash
az containerapp exec \
  --name shift-migration-app \
  --resource-group <rg-name> \
  --command "python3 -c \"
from core.keeper_client import KeeperClient
import json
with open('config.json') as f:
    cfg = json.load(f)
client = KeeperClient(cfg)
client.authenticate()
print('KeeperPAM auth OK')
\""
```

Expected: `KeeperPAM auth OK`

---

## 3. Azure Key Vault Emergency Rotation (KV Itself Compromised)

Use this procedure if the Key Vault access policy or RBAC has been compromised, or if unauthorized access to secrets is detected.

### Indicators of Compromise
- Unexpected entries in Key Vault audit log (`AuditEvent` in Log Analytics)
- Alert from Microsoft Defender for Key Vault
- `SecretGet` operations from unexpected principals or IP addresses

### Steps

**Step 1 — Revoke all non-essential access immediately**

```bash
# List current role assignments on Key Vault
az role assignment list \
  --scope /subscriptions/<sub-id>/resourceGroups/<rg>/providers/Microsoft.KeyVault/vaults/<kv-name> \
  --output table

# Remove any unexpected principal
az role assignment delete \
  --assignee <suspicious-principal-id> \
  --scope /subscriptions/<sub-id>/resourceGroups/<rg>/providers/Microsoft.KeyVault/vaults/<kv-name>
```

**Step 2 — Audit access logs in Log Analytics**

```kusto
AzureDiagnostics
| where ResourceType == "VAULTS"
| where OperationName == "SecretGet" or OperationName == "SecretList"
| where TimeGenerated > ago(7d)
| project TimeGenerated, CallerIPAddress, identity_claim_oid_g, requestUri_s, ResultType
| order by TimeGenerated desc
```

**Step 3 — Rotate ALL secrets stored in Key Vault**

Rotate CyberArkPassword and KeeperPamClientSecret using procedures 1 and 2 above. Also rotate:

```bash
# App Insights connection string — regenerate in Azure Portal
# Application Insights > Properties > Regenerate key
# Then update Key Vault:
az keyvault secret set \
  --vault-name <keyvault-name> \
  --name AppInsightsConnectionString \
  --value "<new-connection-string>"
```

**Step 4 — Notify client security team**

Raise a security incident with:
- Timestamp of suspected compromise
- Affected secrets (names only, not values)
- Log Analytics query results (redact any credential values)
- Actions taken

**Step 5 — Consider Key Vault recreation if persistent access suspected**

If the Key Vault RBAC itself may be compromised at the Azure AD level, create a new Key Vault in a clean resource group, migrate secrets, and update the Container App to reference the new vault.

---

## Mid-Migration Rotation Procedure

Rotating credentials while an ETL run is active requires coordination to avoid interrupting a live migration phase.

### Safe Windows for Rotation

| Migration State | Safe to Rotate? | Notes |
|-----------------|-----------------|-------|
| Phase gate (waiting for approval) | YES | Container App is idle between phases |
| ETL FREEZE or EXPORT step | NO | Active PVWA API calls in progress |
| ETL TRANSFORM step | YES | No active API calls during transform |
| ETL IMPORT step | NO | Active KeeperPAM API calls in progress |
| ETL HEARTBEAT step | YES | Brief window between import and unfreeze |
| Post-phase validation | YES | Agents are read-only during validation |

### Procedure for Mid-Migration Rotation

1. Monitor the ETL progress via Container App logs:
   ```bash
   az containerapp logs show \
     --name shift-migration-app \
     --resource-group <rg-name> \
     --follow
   ```
2. Wait for a safe window (see table above).
3. The Container App watchdog timer is set to 120 minutes. Do not hold at a rotation step for longer than the remaining watchdog time — the watchdog will auto-unfreeze the source vault.
4. Complete the rotation steps above.
5. Restart the Container App revision.
6. If the migration was at a phase gate, resume from the gate with `python3 cli.py run <phase>`.
7. If rotation occurred mid-phase, verify the last completed ETL step in `output/state/migration_state.json` and resume from the correct step.

---

## Verification Checklist After Any Rotation

Complete all items after every rotation event:

- [ ] New secret version visible in Key Vault: `az keyvault secret list-versions --vault-name <kv> --name <secret-name>`
- [ ] Old secret version disabled (optional — do after confirming new version works):
  ```bash
  az keyvault secret set-attributes \
    --vault-name <kv-name> \
    --name <secret-name> \
    --version <old-version-id> \
    --enabled false
  ```
- [ ] Container App restarted with new revision
- [ ] `python3 cli.py preflight` passes all checks
- [ ] No error events in Log Analytics for 15 minutes post-restart:
  ```kusto
  ContainerAppConsoleLogs_CL
  | where TimeGenerated > ago(15m)
  | where Log_s contains "ERROR" or Log_s contains "auth" or Log_s contains "401"
  ```
- [ ] Rotation event recorded in credentials log below

---

## Credentials Rotation Log

| Date | Secret Name | Rotated By | Trigger | Verification Passed | Notes |
|------|-------------|------------|---------|---------------------|-------|
| — | — | — | — | — | Initial deployment |

*Add a row for each rotation event.*

---

*End of Secret Rotation Procedure*

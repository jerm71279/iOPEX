# Security Controls Register — SHIFT Azure Migration System

**Project:** CyberArk → KeeperPAM Azure Migration
**System:** SHIFT (iOPEX PAM Migration Platform)
**Last Updated:** 2026-03-30
**Review Cycle:** After each phase gate; mandatory before P4 (pilot) and P5 (production)

---

## Controls Register

| Control ID | Finding | Severity | Status | Implementation | Verified By | Date |
|------------|---------|----------|--------|----------------|-------------|------|
| C-01 | App Insights connection string exposed as plaintext env var | CRITICAL | IMPLEMENTED | main.bicep updated — AI conn string stored as KV secret, Container App uses secretRef | Security Lead | 2026-03-30 |
| C-02 | Key Vault purge protection and soft-delete retention not enforced | CRITICAL | IMPLEMENTED | main.bicep: enablePurgeProtection=true, softDeleteRetentionInDays=90 | Security Lead | 2026-03-30 |
| C-03 | KeeperPAM OAuth2 endpoint not verified against official API docs | CRITICAL | DOCUMENTED | Requires KeeperPAM API doc review with Keeper Security before live run | Pending | — |
| H-01 | Container App not deployed in VNet; Key Vault and SQL exposed to public endpoints | HIGH | IMPLEMENTED | main.bicep: VNet + CA subnet + private endpoints for KV and SQL | Security Lead | 2026-03-30 |
| H-02 | SQL Server firewall open to all Azure IPs; auditing not enabled | HIGH | IMPLEMENTED | main.bicep: firewall scoped to CA subnet, auditing to Log Analytics | Security Lead | 2026-03-30 |
| H-03 | .dockerignore absent — build context may include secrets and output data | HIGH | IMPLEMENTED | .dockerignore excludes config.json, .env, output/, *.key, *.pem | Security Lead | 2026-03-30 |
| H-04 | Dockerfile includes curl and libpq-dev — unnecessary attack surface | HIGH | IMPLEMENTED | Dockerfile updated — unnecessary tools removed from final image | Security Lead | 2026-03-30 |
| H-05 | Container image deployed by mutable tag — image substitution risk | HIGH | DOCUMENTED | deploy.sh updated to capture digest; image signing procedure in IMAGE_SECURITY.md | Pending | — |
| H-06 | Log Analytics workspace and diagnostic settings absent | HIGH | IMPLEMENTED | main.bicep: Log Analytics workspace + diagnostic settings on all 6 resources | Security Lead | 2026-03-30 |
| H-07 | AcrPull, Storage, and SQL RBAC role assignments not in IaC | HIGH | IMPLEMENTED | main.bicep: role assignments added; SQL DB role requires T-SQL grant (documented) | Security Lead | 2026-03-30 |
| H-08 | CyberArk service account granted permanent elevated permissions | HIGH | DOCUMENTED | P0 runbook updated with time-box procedure | Pending | — |
| M-01 | SSL verification can be disabled without hard error | MEDIUM | IMPLEMENTED | keeper_client.py: SSL disabled raises KeeperError in production | Dev Lead | 2026-03-30 |
| M-02 | App Insights connection string not rotatable via Key Vault | MEDIUM | IMPLEMENTED | Moved to Key Vault (C-01 fix covers this) | Dev Lead | 2026-03-30 |
| M-03 | OAuth2 token expiry not tracked — risk of silent auth failure mid-run | MEDIUM | IMPLEMENTED | keeper_client.py: token_expires_at stored, proactive refresh 60s before expiry | Dev Lead | 2026-03-30 |
| M-04 | output/ directory not persisted — data loss on Container App restart | MEDIUM | IMPLEMENTED | main.bicep: Azure Files share + volume mount on Container App | Dev Lead | 2026-03-30 |
| M-05 | No egress restriction — Container App can reach arbitrary internet endpoints | MEDIUM | DOCUMENTED | NETWORK_ISOLATION.md — requires Azure Firewall (cost decision for client) | Pending | — |
| M-06 | No distributed lock enforcing single-instance ETL execution | MEDIUM | DOCUMENTED | maxReplicas=1 enforced at infrastructure layer; coordinator.py state file provides application-level mutex | Dev Lead | 2026-03-30 |
| M-07 | Container image not scanned for OS/package vulnerabilities in pipeline | MEDIUM | DOCUMENTED | IMAGE_SECURITY.md — ACR security scan + Trivy in CI/CD | Pending | — |
| L-01 | No HEALTHCHECK in Dockerfile | LOW | IMPLEMENTED | Dockerfile updated with Python-based health check | Dev Lead | 2026-03-30 |
| L-02 | Key Vault soft-delete retention not set to 90 days | LOW | IMPLEMENTED | Covered by C-02 | Dev Lead | 2026-03-30 |
| L-03 | deploy.sh does not validate input parameters before use | LOW | IMPLEMENTED | deploy.sh validates RG and TAG format before use | Dev Lead | 2026-03-30 |
| L-04 | No documented procedure for rotating secrets after migration | LOW | DOCUMENTED | SECRET_ROTATION.md | Dev Lead | 2026-03-30 |

---

## Control Implementation Evidence

### C-01 — App Insights Connection String → Key Vault

**Finding:** The Application Insights connection string was passed as a plaintext environment variable in the Container App definition, making it visible in ARM/Bicep templates, deployment logs, and `az containerapp show` output.

**Fix Applied:**

1. `main.bicep` stores the connection string as a Key Vault secret during deployment:
   ```bicep
   resource aiConnStringSecret 'Microsoft.KeyVault/vaults/secrets@2023-07-01' = {
     name: '${keyVault.name}/AppInsightsConnectionString'
     properties: { value: appInsightsConnectionString }
   }
   ```
2. Container App environment references the secret via `secretRef` (never plaintext):
   ```bicep
   secrets: [{ name: 'ai-conn-string', keyVaultUrl: aiConnStringSecret.properties.secretUri, identity: 'system' }]
   env: [{ name: 'APPLICATIONINSIGHTS_CONNECTION_STRING', secretRef: 'ai-conn-string' }]
   ```
3. Managed identity on the Container App has `Key Vault Secrets User` role — no client secret required.

**Residual Risk:** None. Secret is never written to deployment output or logs.

---

### C-02 — Key Vault Purge Protection + 90-Day Retention

**Finding:** Key Vault deployed without purge protection or extended soft-delete retention. A deleted or soft-deleted vault could be immediately purged, destroying all migration secrets permanently.

**Fix Applied:**

```bicep
resource keyVault 'Microsoft.KeyVault/vaults@2023-07-01' = {
  properties: {
    enableSoftDelete: true
    softDeleteRetentionInDays: 90
    enablePurgeProtection: true
    ...
  }
}
```

**Residual Risk:** None for accidental deletion. Purge protection is irreversible once set — vault cannot be purged for 90 days after deletion. This is intentional for migration data protection.

---

### C-03 — KeeperPAM OAuth2 Endpoint Verification

**Finding:** The KeeperPAM OAuth2 token endpoint URL is configured in `config.json` without validation against Keeper Security's published API documentation. An incorrect or stale endpoint would cause silent auth failures or route tokens to an unintended endpoint.

**Status:** DOCUMENTED — requires action before P4 (pilot).

**Required Action:**

1. Obtain current KeeperPAM API documentation from Keeper Security account team.
2. Verify `keeperpam_token_url` in `config.example.json` matches the published endpoint for the tenant region.
3. Confirm OAuth2 grant type (`client_credentials`) is supported for the licensed SKU.
4. Document verified endpoint in P0 runbook under "KeeperPAM connectivity check."
5. Update this register: set Status = IMPLEMENTED, Verified By = Security Lead, Date = verification date.

---

### H-01 — VNet Integration + Private Endpoints

**Finding:** Container App deployed without VNet integration. Key Vault and SQL Database had public endpoints accessible from any Azure region or the internet.

**Fix Applied:**

1. VNet with two subnets deployed via `main.bicep`: Container Apps subnet (`/23`) and private endpoint subnet (`/24`).
2. Container App Environment uses internal VNet integration with subnet delegation to `Microsoft.App/environments`.
3. Private endpoints created for Key Vault (`privatelink.vaultcore.azure.net`) and Azure SQL (`privatelink.database.windows.net`).
4. Private DNS zones linked to VNet so Container App resolves private IPs for both services.
5. Key Vault and SQL public network access disabled (`publicNetworkAccess: 'Disabled'`).

See `NETWORK_ISOLATION.md` for full architecture and NSG rules.

---

### H-02 — SQL Server Firewall + Auditing

**Finding:** SQL Server firewall rule used `0.0.0.0` to `255.255.255.255` (allow all Azure). Auditing was not enabled.

**Fix Applied:**

1. Firewall rule replaced with Container Apps subnet CIDR:
   ```bicep
   resource sqlFirewallRule 'Microsoft.Sql/servers/firewallRules@2023-08-01' = {
     name: 'AllowContainerAppsSubnet'
     properties: { startIpAddress: caSubnetStartIp, endIpAddress: caSubnetEndIp }
   }
   ```
2. SQL auditing enabled with 90-day retention to Log Analytics:
   ```bicep
   resource sqlAudit 'Microsoft.Sql/servers/auditingSettings@2023-08-01' = {
     properties: { state: 'Enabled', isAzureMonitorTargetEnabled: true, retentionDays: 90 }
   }
   ```

---

### H-03 — .dockerignore

**Finding:** No `.dockerignore` file. Docker build context included `config.json` (credentials), `output/` (migration data), and key/cert files.

**Fix Applied:** `.dockerignore` created with the following entries:
```
config.json
.env
output/
*.key
*.pem
*.p12
__pycache__/
*.pyc
.git/
```

---

### H-04 — Dockerfile Attack Surface Reduction

**Finding:** `curl` and `libpq-dev` were installed in the final image without a documented requirement. `curl` provides a network exfiltration vector if the container is compromised; `libpq-dev` is a build-time dependency not needed at runtime.

**Fix Applied:** Both packages removed from the `RUN apt-get install` layer in the Dockerfile. Runtime dependencies audited — only `python3-minimal` and required pip packages remain.

---

### H-06 — Log Analytics + Diagnostic Settings

**Finding:** No centralised logging. Container App logs, Key Vault access events, SQL audit events, and Container Registry events were not forwarded to any SIEM or log store.

**Fix Applied:**

Log Analytics workspace deployed in `main.bicep`. Diagnostic settings created for all six resources:
- Container App Environment → Log Analytics (console logs, system logs)
- Key Vault → Log Analytics (AuditEvent, AllMetrics)
- Azure SQL Server → Log Analytics (SQLInsights, Errors, Timeouts, Blocks, Deadlocks)
- Container Registry → Log Analytics (ContainerRegistryLoginEvents, ContainerRegistryRepositoryEvents)
- Storage Account → Log Analytics (StorageRead, StorageWrite, StorageDelete)
- Application Insights → self-ingesting (no additional diag settings required)

Retention: 90 days in Log Analytics (configurable to 730 days for compliance).

---

### H-07 — RBAC Role Assignments

**Finding:** Container App managed identity was not granted required RBAC roles via IaC. The SQL Database `db_datareader`/`db_datawriter` role cannot be assigned via ARM/Bicep (T-SQL only).

**Fix Applied (IaC):**

```bicep
// AcrPull — Container App MI pulls images from ACR
resource acrPullRole 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  scope: containerRegistry
  properties: { roleDefinitionId: acrPullRoleId, principalId: containerApp.identity.principalId }
}
// Storage File Data SMB Share Contributor — mounts Azure Files volume
resource storageRole 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  scope: storageAccount
  properties: { roleDefinitionId: storageFileSmbRoleId, principalId: containerApp.identity.principalId }
}
// Key Vault Secrets User — reads secrets via secretRef
resource kvSecretsUserRole 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  scope: keyVault
  properties: { roleDefinitionId: kvSecretsUserRoleId, principalId: containerApp.identity.principalId }
}
```

**SQL DB Role (T-SQL — run post-deployment):**

```sql
-- Run as SQL admin after deployment
CREATE USER [<container-app-mi-name>] FROM EXTERNAL PROVIDER;
ALTER ROLE db_datareader ADD MEMBER [<container-app-mi-name>];
ALTER ROLE db_datawriter ADD MEMBER [<container-app-mi-name>];
```

This T-SQL step is documented in the P0 runbook under "Post-deployment SQL RBAC."

---

## Outstanding Architectural Decisions

The following controls are documented but require client-specific decisions or infrastructure investment before implementation.

### C-03 — KeeperPAM OAuth2 Endpoint

**Decision Required:** Verify correct OAuth2 token URL for the client's KeeperPAM tenant region with Keeper Security.
**Owner:** Client security team + iOPEX integration lead
**Deadline:** Before P4 (pilot migration)
**Risk if deferred:** Silent authentication failures or token routing to incorrect endpoint

---

### H-05 — Image Tag Pinning + Signing

**Decision Required:**
1. **Tag pinning** (no cost, low effort) — already implemented in `deploy.sh` via digest capture. Container App update to use digest requires one additional CLI step per deployment.
2. **Image signing** (Notary v2 / cosign) — requires toolchain setup in CI/CD pipeline. See `IMAGE_SECURITY.md`.

**Owner:** DevOps lead
**Deadline:** Before P5 (production batches)

---

### H-08 — CyberArk Service Account Time-Boxing

**Decision Required:** Client CyberArk admin must define the permission grant window for the migration service account. Recommended: grant elevated permissions 1 hour before each wave, revoke immediately after heartbeat validation passes.

**Owner:** Client CyberArk admin
**Procedure:** See P0 runbook, section "Service Account Lifecycle"

---

### M-05 — Egress Restriction via Azure Firewall

**Decision Required:** Azure Firewall costs approximately $1.50/hour (~$1,095/month). For a time-boxed migration project, NSG-only egress filtering (no additional cost) may be acceptable.

**Options:**

| Option | Cost | Egress Control |
|--------|------|----------------|
| NSG rules only | $0 | IP/port allow-list, no FQDN filtering |
| Azure Firewall Standard | ~$1,095/month | FQDN filtering, threat intelligence, full logging |
| Azure Firewall Basic | ~$300/month | FQDN filtering, limited features |

**Owner:** Client architecture / finance approval
**See:** `NETWORK_ISOLATION.md` for NSG rule set and Azure Firewall FQDN rule set

---

### M-07 — Container Image Vulnerability Scanning

**Decision Required:** Microsoft Defender for Containers requires Defender for Cloud at ~$15/node/month. Trivy (open source) provides equivalent scanning at no cost in CI/CD.

**Recommendation:** Trivy in CI/CD pipeline (no cost) + Defender for Containers if client already has Defender for Cloud enabled.

**See:** `IMAGE_SECURITY.md` for implementation steps

---

*End of Security Controls Register*

# Runbook 01 — Azure Infrastructure Deployment
## CyberArk → KeeperPAM Migration | SHIFT System

**Scope:** Deploy all Azure resources and push the migration container image.
**Duration:** 2–4 hours
**Prerequisite:** Azure subscription with Contributor access on target resource group.
**Who runs this:** iOPEX delivery engineer

> **Security by Design:** The infrastructure deployed by this runbook is production-grade from day one.
> VNet isolation, private endpoints, Key Vault secret references, Log Analytics, and non-root containers
> are standard architecture — not options to enable later.

---

## Pre-Deployment Checklist

- [ ] `az login` completed, correct subscription active
- [ ] Resource group created (or Contributor access confirmed on existing RG)
- [ ] Docker Desktop running locally
- [ ] KeeperPAM tenant URL, Client ID, Client Secret in hand
- [ ] CyberArk PVWA URL, service account credentials in hand
- [ ] `azure/bicep/parameters.json` reviewed — `envName` and `location` match client naming convention
- [ ] Change management ticket opened (required before deploying to client environment)

---

## Step 1 — Set Subscription Context

```bash
az login
az account list --output table

# Set the correct subscription
az account set --subscription "<subscription-id>"

# Confirm
az account show --query "{name:name, id:id}" --output table
```

> **Security [MEDIUM]:** Record the subscription ID in the change management ticket.
> All resource deployments trace back to this subscription for billing and audit purposes.

---

## Step 2 — Create Resource Group (if not pre-provisioned)

```bash
RG="rg-pam-migration"
LOCATION="eastus"

az group create --name "$RG" --location "$LOCATION"
```

> If the client's Azure team pre-created the RG, skip this step and confirm access:
> ```bash
> az group show --name "$RG" --output table
> ```

> **Security [LOW]:** Apply a resource lock after deployment to prevent accidental deletion
> of the resource group during the migration period:
> ```bash
> az lock create --name "pam-migration-lock" --resource-group "$RG" \
>   --lock-type CanNotDelete --notes "PAM migration in progress — do not delete"
> ```

---

## Step 3 — Review Parameters

```bash
cat azure/bicep/parameters.json
```

Confirm:
- `envName` — used as prefix for all resources (ACR, Key Vault, Storage, SQL, Container App)
- `location` — must match the resource group's region
- `imageTag` — leave as `latest` for initial deploy; a pinned digest is recorded in Step 6

Edit if needed:
```bash
# Example: change envName to match client naming convention
sed -i 's/"pam-migration"/"clientcode-pam"/g' azure/bicep/parameters.json
```

---

## Step 4 — Deploy Infrastructure

```bash
RG="rg-pam-migration"

az deployment group create \
  --resource-group "$RG" \
  --template-file azure/bicep/main.bicep \
  --parameters "@azure/bicep/parameters.json" \
  --output table
```

**Resources provisioned by this deployment:**

| Resource | Type | Security Control |
|----------|------|-----------------|
| `<envName>-vnet` | Virtual Network | Isolates Container App and private endpoints |
| `<envName>-logs` | Log Analytics Workspace | Centralizes all diagnostic logs (90-day retention) |
| `<envName>acr` | Container Registry | AcrPull managed identity; diagnostic logs to workspace |
| `<envName>-kv` | Key Vault | Purge protection on, network ACL default Deny, private endpoint |
| `<envName>store` | Storage Account | Azure Files for `/app/output`; network ACL restricted |
| `<envName>-sql` | SQL Server + Database | Public network disabled; private endpoint; audit logs to workspace |
| `<envName>-ai` | Application Insights | Connection string stored in Key Vault (not plaintext) |
| `<envName>-env` + `<envName>-app` | Container Apps Env + App | VNet-integrated; non-root container (UID 1000) |

> **Security [HIGH]:** All traffic between the Container App and Key Vault, Storage, and SQL
> traverses private endpoints within the VNet — no public internet exposure.
> Verify private DNS zones resolved correctly after deployment.

**Capture outputs:**
```bash
ACR=$(az deployment group show \
  --resource-group "$RG" --name main \
  --query properties.outputs.acrLoginServer.value --output tsv)

KV_URL=$(az deployment group show \
  --resource-group "$RG" --name main \
  --query properties.outputs.keyVaultUri.value --output tsv)

APP_NAME=$(az deployment group show \
  --resource-group "$RG" --name main \
  --query properties.outputs.containerAppName.value --output tsv)

echo "ACR:       $ACR"
echo "Key Vault: $KV_URL"
echo "App:       $APP_NAME"
```

---

## Step 5 — Store Secrets in Key Vault

Store all migration credentials as Key Vault secrets. The Container App managed identity has
Key Vault Secrets User role (provisioned by Bicep). No credentials are stored anywhere else.

> **Security [CRITICAL]:** Credentials exist ONLY in Key Vault. Never in config files, terminal
> history, environment files, or source code. Key Vault has soft delete (90 days) and purge
> protection enabled — secrets cannot be permanently deleted without deliberate admin action.

```bash
KV_NAME="${APP_NAME%-app}-kv"   # derive KV name from app name

# CyberArk source credentials
az keyvault secret set --vault-name "$KV_NAME" \
  --name "CYBERARK-USERNAME" --value "<svc-migration-username>"

az keyvault secret set --vault-name "$KV_NAME" \
  --name "CYBERARK-PASSWORD" --value "<svc-migration-password>"

# KeeperPAM target credentials
az keyvault secret set --vault-name "$KV_NAME" \
  --name "KEEPERPAM-CLIENT-ID" --value "<keeperpam-client-id>"

az keyvault secret set --vault-name "$KV_NAME" \
  --name "KEEPERPAM-CLIENT-SECRET" --value "<keeperpam-client-secret>"
```

**Confirm secrets are accessible to the managed identity:**
```bash
# This tests that the Container App's identity can read a secret
az keyvault secret show --vault-name "$KV_NAME" --name "CYBERARK-USERNAME" \
  --query id --output tsv
```

---

## Step 6 — Build and Push Container Image

Use the deployment script — it validates inputs, captures the image digest, and logs the full deployment:

```bash
./azure/scripts/deploy.sh "$RG" "latest"
```

Or manually:
```bash
# Login to ACR
az acr login --name "${ACR%%.*}"

# Build (note: .dockerignore excludes credentials, output/, .env files)
docker build -t "$ACR/pam-migration:latest" .

# Push
docker push "$ACR/pam-migration:latest"

# Capture image digest — Security [HIGH]
IMAGE_DIGEST=$(docker inspect --format='{{index .RepoDigests 0}}' "$ACR/pam-migration:latest")
echo "Image digest: $IMAGE_DIGEST"
```

> **Security [HIGH]:** Record the image digest in the change management ticket.
> Container image tags (`:latest`) are mutable — the digest is the immutable identifier
> of exactly what code is running in production. Format: `sha256:<64-char-hash>`

**Verify ACR vulnerability scan passed:**
```bash
# ACR Standard tier runs vulnerability scanning on push automatically
az acr repository show-tags --name "${ACR%%.*}" --repository pam-migration --output table

# Check for any critical/high vulnerabilities (must be zero before running P1)
az security assessment list --resource-group "$RG" \
  --query "[?contains(name,'acr')]" --output table
```

---

## Step 7 — Configure Container App Secrets (Key Vault References)

Wire Key Vault secrets into the Container App as environment variables via Key Vault secret
references — the Container App runtime fetches values directly from Key Vault at startup.

> **Security [HIGH]:** Secret references (`secretref:`) mean the credential value is never
> transmitted through the Azure management plane or visible in Container App configuration.
> The managed identity pulls the value directly from Key Vault at container start.

```bash
# Add Key Vault secret references to Container App environment
az containerapp update --name "$APP_NAME" --resource-group "$RG" \
  --set-env-vars \
    "CYBERARK_URL=https://<pvwa.client.internal>/PasswordVault" \
    "KEEPERPAM_URL=https://keepersecurity.com" \
    "CYBERARK_USERNAME=secretref:CYBERARK-USERNAME" \
    "CYBERARK_PASSWORD=secretref:CYBERARK-PASSWORD" \
    "KEEPERPAM_CLIENT_ID=secretref:KEEPERPAM-CLIENT-ID" \
    "KEEPERPAM_CLIENT_SECRET=secretref:KEEPERPAM-CLIENT-SECRET" \
    "LOG_LEVEL=INFO" \
    "DRY_RUN=false"
```

**Grant SQL database-level access (T-SQL — required post-Bicep):**
```bash
# Security [HIGH]: SQL DB roles cannot be set via Bicep — must be done via T-SQL
# Connect to the SQL database as admin and run:
#
#   CREATE USER [<envName>-app] FROM EXTERNAL PROVIDER;   -- managed identity
#   ALTER ROLE db_datareader ADD MEMBER [<envName>-app];
#   ALTER ROLE db_datawriter ADD MEMBER [<envName>-app];
#
# Replace <envName>-app with the Container App name.
# Do NOT grant db_owner — least privilege.
echo "ACTION REQUIRED: Connect to SQL DB and run T-SQL grants (see above)."
```

---

## Step 8 — Verify Deployment

```bash
# Check container app status
az containerapp show --name "$APP_NAME" --resource-group "$RG" \
  --query "{name:name, state:properties.runningStatus}" --output table

# Run preflight inside container
az containerapp exec \
  --name "$APP_NAME" \
  --resource-group "$RG" \
  --command "python3 cli.py preflight"
```

**Expected preflight output:**
```
============================================================
  PREFLIGHT CHECKS
============================================================

  [PASS] Source Adapter (Multi-Vendor)
  [PASS] Discovery & Dependency Mapping
  [PASS] Dependency Mapper
  [PASS] NHI Handler
  [PASS] Gap Analysis
  [PASS] Permission Mapping & Translation
  [PASS] ETL Orchestration
  [PASS] Heartbeat & Validation
  [PASS] Integration Repointing (CCP/AAM)
  [PASS] Compliance & Audit
  [PASS] Runbook Execution
  [PASS] Staging Validation
  [PASS] Platform Plugin Validator
  [PASS] App Onboarding Factory
  [PASS] Hybrid Fleet Manager

============================================================
```

Any `[FAIL]` — check credentials in Key Vault and network connectivity from the Container App
to CyberArk PVWA and KeeperPAM.

---

## Step 9 — Initialize Migration

```bash
MIGRATION_ID="shift-$(date +%Y%m%d)-001"

az containerapp exec \
  --name "$APP_NAME" \
  --resource-group "$RG" \
  --command "python3 cli.py start $MIGRATION_ID"

# Verify state initialized
az containerapp exec \
  --name "$APP_NAME" \
  --resource-group "$RG" \
  --command "python3 cli.py status"
```

> **Security [MEDIUM]:** Log the Migration ID (`shift-YYYYMMDD-001`) in the change management
> ticket. This ID is the primary key for all audit logs, state files, and compliance evidence
> generated throughout the migration.

---

## Rollback

If deployment fails at any step:

```bash
# Remove deployment without deleting the resource group
az deployment group delete \
  --resource-group "$RG" --name main

# Or delete the entire resource group (destructive — confirm with client and change management)
az group delete --name "$RG" --yes --no-wait
```

> **Security [MEDIUM]:** Key Vault secrets are soft-deleted (90-day retention) even after
> resource group deletion. If re-deploying to a new RG, create fresh Key Vault secrets
> rather than trying to recover from soft-delete.

---

## Next Step

→ **[P0_environment_setup.md](P0_environment_setup.md)** — Configure `config.json`, verify network paths, run agent-level connectivity tests.

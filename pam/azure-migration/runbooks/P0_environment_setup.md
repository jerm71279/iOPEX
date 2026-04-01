# Runbook P0 — Environment Setup
## CyberArk → KeeperPAM Migration | SHIFT System

**Scope:** Configure `config.json`, validate network connectivity, confirm service account permissions.
**Duration:** 1–2 days
**Prerequisite:** [01_azure_deployment.md](01_azure_deployment.md) complete — container running, secrets in Key Vault.
**Who runs this:** iOPEX delivery engineer + client infrastructure team

> **Security by Design:** Service accounts follow least-privilege. Network paths are confirmed
> before any credentials are used. All connectivity tests use the Python application layer
> (not shell tools) so outbound traffic is traceable through the application's audit log.

---

---

## DP-01 — Decision Point: Operator Trigger Method

**Decide this before starting P0. It determines how migration phases are triggered throughout the engagement.**

The 15 SHIFT agents run inside the Azure Container App. Something must tell them when to run.
There are three options. **Option B is recommended.**

| Option | Description | Effort | Recommended |
|--------|-------------|--------|-------------|
| **A — Manual CLI** | Delivery engineer types `az containerapp exec` commands directly at the terminal. No tooling dependency. Works on any machine with `az` installed. | None | Fallback only |
| **B — OpenClaw → Azure** | OpenClaw (AI PMO agent, runs on delivery engineer's PC) issues `az containerapp exec` commands as tools. Engineer asks OpenClaw to run a phase; OpenClaw executes it and reports back. Requires `az` CLI installed and logged in on the PC. | Low — update TOOLS.md | **Recommended** |
| **C — OpenClaw in Azure** | OpenClaw deployed as an Azure Container Instance or second Container App. No PC dependency — can trigger migrations on schedule or via webhook. OpenClaw not currently designed for cloud deployment. | High — future option | Future |

### Choosing Option B (Recommended)

Option B keeps OpenClaw on the delivery engineer's PC (its current home) but gives it the ability to reach into Azure and trigger the migration Container App directly. The engineer talks to OpenClaw; OpenClaw handles the `az` command syntax, monitors output, and feeds results back.

**What this looks like in practice:**
```
Jeremy → OpenClaw: "Run P5 Wave 3"

OpenClaw executes:
  az containerapp exec \
    --name pam-migration-app \
    --resource-group rg-pam-migration \
    --command "python3 cli.py run P5"

OpenClaw reads output, updates PMO state, reports results to Jeremy.
```

**Prerequisites for Option B:**
- [ ] `az` CLI installed on the delivery engineer's PC
- [ ] `az login` completed with an account that has `Container Apps Contributor` on the RG
- [ ] OpenClaw `shift-pmo` TOOLS.md updated with `az containerapp exec` wrapper (see below)
- [ ] `APP_NAME` and `RG` captured from deployment output and added to TOOLS.md

**TOOLS.md update for Option B:**

Open `/home/maverick/.openclaw/agents/shift-pmo/TOOLS.md` and add:

```markdown
## Azure Execution — Container App Trigger

Resource Group : rg-pam-migration
Container App  : <APP_NAME from deploy output>

### Run a phase
az containerapp exec \
  --name <APP_NAME> --resource-group rg-pam-migration \
  --command "python3 cli.py run P{N}"

### Run a single agent
az containerapp exec \
  --name <APP_NAME> --resource-group rg-pam-migration \
  --command "python3 cli.py agent {agent-key} --phase P{N}"

### Check migration status
az containerapp exec \
  --name <APP_NAME> --resource-group rg-pam-migration \
  --command "python3 cli.py status"

### Dry run (no real API calls)
az containerapp exec \
  --name <APP_NAME> --resource-group rg-pam-migration \
  --command "python3 cli.py run P{N} --dry-run"
```

**Decision recorded:** Enter chosen option in the change management ticket before proceeding.

---

## DP-02 — Decision Point: OpenClaw LLM Provider

**Decide this before starting P0 if using Option B. It determines which AI model powers the shift-pmo PMO agent.**

OpenClaw (`shift-pmo`) runs on the delivery engineer's PC and requires an LLM to interpret intent and generate responses. The current default is Claude Sonnet (Anthropic API). For live client engagements, consider whether data residency or enterprise compliance requirements dictate a different provider.

**When to decide:** P0, day one of the live engagement — before any migration phases are triggered.
Switch from Claude Sonnet (demo default) to Azure OpenAI at this point. Do not run live migration phases on the Anthropic API.

| Option | Model | Provider | Data Residency | Recommended |
|--------|-------|----------|----------------|-------------|
| **A — Claude Sonnet** | `claude-sonnet-4-20250514` | Anthropic API | Anthropic (US) | Demo / dev only |
| **B — GPT-4o via Azure OpenAI + LiteLLM** | `azure/gpt-4o` | Azure OpenAI (your tenant) | Azure region of choice | **Live engagement — implement at P0** |
| **C — GPT-4o mini via Azure OpenAI + LiteLLM** | `azure/gpt-4o-mini` | Azure OpenAI (your tenant) | Azure region of choice | Budget option |
| **D — Phi-4 via Ollama** | `phi4` | Local (no API) | On-device | Offline / air-gapped |

### Choosing Option B for Live Engagement

Option B keeps all PMO conversation data inside the client's Azure tenant — important for Cisco's security posture. LiteLLM acts as a local proxy between OpenClaw and Azure OpenAI.

**Architecture:**
```
OpenClaw (shift-pmo) on PC
  → LiteLLM proxy (localhost:4000 or Azure Container)
    → Azure OpenAI (GPT-4o, deployed in client Azure tenant)
```

**Prerequisites for Option B:**
- [ ] Azure OpenAI resource deployed in the engagement Azure subscription
- [ ] GPT-4o model deployed (deployment name: e.g., `gpt-4o-pam-migration`)
- [ ] LiteLLM running (Docker one-liner below)
- [ ] OpenClaw `openclaw.json` updated with `litellm` provider and model string

**LiteLLM setup (one Docker command on delivery engineer's PC):**

```bash
# Set your Azure OpenAI values
export AZURE_API_KEY="<your-azure-openai-key>"
export AZURE_API_BASE="https://<your-resource>.openai.azure.com"
export AZURE_API_VERSION="2024-02-01"

docker run -d \
  --name litellm-proxy \
  -p 4000:4000 \
  -e AZURE_API_KEY="$AZURE_API_KEY" \
  -e AZURE_API_BASE="$AZURE_API_BASE" \
  -e AZURE_API_VERSION="$AZURE_API_VERSION" \
  ghcr.io/berriai/litellm:main \
  --model azure/gpt-4o=gpt-4o-pam-migration
```

**Update OpenClaw config for shift-pmo:**

Edit `/home/maverick/.openclaw/openclaw.json` — change the `shift-pmo` agent entry:

```json
{
  "id": "shift-pmo",
  "name": "shift-pmo",
  "workspace": "/home/maverick/.openclaw/agents/shift-pmo",
  "agentDir": "/home/maverick/.openclaw/agents/shift-pmo/agent",
  "model": "litellm/azure/gpt-4o"
}
```

Set the LiteLLM API key in your environment (LiteLLM master key — set to any string for local use):
```bash
export LITELLM_API_KEY="sk-local-pam-migration"
```

**Verify:**
```bash
curl http://localhost:4000/health
```
Expected: `{"status": "healthy"}`

> **Security [MEDIUM]:** LiteLLM runs locally — PMO conversation content never leaves the PC except to Azure OpenAI. Azure OpenAI with `data_logging=false` (default) does not use prompts for model training. Confirm with the client's Azure OpenAI deployment settings.

**Decision recorded:** Enter chosen option in the change management ticket before proceeding.

---

## P0 Checklist

- [ ] **DP-01 decision recorded** — Option A / B / C chosen and noted in change management ticket
- [ ] If Option B: `az` CLI installed on delivery engineer's PC, `az login` complete
- [ ] If Option B: OpenClaw `shift-pmo` TOOLS.md updated with Container App name and RG
- [ ] **DP-02 decision recorded** — LLM provider chosen and noted in change management ticket
- [ ] If DP-02 Option B/C: Azure OpenAI resource deployed, GPT-4o model deployed, LiteLLM container running
- [ ] If DP-02 Option B/C: OpenClaw `openclaw.json` updated with `litellm/azure/gpt-4o` model string
- [ ] CyberArk PVWA reachable from Container App (outbound 443)
- [ ] KeeperPAM URL reachable from Container App (outbound 443)
- [ ] CyberArk service account created with required permissions
- [ ] KeeperPAM OAuth2 client created with required scopes
- [ ] `config.json` created from template and populated
- [ ] All preflight checks passing (15/15)
- [ ] Output directory mounted and writable (Azure Files volume)
- [ ] SQL database roles granted (T-SQL step from Runbook 01 Step 7)

---

## Step 1 — CyberArk Service Account Requirements

Work with the client's CyberArk admin to create a dedicated migration service account.

> **Security [HIGH]:** Use a dedicated service account (`svc-iopex-migration`) — never a
> personal admin account. This account is revoked at P7 decommission. Dedicated accounts
> limit blast radius if credentials are compromised and provide clean audit attribution.

**Required CyberArk PVWA permissions:**

| Permission | Required For | Sensitive? |
|------------|-------------|-----------|
| Logon | Authentication | |
| List Accounts | Discovery (Agent 01) | |
| Retrieve Accounts | ETL password export (Agent 04) | Yes — grants password access |
| View Safe Members | Permission mapping (Agent 03) | |
| Manage Safe Members | Permission apply (P3) | Yes — can modify access |
| Access Without Confirmation | Retrieval without dual control | Yes — bypasses approval |
| View Audit Log | Compliance evidence (Agent 07) | |
| Activate Users | CPM freeze/unfreeze (Agent 04) | |

> **Security [MEDIUM]:** The `AccessWithoutConfirmation` and `ManageSafeMembers` permissions
> are elevated. Document in the change management ticket that these are granted to
> `svc-iopex-migration` only for the migration period and will be revoked at P7.

**Recommended:** Create a dedicated `iOPEX-Migration` safe. Add `svc-iopex-migration` as a member
of ALL safes to be migrated with at minimum `ListAccounts` + `RetrieveAccounts` + `ViewSafeMembers`.

---

## Step 2 — KeeperPAM OAuth2 Client Setup

Work with the client's KeeperPAM admin to create an API client for the migration.

> **Security [HIGH]:** Create a migration-specific OAuth2 client (`pam-migration-iopex`) that is
> separate from any operational clients. This client is revoked at P7 close-out. Never reuse
> an existing operational client — if credentials are compromised during migration, revocation
> affects only migration activity, not live PAM operations.

**Required KeeperPAM scopes (verify against KeeperPAM API docs):**
- Vault creation and management
- Record creation and bulk import
- Member permission assignment
- Record type (platform) management
- Password retrieval for heartbeat validation

**Capture:**
- `KEEPERPAM_URL` — tenant base URL (e.g., `https://keepersecurity.com`)
- `KEEPERPAM_CLIENT_ID` — OAuth2 client ID
- `KEEPERPAM_CLIENT_SECRET` — OAuth2 client secret

Store in Key Vault (see [01_azure_deployment.md](01_azure_deployment.md) Step 5).

> **Security [MEDIUM]:** Confirm with the KeeperPAM admin that the OAuth2 client secret
> has a defined expiry. If KeeperPAM supports it, set a 90-day expiry aligned with the
> migration timeline. Rotate mid-migration if the client has a shorter rotation policy.

---

## Step 3 — Create config.json

```bash
# Run inside the container or locally before building
cp config.example.json config.json
```

Edit `config.json`:

```json
{
  "cyberark_on_prem": {
    "base_url": "https://pvwa.client.internal/PasswordVault",
    "auth_type": "LDAP",
    "verify_ssl": true,
    "timeout": 30,
    "max_retries": 3,
    "retry_delay": 1.0,
    "rate_limit": 0.1,
    "batch_size": 1000
  },
  "keeperpam": {
    "base_url": "https://keepersecurity.com",
    "auth_method": "oauth2",
    "verify_ssl": true,
    "timeout": 30,
    "max_retries": 3,
    "retry_delay": 1.0,
    "rate_limit": 0.1,
    "batch_size": 500
  },
  "output_dir": "./output",
  "log_level": "INFO",
  "environment": "production"
}
```

> **Security [CRITICAL]:** `verify_ssl` MUST be `true` in production. Setting it to `false`
> allows man-in-the-middle attacks against credential traffic. The application will refuse
> to authenticate if `base_url` does not start with `https://`.

> **Never commit config.json** — it is gitignored. In Azure, credentials come from Key Vault
> via Container App secret references. The `config.json` only needs non-sensitive connection
> parameters (base URLs, timeouts, batch sizes).

---

## Step 4 — Set Environment Variables

Credentials come from Key Vault via Container App secret references (set in
[01_azure_deployment.md](01_azure_deployment.md) Step 7). For local testing only:

```bash
export CYBERARK_USERNAME="svc-iopex-migration"
export CYBERARK_PASSWORD="<password>"
export KEEPERPAM_CLIENT_ID="<client-id>"
export KEEPERPAM_CLIENT_SECRET="<client-secret>"
```

> **Security [HIGH]:** For local testing, use a `.env` file (gitignored) and load with
> `set -a && source .env && set +a`. Never type credentials directly at the terminal
> — they persist in shell history.

---

## Step 5 — Network Connectivity Tests

The container image does not include `curl` or `wget` — this is intentional. All outbound
connectivity from the container goes through the Python application layer, which is logged
and audited. Use Python-based tests:

```bash
# Test CyberArk PVWA reachability via Python
az containerapp exec \
  --name "$APP_NAME" --resource-group "$RG" \
  --command "python3 -c \"
import urllib.request, ssl
ctx = ssl.create_default_context()
try:
    r = urllib.request.urlopen('https://pvwa.client.internal/PasswordVault/api/Auth/checkAuth', context=ctx, timeout=10)
    print('PVWA reachable — HTTP', r.status)
except urllib.error.HTTPError as e:
    print('PVWA reachable — HTTP', e.code, '(expected 401 = not authenticated)')
except Exception as e:
    print('PVWA UNREACHABLE:', e)
\""

# Test KeeperPAM reachability
az containerapp exec \
  --name "$APP_NAME" --resource-group "$RG" \
  --command "python3 -c \"
import urllib.request, ssl
ctx = ssl.create_default_context()
try:
    r = urllib.request.urlopen('https://keepersecurity.com', context=ctx, timeout=10)
    print('KeeperPAM reachable — HTTP', r.status)
except urllib.error.HTTPError as e:
    print('KeeperPAM reachable — HTTP', e.code)
except Exception as e:
    print('KeeperPAM UNREACHABLE:', e)
\""
```

**Expected results:**
- PVWA: `HTTP 401` — reachable, not authenticated (correct)
- KeeperPAM: `HTTP 200` or `HTTP 301` — reachable

If PVWA is internal (private IP / private DNS):
- VNet integration is already provisioned by the Bicep deployment
- Confirm the client has peered the Azure VNet to their on-prem network (VPN / ExpressRoute)
- DNS resolution for `pvwa.client.internal` must resolve from within the Container Apps subnet

> **Security [HIGH]:** Confirm TLS certificate validity for PVWA before proceeding.
> A private CA cert may need to be added to the container trust store. If the client
> uses an internal PKI, add the root CA cert to the Docker image during build.

---

## Step 6 — Run All Preflight Checks

```bash
az containerapp exec \
  --name "$APP_NAME" --resource-group "$RG" \
  --command "python3 cli.py preflight"
```

All 15 agents must show `[PASS]`. For any `[FAIL]`:

| Failure | Likely Cause | Fix |
|---------|-------------|-----|
| Source Adapter | PVWA unreachable or bad credentials | Check network + Key Vault secrets |
| Discovery | PVWA auth failing | Verify `CYBERARK_USERNAME` / `CYBERARK_PASSWORD` |
| Staging Validation | No staging tenant URL in config | Add `keeperpam.base_url` to config |
| ETL | Missing discovery data | Run P1 first (expected at P0) |
| Platform Plugin | PVWA API version mismatch | Check PVWA version supports `/Platforms/Targets` |

---

## Step 7 — Initialize Migration State

```bash
MIGRATION_ID="shift-$(date +%Y%m%d)-001"

az containerapp exec \
  --name "$APP_NAME" --resource-group "$RG" \
  --command "python3 cli.py start $MIGRATION_ID"

# Verify
az containerapp exec \
  --name "$APP_NAME" --resource-group "$RG" \
  --command "python3 cli.py status"
```

Expected output:
```
Migration ID : shift-YYYYMMDD-001
Phase        : P0
Status       : in_progress
Started      : YYYY-MM-DDTHH:MM:SSZ
```

---

## Step 8 — Verify Output Directory Structure

The output directory is mounted as an Azure Files volume at `/app/output`.
State files, audit logs, and reports persist across container restarts.

```bash
az containerapp exec \
  --name "$APP_NAME" --resource-group "$RG" \
  --command "python3 -c \"
import os, stat
base = '/app/output'
for d in ['logs', 'reports', 'state', 'state/raw']:
    path = os.path.join(base, d)
    exists = os.path.isdir(path)
    writable = os.access(path, os.W_OK) if exists else False
    print(f'  {path}: exists={exists}, writable={writable}')
\""
```

> **Security [MEDIUM]:** The output directory contains audit logs and (encrypted) state files.
> Azure Files enforces storage account network ACLs — access is restricted to the VNet.
> The lifecycle policy moves logs to archive tier after 90 days for cost management while
> maintaining the 7-year PCI-DSS retention requirement.

If `output/` is missing subdirectories, the coordinator creates them automatically on first run.

---

## Step 9 — Advance to P1

After all checks pass and client has reviewed and signed the migration plan:

```bash
az containerapp exec \
  --name "$APP_NAME" --resource-group "$RG" \
  --command "python3 cli.py advance"
```

---

## P0 Sign-Off

Before advancing, confirm with client:

| Item | Owner | Status |
|------|-------|--------|
| Service account `svc-iopex-migration` created with documented permissions | Client CyberArk admin | |
| KeeperPAM OAuth2 client `pam-migration-iopex` created | Client KeeperPAM admin | |
| Credentials stored in Key Vault (not config files) | iOPEX | |
| Network path from Azure Container App to PVWA confirmed (HTTP 401 test) | iOPEX + Client Infra | |
| SQL database roles granted (T-SQL step) | iOPEX | |
| Migration ID logged in change management system | iOPEX PMO | |
| Image digest recorded in change management ticket | iOPEX | |

---

## Next Step

→ **[P1_discovery.md](P1_discovery.md)** — Full source system discovery, dependency mapping, NHI classification, gap analysis.

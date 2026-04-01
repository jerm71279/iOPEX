# Runbook 02 — Stakeholder Dashboard
## CyberArk → KeeperPAM Migration | SHIFT System

**Scope:** Activate the SHIFT Migration Control Center for live stakeholder visibility.
Share the dashboard URL with iOPEX team and client (Cisco). Dashboard auto-refreshes
every 60 seconds from Azure Blob Storage as the migration progresses.
**Duration:** 30 minutes
**Prerequisite:** [01_azure_deployment.md](01_azure_deployment.md) complete — Bicep deployed, deploy.sh run.
**Who runs this:** iOPEX delivery engineer
**Audience:** iOPEX delivery team + Cisco migration stakeholders (read-only)

---

## How It Works

```
Azure Container App (migration runs)
  └── After every agent completes automatically:
        core/dashboard_export.py
          ├── Reads current phase & status from migration state
          ├── Reads agent report JSON files (ETL counts, heartbeat rates, compliance)
          ├── Reads last 10 audit log entries for activity feed
          └── Uploads status.json ──────────────────────────────────────────┐
                                                                             │
Azure Blob Storage (public read, non-sensitive data only)                    │
  https://<envName>dash.blob.core.windows.net/dashboard/status.json ◄────────┘
                                             │
                                             │  (fetched every 60 seconds)
                                             ▼
                              SHIFT Migration Control Center
                         (browser — iOPEX team + Cisco stakeholders)
```

**What the blob contains:** Phase progress, account counts, heartbeat pass rates, agent
statuses, wave results, Yellow Checkpoint states, compliance evidence summary, recent
activity log. No credentials, no raw account data, no audit log hashes.

---

## Step 1 — Get the Dashboard Blob URL

The blob URL is output by the deployment script. Retrieve it:

```bash
RG="rg-pam-migration"

DASHBOARD_URL=$(az deployment group show \
  --resource-group "$RG" \
  --name main \
  --query properties.outputs.dashboardUrl.value \
  --output tsv)

echo "Dashboard blob URL: $DASHBOARD_URL"
```

Expected format:
```
https://<envName>dash.blob.core.windows.net/dashboard/status.json
```

> **Note:** If deploy.sh was run, the Container App already has `DASHBOARD_STORAGE_URL`
> set as an environment variable and will publish updates automatically. Verify:
> ```bash
> az containerapp show --name "$APP_NAME" --resource-group "$RG" \
>   --query "properties.template.containers[0].env[?name=='DASHBOARD_STORAGE_URL'].value" \
>   --output tsv
> ```

---

## Step 2 — Trigger the First Status Export

Before sharing the URL, confirm the blob contains live data:

```bash
az containerapp exec \
  --name "$APP_NAME" --resource-group "$RG" \
  --command "python3 cli.py status"
```

Then manually trigger the first export:

```bash
az containerapp exec \
  --name "$APP_NAME" --resource-group "$RG" \
  --command "python3 -c \"
from core.dashboard_export import DashboardExporter
from core.state import MigrationState
import json

with open('config.json') as f:
    config = json.load(f)

state = MigrationState(state_dir='output/state')
exp = DashboardExporter(config, state, 'output/state')
ok = exp.export()
print('Export OK:', ok)
\""
```

**Verify the blob is live:**
```bash
curl -s "$DASHBOARD_URL" | python3 -c "
import json, sys
d = json.load(sys.stdin)
print('Migration ID:', d['meta']['migration_id'])
print('Phase:       ', d['meta']['current_phase'])
print('Last updated:', d['meta']['last_updated'])
print('Accounts:    ', d['dashboard']['stats']['total_accounts'])
"
```

---

## Step 3 — Activate Live Mode in the Control Center

Open the Control Center's `frontend/index.html` and set the blob URL:

```html
<script>
  window.DASHBOARD_CONFIG = {
    blobUrl: "https://<envName>dash.blob.core.windows.net/dashboard/status.json",
    pollInterval: 60
  };
</script>
```

Replace `<envName>dash` with the actual storage account name from Step 1.

After this change:
- The sidebar shows **"Updated HH:MM:SS"** in green when live data loads
- All dashboard pages populate from the blob instead of mock data
- The dashboard auto-refreshes every 60 seconds without any user action
- Demo mode (empty `blobUrl`) is preserved for sales presentations

**Redeploy the Control Center** to publish the updated `index.html`:

```bash
# If hosted on Render.com (current config):
git add frontend/index.html
git commit -m "feat: activate live dashboard for Cisco migration"
git push origin main
# Render auto-deploys on push

# If hosted on Azure Static Web Apps:
az staticwebapp deploy \
  --name "shift-control-center" \
  --resource-group "$RG" \
  --source ./frontend
```

---

## Step 4 — Share the Dashboard URL

Share the Control Center URL (not the blob URL) with stakeholders.
The blob URL is an internal implementation detail — stakeholders only need the app URL.

**iOPEX team:**

| Role | Access |
|------|--------|
| Delivery Engineer | Full dashboard — all pages |
| Project Manager | Mission Control + Gate Tracker + Yellow Checkpoints |
| Practice Lead | All pages + compliance evidence |

**Cisco stakeholders:**

| Role | Recommended View | Page |
|------|-----------------|------|
| Executive Sponsor | Overall progress, gates passed | Mission Control |
| IT Project Manager | Phase timeline, wave schedule | Phase Explorer + Wave Execution |
| CISO / Security Lead | Compliance evidence, heartbeat rates | Agents + Yellow Checkpoints |
| CyberArk Admin | Parallel running status, fleet | Wave Execution + Gate Tracker |
| App Team Leads | Integration repointing status | Agents (Agent 06) |

> **Note:** The dashboard is read-only — stakeholders cannot trigger approvals or
> advance phases through it. All gate approvals go through iOPEX delivery engineer
> + client sign-off via change management, as documented in each phase runbook.

---

## Step 5 — Verify Auto-Update Cadence

Confirm the blob updates after migration runs:

| Trigger | When update appears |
|---------|-------------------|
| `python3 cli.py run P1` | After each of the 6 P1 agents completes |
| `python3 cli.py run P5` | After each wave agent (ETL, heartbeat, integration, compliance) |
| `python3 cli.py advance` | Immediately after phase advance |
| Manual: `cli.py agent 05-heartbeat` | After agent run completes |

The sidebar **"Updated HH:MM:SS"** timestamp shows the last time the browser received
fresh data. If it stops updating, check:

```bash
# Check Container App is running
az containerapp show --name "$APP_NAME" --resource-group "$RG" \
  --query "properties.runningStatus" --output tsv

# Check blob was written recently (Last-Modified header)
curl -sI "$DASHBOARD_URL" | grep -i "last-modified"
```

---

## Dashboard Pages — What Stakeholders See

| Page | Key Information | Updates When |
|------|----------------|-------------|
| **Mission Control** | Phase timeline, account counts, active agents, NHI count, gates passed | Every agent run |
| **Phase Explorer** | P0–P7 detail, agent sequence per phase, duration | Phase advance |
| **Agents** | All 15 agents — status (pending / active / complete), last run | Every agent run |
| **Wave Execution** | 5 waves — account counts, ETL step animation, heartbeat pass rate | After each wave ETL |
| **Account Explorer** | Total / migrated / failed / pending counts, migration % | After ETL agents |
| **Gate Tracker** | 7 Yellow Checkpoint gates — pending / active / passed | Phase advance |
| **Yellow Checkpoints** | Approval requirements per gate, who must sign off | Phase advance |
| **Compliance** | Frameworks evidenced (PCI-DSS, NIST, HIPAA, SOX), open gaps | After Agent 07 runs |

---

## Troubleshooting

| Issue | Cause | Fix |
|-------|-------|-----|
| Sidebar shows "Demo mode" | `blobUrl` not set in `index.html` | Complete Step 3 |
| Blob returns 404 | Container App hasn't run yet | Run Step 2 (manual export) |
| Data is stale | Container App stopped between phases | Normal — updates on next `cli.py run` |
| CORS error in browser | Browser policy blocking cross-origin fetch | Confirm `allowBlobPublicAccess: true` in Bicep; CORS rule deployed |
| Blob URL not in deploy output | Old Bicep deployment pre-dashboard | Re-run `az deployment group create` with updated `main.bicep` |

---

## After the Migration Completes (P7)

Once P7 closes:

1. The final `dashboard_status.json` blob remains accessible as a read-only record
2. Update `blobUrl` to point to the archived final state (or leave as-is)
3. The Control Center shows the final completed view — a reference for post-migration audits
4. Optionally revoke public blob access after the project close-out period

```bash
# After P7 — lock down the dashboard storage (optional, 90 days post-cutover)
az storage container set-permission \
  --account-name "${ENVNAME}dash" \
  --name "dashboard" \
  --public-access "off" \
  --auth-mode login
```

---

## Next Step

→ **[P0_environment_setup.md](P0_environment_setup.md)** — Service accounts, config.json, network connectivity, preflight checks.

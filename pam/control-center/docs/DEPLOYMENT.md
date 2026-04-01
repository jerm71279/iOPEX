# Deployment — PAM Migration Control Center (SHIFT)

## Environments

| Environment | Stack | When to Use |
|---|---|---|
| Local dev | `docker-compose up` | Day-to-day development |
| Frontend-only | `python3 -m http.server 8080` | UI iteration, no backend needed |
| Production demo | Docker Compose on engagement VM | Client-facing demos |
| Live engagement | Docker Compose + Redis + KV | P4+ of actual KeeperPAM migration |

---

## Local Development

### Prerequisites

- Docker + Docker Compose
- Python 3.12+ (frontend-only mode only)

### Full stack

```bash
cd /home/maverick/projects/iOPEX/pam/control-center
docker-compose up
```

Services started:

| Service | URL | Purpose |
|---|---|---|
| control-center | http://localhost:8080 | Dashboard SPA + FastAPI |
| pam-migration-mcp | http://localhost:8100 | Migration orchestrator MCP tools |
| control-center-mcp | http://localhost:8101 | Dashboard MCP proxy |

### Frontend only

```bash
cd frontend && python3 -m http.server 8080
# Open http://localhost:8080
```

### Backend only

```bash
cd backend
pip install -r requirements.txt
uvicorn app:app --reload --port 8000
```

### Health check

```bash
curl http://localhost:8080/api/dashboard/stats
```

---

## Environment Variables

### Control Center (`backend/.env`)

| Variable | Required | Default | Description |
|---|---|---|---|
| `API_HOST` | No | `0.0.0.0` | FastAPI bind address |
| `API_PORT` | No | `8000` | FastAPI port |
| `ENVIRONMENT` | No | `dev` | `dev` or `production` |
| `DATABASE_URL` | Prod only | — | PostgreSQL URL for persistent state (P0 blocker) |
| `NHI_MODEL_PATH` | No | auto | Path to saved LightGBM model |
| `ANOMALY_MODEL_PATH` | No | auto | Path to saved Isolation Forest model |
| `CYBERARK_BASE_URL` | Live only | — | On-prem PVWA base URL |
| `CYBERARK_USERNAME` | Live only | — | PVWA service account username |
| `CYBERARK_PASSWORD` | Live only | — | PVWA service account password |
| `DASHBOARD_SECRET_KEY` | Prod only | — | JWT / API key for dashboard auth (P0 blocker) |

### PAM Migration MCP Server

| Variable | Required | Default | Description |
|---|---|---|---|
| `PAM_MCP_MIGRATION_OPTION` | Yes | `b` | `a` = Privilege Cloud, `b` = Secret Server |
| `PAM_MCP_ENVIRONMENT` | Yes | `dev` | `dev` skips KV startup gate; never use in prod |
| `PAM_MCP_PORT` | No | `8100` | MCP server port |
| `PAM_MCP_CYBERARK_BASE_URL` | Live only | — | On-prem PVWA URL |
| `PAM_MCP_CYBERARK_AUTH_TYPE` | No | `LDAP` | CyberArk auth type: `LDAP`, `CyberArk`, `RADIUS` |
| `PAM_MCP_CYBERARK_VERIFY_SSL` | No | `true` | Set `false` for self-signed certs (dev only) |
| `PAM_MCP_KEY_VAULT_URI` | Prod only | — | Azure Key Vault URI (e.g. `https://kv-pam.vault.azure.net/`) |
| `PAM_MCP_WATCHDOG_TIMEOUT_MINUTES` | No | `120` | Auto-unfreeze timeout |
| `PAM_MCP_ORCHESTRATOR_PATH_A` | Prod only | `/orchestrator-a` | Mount path for Privilege Cloud orchestrator |
| `PAM_MCP_ORCHESTRATOR_PATH_B` | Prod only | `/orchestrator-b` | Mount path for Secret Server orchestrator |
| `PAM_MCP_OUTPUT_DIR` | No | `./output` | Shared state volume path |

### Control Center MCP Server

| Variable | Required | Default | Description |
|---|---|---|---|
| `CC_MCP_PORT` | No | `8101` | MCP proxy port |
| `CC_MCP_CONTROL_CENTER_URL` | No | `http://control-center:8080` | Internal CC URL |

---

## Production Deployment (Live Engagement)

### Azure Prerequisites (complete before P4 gate g5)

These must be confirmed before setting `PAM_MCP_ENVIRONMENT=production`.

1. **Azure Key Vault provisioned** with PAM credentials loaded:
   - `cyberark-username` → `CYBERARK_USERNAME`
   - `cyberark-password` → `CYBERARK_PASSWORD`
   - `pcloud-client-id` / `pcloud-client-secret` (Option B)
   - `ss-client-id` / `ss-client-secret` (Option A)

2. **Managed Identity assigned** to the orchestrator VM or container with `Key Vault Secrets User` role on the KV resource.

3. **Network access**: if the KV is private-endpoint-only, the orchestrator must be in the approved VNet or subnet. Confirm with `az keyvault show --name kv-pam --query networkAcls`.

4. **Startup gate behavior**: when `PAM_MCP_ENVIRONMENT != dev` and `PAM_MCP_KEY_VAULT_URI` is set, the MCP server will **refuse to start** if `CYBERARK_USERNAME` or `CYBERARK_PASSWORD` fail to load from KV. This is intentional — a credential-less server must not run against a live PVWA. Fix the KV access before retrying.

### docker-compose override for production

Create `docker-compose.prod.yml`:

```yaml
services:
  pam-migration-mcp:
    environment:
      - PAM_MCP_ENVIRONMENT=production
      - PAM_MCP_KEY_VAULT_URI=https://kv-pam.vault.azure.net/
      - PAM_MCP_CYBERARK_BASE_URL=https://pvwa.client.com
      - PAM_MCP_MIGRATION_OPTION=b
    volumes:
      - /path/to/keeperpam-orchestrator:/orchestrator-b:ro

  control-center:
    environment:
      - ENVIRONMENT=production
      - DATABASE_URL=postgresql://shift:pass@redis-host:5432/shift
      - DASHBOARD_SECRET_KEY=<strong-random-key>
```

Run with:

```bash
docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d
```

### Redis (persistent state — required before P4)

Add to `docker-compose.prod.yml`:

```yaml
services:
  redis:
    image: redis:7-alpine
    restart: unless-stopped
    volumes:
      - redis-data:/data

volumes:
  redis-data:
```

Set `DATABASE_URL` in control-center to point at Redis or PostgreSQL per the state backend chosen.

---

## Render.com (Public Demo)

1. Connect repo `jerm71279/pam-control-center` to Render.com
2. Runtime: **Docker** (uses `Dockerfile` in repo root)
3. Health check path: `/api/dashboard/stats`
4. Set `ENVIRONMENT=dev` in Render environment
5. Auto-deploys on push to `main`

> **Note:** `render.yaml` rootDir must be updated from `pam-migration-control-center/` to `pam/control-center/` before the next monorepo push. See `sync-repos.sh` note in MAVERICK_CONTEXT.md.

---

## Dual-Repo Push

This project lives in two repos. Always push both:

```bash
# From /home/maverick/projects/iOPEX/
./sync-repos.sh push "your commit message"
```

Or manually:

```bash
# Public repo
cd /home/maverick/projects/iOPEX/pam/control-center
git add . && git commit -m "..." && git push

# Private repo (as subdirectory)
cd /home/maverick/projects/iOPEX
git add pam/control-center/ && git commit -m "..." && git push
```

> **Warning:** `sync-repos.sh` still references the old path `pam-migration-control-center/`. Update before use.

---

## Security Notes

- `PAM_MCP_ENVIRONMENT=dev` bypasses the Key Vault credential startup gate. Never set this in a live engagement environment.
- MCP servers bind to `0.0.0.0` on ports 8100/8101 with plain HTTP. In a client Azure environment, place behind a reverse proxy with TLS or restrict with NSG rules to orchestrator-only source IPs.
- Gate approval (`POST /api/gates/{id}/approve`) has no authentication in the current build. This is a P0 blocker before live engagement. Set `DASHBOARD_SECRET_KEY` and add middleware.
- Never commit `.env`, `config.json`, or any file matching `*.pem`, `*.key` to either repo.
- ML models (`*.pkl`) should be loaded from a mounted volume, not committed to the public repo.

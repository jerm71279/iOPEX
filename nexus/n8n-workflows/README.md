# nexus-core n8n Workflows

9 automation workflows for the iOPEX ecosystem. Import via n8n UI (Settings → Import Workflow).

n8n runs on `http://localhost:5678` — start with `docker compose up -d n8n` in `digital-expert/`.

---

## One-time Setup in n8n UI

1. **Credentials** — Settings → Credentials → Add:
   - `Nexus Telegram Bot` — Telegram Bot API, token = `TELEGRAM_BOT_TOKEN_IOPEX`
   - `GitHub jerm71279` — GitHub API, Personal Access Token (repo scope)

2. **Variables** — Settings → Variables → Add:
   - `TELEGRAM_CHAT_ID` — your Telegram chat ID (send `/start` to the bot, check logs)
   - `FRONTDOOR_URL` — `https://your-frontdoor.onrender.com`

3. **SSH** — for workflows using `executeCommand`, n8n runs on the Docker host network.
   Commands execute via `host.docker.internal` or direct exec if n8n has host access.
   Set `network_mode: host` in docker-compose.yml for the n8n service if shell access is needed.

---

## Workflows

| # | File | Trigger | What It Does |
|---|------|---------|--------------|
| 01 | `01-morning-nexus-brief.json` | Weekdays 7:00 AM | Health check → nexus brief → Telegram |
| 02 | `02-weekly-pmo-directive.json` | Monday 8:00 AM | Auto-calc SHIFT week → PMO directive → Telegram |
| 03 | `03-friday-wave-readiness.json` | Friday 4:00 PM | Wave GO/NO-GO → Telegram |
| 04 | `04-terraform-drift-detection.json` | Daily 6:00 AM | drift-check.sh → alert on drift only |
| 05 | `05-knowledge-base-freshness.json` | Sunday 9:00 AM | Ingest age check → auto re-ingest if stale |
| 06 | `06-frontdoor-deploy-verify.json` | Render webhook | Wait 30s → health check → pass/fail Telegram |
| 07 | `07-github-pr-shift-gate.json` | GitHub PR webhook | SHIFT preflight → PR comment with agent results |
| 08 | `08-ci-failure-alert.json` | GitHub Actions webhook | CI failure → Telegram alert with commit info |
| 09 | `09-daily-doctor-health.json` | Daily 6:30 AM | nexus-core doctor → alert on failures only |
| 10 | `10-memory-freshness-audit.json` | Sunday 9:00 AM | Compare memory file timestamps vs last git commit → alert if stale |

---

## Webhook Setup (workflows 06, 07, 08)

For local dev, expose n8n via ngrok:
```bash
ngrok http 5678
# Copy the https URL → use as webhook base
```

For production (Azure VM), n8n runs behind a reverse proxy. Add to nginx config:
```nginx
location /webhook/ {
    proxy_pass http://127.0.0.1:5678;
}
```

### Render Deploy Hook (workflow 06)
Render dashboard → Service → Settings → Deploy Hooks → Add hook:
- Name: n8n FrontDoor verify
- URL: `https://<your-n8n-url>/webhook/frontdoor-deploy`

### GitHub Webhooks (workflows 07, 08)
Repo Settings → Webhooks → Add webhook:
- Payload URL: `https://<your-n8n-url>/webhook/github-pr` (or `github-ci`)
- Content type: `application/json`
- Events: Pull requests (07), Workflow runs (08)

---

## Scheduled Workflow Timeline

```
06:00 AM  — Terraform drift check (workflow 04)
06:30 AM  — nexus-core doctor (workflow 09)
07:00 AM  — Morning Nexus brief, weekdays (workflow 01)
08:00 AM  — PMO directive, Mondays only (workflow 02)
16:00 PM  — Wave readiness, Fridays only (workflow 03)
09:00 AM  — KB freshness, Sundays only (workflow 05)
09:00 AM  — Memory freshness audit, Sundays only (workflow 10)
```

---

## Regen This Table

When a new workflow is added, update the table above. The workflow files are the
source of truth — the `_meta` block in each JSON documents setup requirements.

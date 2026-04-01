# PAM Migration — Project Index

All iOPEX PAM migration projects live here.

---

## Projects

| Directory | Purpose | Stack | Repo |
|-----------|---------|-------|------|
| [`cyberark-migration/`](cyberark-migration/) | 15-agent AI orchestrator: CyberArk → Privilege Cloud (Option A) | Python 3.12 | Private (iOPEX) |
| [`secret-server-migration/`](secret-server-migration/) | 15-agent AI orchestrator: CyberArk → Secret Server (Option B) | Python 3.12 | Private (iOPEX) |
| [`migration-assistant/`](migration-assistant/) | Standalone CLI tools: scanning, discovery, wave classification | Python 3.12 | Private (iOPEX) |
| [`control-center/`](control-center/) | Real-time migration dashboard + PMO layer (SHIFT) | FastAPI + Vanilla JS + ML | [`jerm71279/pam-control-center`](https://github.com/jerm71279/pam-control-center) (public) |
| [`consulting-agent/`](consulting-agent/) | PAM assessment toolkit: Streamlit UI, PowerShell pipelines, 10-domain assessment | Python + Streamlit + PS | [`jerm71279/pam-consultant-agent`](https://github.com/jerm71279/pam-consultant-agent) (private) |
| [`common/`](common/) | Shared library — core modules, shared agents, shared scripts (symlinked) | Python 3.12 | Private (iOPEX) |

---

## Architecture

```
                    ┌─────────────────────────────────┐
                    │         pam/common/              │
                    │  core/  agents/  scripts/        │
                    │  (single source of truth)        │
                    └──────────┬──────────┬────────────┘
                               │ symlinks  │
              ┌────────────────┘          └──────────────────┐
              ▼                                              ▼
  ┌─────────────────────┐                    ┌──────────────────────────┐
  │  cyberark-migration │                    │  secret-server-migration  │
  │  Option A           │                    │  Option B                 │
  │  → Privilege Cloud  │                    │  → Delinea Secret Server  │
  │  core/cloud_client  │                    │  core/secret_server_client│
  │  (11 unique agents) │                    │  (11 unique agents)       │
  └─────────────────────┘                    └──────────────────────────┘

  ┌─────────────────────┐   symlinks   ┌─────────────────────────────┐
  │  migration-assistant│ ◄──────────► │  consulting-agent           │
  │  CLI tools          │   to common/ │  Streamlit UI + PowerShell  │
  │  wave-classifier    │   scripts/   │  pam_assessor, autodiscovery│
  └─────────────────────┘              └─────────────────────────────┘

  ┌─────────────────────┐
  │  control-center     │  (standalone — own .git, public repo)
  │  Dashboard + ML     │  Push: cd control-center && git push (public)
  │  FastAPI backend    │       cd ../.. && git add pam/control-center && git push (private)
  └─────────────────────┘
```

---

## Quick Start

```bash
# Option A — CyberArk → Privilege Cloud
cd pam/cyberark-migration
python3 cli.py preflight && python3 cli.py start my-migration-001

# Option B — CyberArk → Secret Server
cd pam/secret-server-migration
python3 cli.py preflight && python3 cli.py start my-migration-001

# Migration assistant scripts
cd pam/migration-assistant
python3 scripts/wave_classifier.py --accounts accounts.csv --output waves.csv

# Consulting assessment
cd pam/consulting-agent
streamlit run scripts/web_app.py --server.port 8501

# Dashboard (local)
cd pam/control-center/frontend && python3 -m http.server 8080
```

---

## Shared Code Policy

All changes to files in `pam/common/` automatically apply to both orchestrators via symlinks.
**Never edit the symlink targets directly in `cyberark-migration/` or `secret-server-migration/`** —
edit in `common/` only.

See [`common/README.md`](common/README.md) for the full shared file inventory.

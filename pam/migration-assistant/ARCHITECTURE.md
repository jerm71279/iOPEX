# PAM Migration Assistant — Architecture

## System Overview

Six standalone Python CLI scripts providing pre-migration discovery, analysis, and code generation for the CyberArk → KeeperPAM migration. Scripts are stateless and composable — each reads from files and writes to files, with no shared runtime state. Their outputs are the primary inputs to the 15-agent orchestrators (wave classification → Agent 04 ETL, NHI list → Agent 12, integration map → Agent 06) and the primary client deliverables (PAM wrapper, converted code, wave plan).

Reference documentation (`references/`) covers CyberArk→Secret Server API translation for historical context. KeeperPAM-specific docs need to be added before go-live.

---

## Component Map

```
pam/migration-assistant/
│
├── scripts/
│   ├── nhi_discovery.py        Identify NHIs from CyberArk audit CSV export
│   ├── ccp_code_scanner.py     Scan codebases for CCP/AAM API call patterns
│   ├── integration_mapper.py   Map all CyberArk integration points in a codebase
│   ├── wave_classifier.py      Classify accounts into 5 migration waves by risk
│   ├── code_converter.py       Convert CCP calls to target platform SDK (⚠ needs keeper target)
│   └── generate_wrapper.py     Generate PAM wrapper module (⚠ needs keeper target — go-live blocker)
│
├── references/
│   ├── api_mapping.md          CyberArk CCP → Secret Server REST API translation
│   ├── permission_matrix.md    22 CyberArk permissions → SS 4-role mapping (+ important correction)
│   └── nhi_discovery.md        NHI identification guide and classification patterns
│
├── assets/templates/
│   ├── python_secret_retrieval.py      KeeperPAM/SS credential retrieval template (Python)
│   ├── dotnet_secret_retrieval.cs      KeeperPAM/SS credential retrieval template (.NET)
│   ├── powershell_secret_retrieval.ps1 KeeperPAM/SS credential retrieval template (PowerShell)
│   └── pam_wrapper_template.py         PAM wrapper base template
│
├── tests/
│   ├── test_scanner.py         Unit tests for ccp_code_scanner (patterns, risk levels, scan logic)
│   └── fixtures/               Sample CyberArk code in Python, .NET, PowerShell, YAML
│
├── requirements.txt            requests, pytest, responses, black, flake8, mypy
└── setup.py                    pip install -e . support
```

---

## Data Flow

```
PRE-MIGRATION PIPELINE (P1)

  CyberArk Audit Export (CSV)
    ↓
  nhi_discovery.py ──────────────────────────────→ nhis.csv
    │                                                  │
    │                                                  ↓
  Application Source Repos                    wave_classifier.py ──→ waves.csv
    ↓                                          (+ accounts.csv)        │
  ccp_code_scanner.py ──→ scanner_results.json                         │
    │                           │                                      │
    ↓                           ↓                                      ↓
  integration_mapper.py   code_converter.py                    → Agent 04 ETL
    ↓                        ↓                                  (wave gating)
  integrations.csv        converted/ code                         │
    │                                                             ↓
    ↓                     generate_wrapper.py ──→ pam_wrapper.py  │
  → Agent 06 Rewirer        (per language,                       │
  (integration repoint)      per platform)                       │
                              │                                  │
                              ↓                                  ↓
                          Client deliverable             → Agent 12 NHI Handler
                          (Wave 5 cutover kit)           (NHI classification)

REFERENCE DOCS (human-consumed, not automated)
  api_mapping.md        → Developer reference during code_converter / generate_wrapper review
  permission_matrix.md  → Agent 03 / human review reference for permission loss
  nhi_discovery.md      → Analyst reference for manual NHI identification
```

---

## Key Interfaces

| Interface | Type | Direction | Notes |
|-----------|------|-----------|-------|
| CyberArk audit export | CSV file | Inbound | `--audit-file audit.csv` to nhi_discovery |
| CyberArk accounts export | CSV file | Inbound | `--accounts accounts.csv` to wave_classifier |
| Application source repos | File system | Inbound | `--scan /path/to/code` to scanner + mapper |
| nhis.csv | CSV file | Internal | nhi_discovery → wave_classifier |
| scanner_results.json | JSON file | Internal | ccp_code_scanner → code_converter |
| waves.csv | CSV file | Outbound | wave_classifier → Agent 04 ETL wave gating |
| integrations.csv | CSV file | Outbound | integration_mapper → Agent 06 Rewirer |
| converted/ | File system | Outbound | code_converter → developer review → deployment |
| pam_wrapper.py | Python module | Outbound | generate_wrapper → Wave 5 app teams |
| pytest test suite | CLI | Internal | `pytest tests/ -v` — CI/CD gate |

---

## Deployment Topology

```
EXECUTION ENVIRONMENT
  Migration workstation (same host as orchestrators, or separate)
  Python 3.12+
  pip install -e .  or  pip install -r requirements.txt
  No server, no Docker, no build step — pure CLI

INPUT DATA SOURCES
  CyberArk audit export:   exported from PVWA Reports module (CSV)
  Accounts export:         exported from PVWA Accounts list (CSV)
  Application source:      git clone of all application repos to a local path

OUTPUT DESTINATIONS
  waves.csv, nhis.csv:     copied to orchestrator input dir (fed to Agents 04, 12)
  integrations.csv:        copied to orchestrator input dir (fed to Agent 06)
  converted/ + pam_wrapper: delivered to client application teams (Wave 5 cutover kit)

CI/CD (for the scripts themselves)
  pytest tests/ -v  run in GitHub Actions on every push to main
  Coverage target: >80% on scanner patterns (highest risk of false negatives)
```

---

## Security Notes

- **No live API calls by default**: All scripts operate on exported files. No credentials required for discovery/analysis phase.
- **Audit CSV sensitivity**: The CyberArk audit export contains account names, safe names, and access patterns — treat as confidential. Do not commit to any repo.
- **Generated code review**: `code_converter` and `generate_wrapper` output must be reviewed before deployment. Generated code could introduce auth vulnerabilities if KSM token handling is incorrect.
- **Permission matrix correction**: `references/permission_matrix.md` documents an important nuance — Secret Server has 200+ granular system-level permissions. The "22→4" narrative only applies to folder-level permissions. Do not over-simplify in client communications.
- **Wave 5 is the blast radius**: Wave 5 accounts are NHIs with active CCP/AAM integrations. A premature Wave 5 migration without app cutover causes immediate production outages. The wave classifier gate criteria enforce app team sign-off before Wave 5.

---

## Decision Log

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Standalone scripts (not orchestrator agents) | CLI scripts | Discrete tasks that can be run independently, re-run with different inputs, and handed to non-orchestrator users |
| File-based I/O | CSV / JSON | Human-inspectable, version-controllable, feedable to orchestrators and spreadsheets |
| No external dependencies (core) | Only `requests` | Scripts must run on an air-gapped migration workstation; no cloud SDKs required for analysis phase |
| Wave 5 = NHI + CCP (CRITICAL) | Separate from Wave 4 | CCP/AAM integrations require app team cutover coordination — merging with Wave 4 removes that gate |
| Reference docs cover SS (not KeeperPAM) | Historical | Reference docs were written before KeeperPAM was confirmed as live target. Add KeeperPAM refs before P1. |
| generate_wrapper is a go-live blocker | acknowledged | KeeperPAM KSM SDK wrapper must exist before Wave 5 cutover. Priority P0 for go-live prep. |

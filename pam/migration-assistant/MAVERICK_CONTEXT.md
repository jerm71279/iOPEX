# PAM Migration Assistant — Maverick Context

> Internal-only. Not for client distribution.
> Provides Jeremy / Claude Code with full project context for AI-assisted development.

---

## Project Identity

| Field | Value |
|-------|-------|
| Project | PAM Migration Assistant |
| Customer | iOPEX / live KeeperPAM engagement client |
| Status | active — scripts ready; KeeperPAM targets missing (go-live blocker) |
| Started | 2026-03-28 |
| Live Target | CyberArk PAS on-prem → **KeeperPAM (Keeper Security)** |
| Owner | JIT Technologies LLC |
| Primary Contact | Jeremy Smith (jerm712@icloud.com) |

---

## Why This Exists

The 15-agent orchestrators execute the migration, but they need pre-processed input data: which accounts go into which wave, which NHIs need special handling, which integrations need repointing. Doing this manually takes weeks and produces errors. The Migration Assistant automates the discovery and classification pipeline, reducing P1 preparation from 3–4 weeks of analyst work to 2–3 days of script execution and review.

The scripts also produce the primary client-facing deliverables for Wave 5: the PAM wrapper module that application teams drop into their codebases to replace CCP calls with KeeperPAM KSM SDK calls.

---

## What Has Been Built

- `nhi_discovery.py` — NHI identification from CyberArk audit CSV export; 7 NHI categories
- `ccp_code_scanner.py` — CCP/AAM pattern scanner across Python, Java, .NET, PowerShell, Bash; risk-leveled findings
- `integration_mapper.py` — CyberArk integration inventory; feeds Agent 06 Rewirer
- `wave_classifier.py` — 5-wave account classifier (Wave 1 Low → Wave 5 Critical NHI+CCP); gate criteria per wave
- `code_converter.py` — CCP→target platform code conversion (currently Secret Server only)
- `generate_wrapper.py` — PAM wrapper generator (currently Secret Server only)
- `references/api_mapping.md` — CyberArk CCP → Secret Server REST API translation
- `references/permission_matrix.md` — 22→4 permission mapping with important correction (SS has 200+ system-level permissions)
- `references/nhi_discovery.md` — NHI identification guide and classification patterns
- `assets/templates/` — credential retrieval templates (Python, .NET, PowerShell)
- `tests/test_scanner.py` — unit tests for ccp_code_scanner with fixtures

---

## What Is In Progress

### Go-Live Blockers (KeeperPAM targets)

| Priority | Item | Effort |
|----------|------|--------|
| **P0 — BLOCKER** | `generate_wrapper.py --platform keeper` (KSM SDK) | Medium |
| **P0 — BLOCKER** | `code_converter.py --platform keeper` | Medium |
| P1 | `references/keeper_api_mapping.md` — CyberArk CCP → KSM API translation | Small |
| P1 | `assets/templates/keeper_secret_retrieval.py` — KSM Python template | Small |
| P1 | `assets/templates/keeper_secret_retrieval.cs` — KSM .NET template | Small |
| P1 | `assets/templates/keeper_secret_retrieval.ps1` — KSM PowerShell template | Small |
| P2 | Expand test coverage to >80% on all scripts (currently only scanner tested) | Medium |
| P2 | `nhi_discovery.py` — add `--verbose` flag showing skip reasons | Small |

---

## Known Issues / Blockers

- **No KeeperPAM wrapper (BLOCKER):** `generate_wrapper.py` only generates Secret Server wrappers. Wave 5 cutover cannot proceed without a KeeperPAM KSM SDK wrapper. KSM Python SDK: `keeper_secrets_manager_core`. This is the highest-priority gap.
- **No KeeperPAM converter:** `code_converter.py` converts CCP to SS REST API calls. For KeeperPAM, conversion target is the KSM SDK, which has a completely different API surface (no REST — it's an SDK with local record caching).
- **NHI audit gap risk:** `nhi_discovery.py` is only as complete as the audit CSV provided. If the client filtered the export or excluded certain safes, NHIs will be silently missed and misclassified.
- **Wave classifier dependency:** wave_classifier must be run AFTER nhi_discovery. There is no enforcement of this — running in wrong order produces silently wrong waves.
- **Permission matrix correction:** `permission_matrix.md` notes that "22→4" only applies at the folder level. SS has 200+ system-level permissions. Do not present the 4-role model as the complete picture to a compliance-conscious client.
- **Tests coverage gap:** Only `ccp_code_scanner.py` has unit tests. `nhi_discovery`, `wave_classifier`, `integration_mapper`, `code_converter`, `generate_wrapper` have no test coverage.

---

## Key Decisions Made

- **Scripts not agents:** These are CLI scripts, not orchestrator agents. They run once per engagement during P1 preparation, not continuously. Keeping them simple and file-based means they work on air-gapped workstations.
- **Wave 5 is separated from Wave 4:** NHIs with active CCP integrations get their own wave because they require app team cutover coordination. Merging them with Wave 4 removes that gate.
- **KeeperPAM is the live target (confirmed 2026-03-28):** All new wrapper and converter work should target KSM SDK, not Secret Server. Reference docs covering SS are retained for historical/comparison use only.
- **generate_wrapper is a client deliverable:** The wrapper module is what application teams actually receive and deploy. It must be production-quality, documented, and tested — not just a code template.

---

## Client Context

The Migration Assistant scripts are run by iOPEX delivery engineers during P1. The outputs are reviewed jointly with the client:
- `waves.csv` — client signs off on wave assignments before P4
- `integrations.csv` — shared with client app teams to scope Wave 5 work
- `pam_wrapper.py` (or keeper equivalent) — delivered to client app teams for Wave 5 integration cutover

The scripts themselves are not shared with clients. The outputs are client deliverables.

---

## IP Notes

All code in this project is the exclusive property of JIT Technologies LLC.
The client receives the output files (wave plans, integration inventory, wrapper module),
not the scripts that generate them.

White label rights require a separate White Label License Agreement.

---

## Useful Commands

```bash
# Install
pip install -e .

# Full pre-migration pipeline (run in order)
python3 scripts/nhi_discovery.py --audit-file audit.csv --output nhis.csv
python3 scripts/ccp_code_scanner.py /path/to/app/source --output scanner_results.json
python3 scripts/integration_mapper.py --scan /path/to/app/source --output integrations.csv
python3 scripts/wave_classifier.py --accounts accounts.csv --nhis nhis.csv --output waves.csv

# Apply manual wave overrides
python3 scripts/wave_classifier.py --accounts accounts.csv --nhis nhis.csv \
  --overrides overrides.csv --output waves.csv

# Generate wave summary report
python3 scripts/wave_classifier.py --classified waves.csv --summary

# Convert CCP code to target platform (⚠ keeper target not yet available)
python3 scripts/code_converter.py scanner_results.json --language python --output converted/
python3 scripts/code_converter.py scanner_results.json --language csharp --output converted/
python3 scripts/code_converter.py scanner_results.json --language powershell --output converted/

# Generate PAM wrapper (⚠ keeper target not yet available — go-live blocker)
python3 scripts/generate_wrapper.py --language python --output pam_wrapper.py
# TODO: python3 scripts/generate_wrapper.py --platform keeper --language python --output keeper_wrapper.py

# Run tests
python3 -m pytest tests/ -v
python3 -m pytest tests/ -v --cov=scripts --cov-report=term-missing
```

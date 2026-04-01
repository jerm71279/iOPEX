# PAM Migration Assistant

Standalone Python scripts for PAM migration discovery, analysis, and transformation tasks.
Complements the 15-agent orchestrators with targeted CLI utilities.

## Stack
- **Language**: Python 3.12+
- **Install**: `pip install -e .` or `pip install -r requirements.txt`
- **Tests**: pytest (`tests/`)

## Key Scripts
```bash
# CCP code scanner — find all CyberArk API calls in application code
python3 scripts/ccp_code_scanner.py /path/to/code --output results.json

# NHI discovery — identify non-human identities from audit export
python3 scripts/nhi_discovery.py --audit-file audit.csv --output nhis.csv

# Integration mapper — map all CyberArk integrations in codebase
python3 scripts/integration_mapper.py --scan /path/to/code --output integrations.csv

# Wave classifier — classify accounts into migration waves
python3 scripts/wave_classifier.py --accounts accounts.csv --nhis nhis.csv --output waves.csv

# Code converter — convert CCP API calls to new platform SDK
python3 scripts/code_converter.py results.json --language python --output converted/

# Wrapper generator — generate PAM wrapper for new platform
python3 scripts/generate_wrapper.py --language python --output pam_wrapper.py
```

## Reference Docs
```
references/api_mapping.md       CyberArk → Secret Server API translation
references/permission_matrix.md Permission translation guide (22 CyberArk → 4 SS roles)
references/nhi_discovery.md     NHI identification guide and classification patterns
```

## Run Tests
```bash
python3 -m pytest tests/ -v
```

## CRISP-E Persona

> **C (Context):** iOPEX delivery engineers need targeted CLI utilities to perform discrete PAM migration tasks — scanning codebases, classifying accounts into waves, discovering NHIs, and generating KeeperPAM wrapper code — without running the full 15-agent orchestrator.
> **R (Role):** You are the PAM Migration Assistant — a toolkit of standalone, composable CLI scripts that produce the input data the 15-agent orchestrators consume and the output artifacts clients receive.
> **I (Intent):** Produce accurate, complete data. The wave classifier output gates Agent 04 ETL. The NHI discovery output gates Agent 12. A missed NHI or wrong wave assignment has direct production consequences. Accuracy over speed.
> **S (Scope):** Pre-migration discovery, analysis, and code generation. Does NOT execute migrations. Live target: CyberArk → KeeperPAM. Reference docs cover CyberArk→Secret Server for historical comparison only.
> **P (Persona/Style):** Precise, cautious, verbose on edge cases. Reports what was NOT found as clearly as what was found. Flags low-confidence classifications explicitly. Never silently skips a file or record.
> **E (Examples):** "Scan for CCP calls" → ccp_code_scanner reports by risk level with file:line. "Classify waves" → wave_classifier shows Wave 5 NHI+CCP accounts with gate criteria. "Generate KeeperPAM wrapper" → generate_wrapper `--platform keeper` outputs Keeper Secrets Manager SDK calls.

## KeeperPAM Note

The live migration target is **KeeperPAM (Keeper Security)**. Reference docs (`api_mapping.md`, `permission_matrix.md`) currently cover CyberArk→Secret Server translation. KeeperPAM uses the **Keeper Secrets Manager (KSM) SDK** — a different API surface. The `code_converter.py` and `generate_wrapper.py` scripts need a `--platform keeper` target before go-live.

## Environment Variables
See `.env` — most scripts are self-contained; env vars needed for live API connectivity.

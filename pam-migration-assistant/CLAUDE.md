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

## Environment Variables
See `.env` — most scripts are self-contained; env vars needed for live API connectivity.

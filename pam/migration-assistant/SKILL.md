---
name: pam-migration-assistant
description: "CyberArk to Delinea Secret Server PAM migration toolkit. Use when: (1) Scanning codebases for CyberArk CCP/AAM API dependencies, (2) Converting CyberArk API calls to Secret Server API calls, (3) Generating migration code templates in Python/PowerShell/.NET, (4) Mapping CyberArk Safes/Platforms/Permissions to Secret Server equivalents, (5) Creating NHI (Non-Human Identity) discovery scripts, (6) Building application credential cutover plans, (7) Any CyberArk-to-Secret-Server or CyberArk-to-Delinea migration task"
---

# PAM Migration Assistant

Toolkit for migrating from CyberArk PAS to Delinea Secret Server, with focus on application credential (CCP/AAM) conversion.

## Quick Start

### 1. Scan for CyberArk Dependencies
Run the code scanner to find all CyberArk API usage in a codebase:
```bash
python scripts/ccp_code_scanner.py /path/to/codebase --output scan_results.json
```

### 2. Generate Conversion Code
For each detected pattern, generate Secret Server equivalent:
```bash
python scripts/code_converter.py scan_results.json --language python --output converted/
```

### 3. Create Wrapper Library
Generate an abstraction layer for gradual migration:
```bash
python scripts/generate_wrapper.py --language python --output pam_wrapper.py
```

## Core Tools

### Code Scanner (`scripts/ccp_code_scanner.py`)
Scans directories for CyberArk CCP/AAM patterns across multiple languages.

**Detected Patterns:**
- REST API calls (`AIMWebService`, `/api/Accounts`)
- SDK imports (`CyberArk.AIM`, `com.cyberark`, `PasswordSDK`)
- Configuration references (`AppID`, `Safe`, `Object`)
- Connection strings with CyberArk parameters

**Output:** JSON report with file locations, pattern types, risk levels, and migration actions.

### Code Converter (`scripts/code_converter.py`)
Generates Secret Server equivalent code from detected CyberArk patterns.

**Supported Languages:** Python, PowerShell, C#/.NET, Java, Bash

**Features:**
- Converts CCP REST calls to Secret Server REST API
- Maps SDK calls to Thycotic.SecretServer equivalents
- Generates OAuth2 token handling code
- Preserves error handling patterns

### Wrapper Generator (`scripts/generate_wrapper.py`)
Creates abstraction layer that works with both systems during parallel running.

**Benefits:**
- Application code calls wrapper (doesn't change)
- Wrapper implementation switches between CyberArk and Secret Server
- Enables gradual cutover per-application

## API Mapping Reference

See `references/api_mapping.md` for complete CyberArk → Secret Server API translation:
- REST endpoints
- Authentication differences
- Response format changes
- Error code mapping

## Permission Translation

See `references/permission_matrix.md` for:
- CyberArk Safe permissions → Secret Server roles
- What granularity is lost
- Workarounds for specific permission needs

## NHI Discovery

See `references/nhi_discovery.md` for:
- Identifying non-human identities from CyberArk audit logs
- Classifying accounts by integration type
- Risk assessment framework

## Code Templates

Pre-built templates in `assets/templates/`:
- `python_secret_retrieval.py` - Python Secret Server client
- `powershell_secret_retrieval.ps1` - PowerShell Secret Server client
- `dotnet_secret_retrieval.cs` - C# Secret Server client
- `pam_wrapper_template.py` - Abstraction layer template

## Workflow

```
1. SCAN     → Find all CyberArk dependencies
2. ANALYZE  → Classify by risk and complexity
3. GENERATE → Create Secret Server equivalent code
4. WRAP     → Build abstraction layer (optional)
5. TEST     → Validate in non-production
6. CUTOVER  → Deploy during maintenance window
```

## Best Practices

### For Application Teams
- Use wrapper pattern to minimize code changes
- Test credential retrieval in non-prod first
- Coordinate maintenance window with PAM team
- Have rollback plan (keep CyberArk code available)

### For PAM Engineers
- Run scanner before migration planning
- Prioritize by risk level (HIGH first)
- Track all CCP/AAM applications in inventory
- Keep CyberArk running until all apps cutover

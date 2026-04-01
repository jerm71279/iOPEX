# PAM Migration Assistant — Agent Roster

## Overview

6 standalone CLI script agents, each performing a discrete pre-migration or analysis task. Scripts are composable — the output of one feeds the input of the next. Together they produce the data sets that the 15-agent orchestrators consume and the deliverables that clients receive.

**Execution order for a full pre-migration run:**
`nhi_discovery` → `ccp_code_scanner` → `integration_mapper` → `wave_classifier` → `code_converter` → `generate_wrapper`

**Live target:** CyberArk → **KeeperPAM**. Reference docs cover CyberArk→Secret Server for comparison. `code_converter` and `generate_wrapper` need `--platform keeper` support before go-live.

**Red Team Risk (Phase 7.5):** The #1 risk is a silent miss in `nhi_discovery`. If NHIs are not in the audit CSV export (filtered, excluded, or from a secondary system), they will be classified as human accounts in `wave_classifier`, placed in Wave 1–3, and migrated without app team coordination. The result is a production outage when the application tries to retrieve a secret that no longer exists at the old CyberArk address.

---

## Agents

| # | Agent | Alias | Role | Failure Mode | Remediation Script |
|---|-------|-------|------|--------------|--------------------|
| 1 | scripts/nhi_discovery.py | Discoverer | Identify non-human identities from CyberArk audit CSV export | Audit export is filtered or incomplete — NHIs from secondary vaults or recent additions are missed silently | Cross-reference against Agent 01 (orchestrator) discovery output; run with `--verbose` to see skip reasons |
| 2 | scripts/ccp_code_scanner.py | Scanner | Scan codebase for CyberArk CCP/AAM API call patterns by risk level | Misses custom CCP wrappers or obfuscated strings; no false-negative reporting — 0 results ≠ clean | Run `--strict` mode; manually grep for `AppID`, `AIMWebService`, `GetPassword` in build artifacts |
| 3 | scripts/integration_mapper.py | Mapper | Map all CyberArk integration points in a codebase; produce integration inventory | Same blind spots as scanner; also misses compiled binaries and config files outside scan path | Expand `--scan` path; add compiled output dirs; cross-reference with Agent 09 dependency mapper output |
| 4 | scripts/wave_classifier.py | Classifier | Classify accounts into 5 migration waves by risk, type, and NHI status | **CRITICAL**: NHIs missing from nhis.csv get classified as Wave 1–3 — migrated without app team coordination | Always validate wave_classifier input: `nhi_count` in nhis.csv must match orchestrator Agent 12 NHI count |
| 5 | scripts/code_converter.py | Converter | Convert CCP API call patterns to target platform SDK (KeeperPAM/SS) | Generates syntactically valid code that has runtime errors — token refresh, field names, error handling not validated | Generated code must be reviewed by a developer; add `--dry-run` flag to show diff without writing files |
| 6 | scripts/generate_wrapper.py | Generator | Generate PAM wrapper module for target platform SDK | **GAP**: No `--platform keeper` option — currently generates Secret Server wrapper only; KeeperPAM go-live blocked | Add KeeperPAM/KSM SDK target: `generate_wrapper.py --platform keeper --language python` |

---

## Agent Details

### Agent 1 — Discoverer (NHI Discovery)
**File:** `scripts/nhi_discovery.py`
**Input:** CyberArk audit log export (CSV) — `--audit-file audit.csv`
**Output:** NHI candidate list (CSV) — `--output nhis.csv`

Analyzes CyberArk audit logs to identify accounts accessed by non-human processes: service account patterns, application IDs, scheduled task signatures, API key patterns. Classifies by NHI category (service account, CCP app, scheduled task, DB connection, API key, DevOps credential, machine identity).

**Production checklist:**
- [ ] Export audit logs for full vault scope — not just top-level safes
- [ ] Include audit logs from secondary vaults and agent systems
- [ ] Cross-reference output count against Agent 12 (orchestrator) NHI classification count
- [ ] Flag any `confidence: low` NHIs for manual review before wave classification

**Wave dependency:** `nhis.csv` is required input to `wave_classifier.py`. An incomplete NHI list directly causes wave misclassification.

### Agent 2 — Scanner (CCP Code Scanner)
**File:** `scripts/ccp_code_scanner.py`
**Input:** Codebase directory path
**Output:** JSON report of CCP/AAM API call findings by file, line, risk level

Scans source files (Python, Java, .NET, PowerShell, Bash) for CyberArk CCP/AAM API patterns. Groups findings by risk level (HIGH/MEDIUM/LOW). Each finding includes: file, line number, pattern matched, risk level, migration action required.

**Pattern coverage:** `AIMWebService`, `AppID`, `GetPassword`, `CyberArk.AIM`, CCP URL patterns, SDK imports.
**Does NOT scan:** Compiled binaries, encrypted configs, non-standard wrapper libraries.

**Production checklist:**
- [ ] Run against all application source repos, not just the primary codebase
- [ ] Scan build artifact directories for embedded configs
- [ ] Manually search for custom CCP wrapper class names that aren't in the pattern list
- [ ] Zero results should trigger a manual audit, not be accepted at face value

### Agent 3 — Mapper (Integration Mapper)
**File:** `scripts/integration_mapper.py`
**Input:** Codebase directory path
**Output:** CSV integration inventory (integration type, file, count, migration complexity)

Produces a structured inventory of all CyberArk integration points for the migration plan. Groups by integration type (CCP/AAM, PSM, CPM, PVWA API, custom SDK). Feeds Agent 06 (Integration Rewirer) in the orchestrator.

**Production checklist:**
- [ ] Run against all repos, not just the migration target application
- [ ] Output should be reviewed against the SOW integration list — discrepancies need explanation
- [ ] High-complexity integrations should be flagged for a separate integration workstream

### Agent 4 — Classifier (Wave Classifier)
**File:** `scripts/wave_classifier.py`
**Input:** Accounts CSV export + NHI candidates CSV
**Output:** Classified accounts CSV with wave assignment + gate criteria

Wave definitions:
- **Wave 1:** Test/Dev accounts (LOW risk) — validates process
- **Wave 2:** Standard user accounts (MEDIUM risk) — after Wave 1 validated
- **Wave 3:** Infrastructure accounts (MEDIUM-HIGH) — change window required
- **Wave 4:** NHIs without CCP/AAM (HIGH) — coordinated with app teams
- **Wave 5:** NHIs with CCP/AAM (CRITICAL) — requires app cutover

**Production checklist:**
- [ ] Validate: `nhi_discovery` output count matches Agent 12 (orchestrator) NHI count before running
- [ ] Review all Wave 5 accounts with app owners before P4
- [ ] Apply manual overrides (`--overrides overrides.csv`) for accounts that need wave adjustment
- [ ] Wave 5 gate criteria: all CCP/AAM integrations repointed to KeeperPAM KSM before migration

### Agent 5 — Converter (Code Converter)
**File:** `scripts/code_converter.py`
**Input:** Scanner results JSON + target language
**Output:** Converted source files in output directory

Converts CCP API call patterns to target platform SDK calls. Supports Python, Java, .NET (.cs), PowerShell.

**⚠ KeeperPAM gap:** Currently generates Secret Server REST API calls. For go-live, add KeeperPAM/KSM SDK conversion target.

**Production checklist:**
- [ ] Add `--platform keeper` target (KSM SDK: `keeper_secrets_manager_core`)
- [ ] All generated code must be reviewed by a developer before deployment
- [ ] Add `--dry-run` to preview without writing
- [ ] Run the test suite (`pytest tests/`) against converted code before delivery

### Agent 6 — Generator (Wrapper Generator)
**File:** `scripts/generate_wrapper.py`
**Input:** Target platform, language
**Output:** PAM wrapper module for the target platform

Generates a reusable PAM credential retrieval wrapper that application teams can drop into their codebases to replace direct CCP calls.

**⚠ KeeperPAM gap (BLOCKER for go-live):** Only generates Secret Server wrapper. KeeperPAM requires Keeper Secrets Manager (KSM) SDK wrapper. This is the primary client deliverable for Wave 5 integration cutover.

**Production checklist:**
- [ ] **Add `--platform keeper` using `keeper_secrets_manager_core` Python SDK**
- [ ] Include token caching and refresh logic in generated wrapper
- [ ] Add error handling for KSM connectivity failures (fallback to cached secret)
- [ ] Generate wrappers for all languages used by Wave 5 apps (Python, Java, .NET, PowerShell)
- [ ] Deliver wrapper to app teams with test fixtures before Wave 5 cutover

---

## Orchestration

Scripts are standalone — no shared state, no coordinator. Each produces a file that the next consumes. Recommended execution order:

```
1. nhi_discovery     → nhis.csv
2. ccp_code_scanner  → scanner_results.json
3. integration_mapper → integrations.csv
4. wave_classifier   → waves.csv          (requires nhis.csv from step 1)
5. code_converter    → converted/          (requires scanner_results.json from step 2)
6. generate_wrapper  → pam_wrapper.py      (per language, per platform)
```

Output files from steps 1–4 feed Agent 12, Agent 06, and Agent 04 of the orchestrators respectively.

---

## Status

| Agent | Status | Last Action |
|-------|--------|-------------|
| 1 Discoverer | ready | Pending audit CSV export from client |
| 2 Scanner | ready — tests passing | Run against client codebase in P1 |
| 3 Mapper | ready | Run against client codebase in P1 |
| 4 Classifier | ready | Requires Discoverer output first |
| 5 Converter | partial ⚠ | Missing `--platform keeper` target |
| 6 Generator | **blocked** ⚠ | Missing `--platform keeper` — go-live blocker |

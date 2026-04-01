# CyberArk Migration — Agent Roster

## Overview

15-agent AI orchestrator for CyberArk PAS on-prem → KeeperPAM migration. Agents are sequenced by phase via `coordinator.py`. Each agent extends `AgentBase`, returns `AgentResult`, and gates on prior agent output before proceeding. All actions are SHA-256 audit-logged.

**Red Team Risk (Phase 7.5):** The #1 systemic risk is the ETL vault freeze not being reversed after a pipeline failure. If Agent 04's watchdog fails and the process is killed, production accounts become inaccessible. The emergency unfreeze path is the primary mitigation — know it before running P4.

---

## Agents

| # | Agent | Alias | Role | Failure Mode | Remediation Script |
|---|-------|-------|------|--------------|--------------------|
| 01 | agent_01_discovery.py | Scout | Enumerate all safes, accounts, platforms via PVWA Applications API | Silent pagination failure on large vaults — inventory is incomplete with no error | Re-run with `--resume`; check `output/state/raw/` for last page token |
| 02 | agent_02_gap_analysis.py | Analyst | 10-domain gap analysis across 4 compliance frameworks | Misconfigured threshold marks critical gaps as acceptable — they slip to P2 | Review `output/reports/gap_analysis.json`; lower acceptance threshold in `agent_config.json` |
| 03 | agent_03_permissions.py | Mapper | Map all 22 safe permissions 1:1 via Safe Members API; flag 7 sensitive permissions | API rate limit causes partial mapping — some members silently get default permissions | Check report for `status: defaulted`; re-run agent 03 after rate limit window |
| 04 | agent_04_etl.py | Mover | FREEZE → EXPORT → TRANSFORM → SAFE CREATION → IMPORT → HEARTBEAT → UNFREEZE | **CRITICAL**: Vault stays frozen if watchdog fails or process is killed mid-pipeline | `python3 cli.py agent 04 --emergency-unfreeze`; watchdog fires at 120 min |
| 05 | agent_05_heartbeat.py | Validator | 10 post-migration validation checks on target KeeperPAM | False positive — account responds but CPM cannot rotate due to firewall block | Run `--deep-validate`; verify CPM network connectivity independently |
| 06 | agent_06_integration.py | Rewirer | CCP/AAM code scanning + repointing to KeeperPAM endpoints | Misses hardcoded PVWA URLs in compiled binaries or obfuscated scripts | Manual review of flagged files; extend pattern list in scanner config |
| 07 | agent_07_compliance.py | Auditor | PCI-DSS, NIST 800-53, HIPAA, SOX compliance evidence generation | Generates passing report from stale evidence — `generated_at` timestamp not checked | Force re-run with `--fresh`; validate report timestamp before submission |
| 08 | agent_08_runbook.py | Gatekeeper | Phase gate execution + human approval workflow | Approval timeout not enforced — runbook hangs indefinitely waiting for sign-off | Set `APPROVAL_TIMEOUT_MIN` in `agent_config.json`; configure Slack escalation |
| 09 | agent_09_dependency_mapper.py | Mapper | 6-scanner dependency detection (IIS, services, tasks, Jenkins, scripts, configs) | Misses dependencies on UNC paths / network shares not local to scanned host | Add network share paths to scanner config; review `output/reports/dependencies.json` |
| 10 | agent_10_staging.py | Tester | 10 staging assertions; hard-blocks production if any fail | Staging config drifts from production — staging passes, production fails | Run `--compare-configs` before promoting; keep staging config in sync |
| 11 | agent_11_source_adapter.py | Importer | 7 vendor source adapters (BeyondTrust, SS, HashiCorp, AWS, Azure, GCP) | Vendor API token expires mid-export on large vaults (>10K accounts) | Set `ADAPTER_BATCH_SIZE` smaller; implement proactive token refresh |
| 12 | agent_12_nhi_handler.py | Classifier | NHI classification via 3 signals (platform, name, safe pattern); weighted scoring | Low-confidence NHIs default to human account treatment — skip specialized migration path | Review `output/reports/nhi_classification.json` for `confidence: low`; manually reclassify |
| 13 | agent_13_platform_plugins.py | Porter | Export/import custom CyberArk platform plugins to KeeperPAM | Custom platform with non-standard CPM plugin fails import silently — missing in target | Check `output/reports/platform_import.json` for `status: failed`; manual plugin rebuild |
| 14 | agent_14_onboarding.py | Onboarder | 10-step service account onboarding pipeline during/after migration | Partial records if steps 5–9 fail — safe created but account not linked | Run `--cleanup-partial` to remove orphaned safes; re-run from failed step |
| 15 | agent_15_hybrid_fleet.py | Balancer | Hybrid fleet manager during parallel running (on-prem + KeeperPAM) | Split-brain: both CPM instances rotate same account simultaneously | Set `HYBRID_MODE=exclusive` in `agent_config.json`; enforce mutex lock |

---

## Agent Details

### Agent 01 — Scout (Discovery)
**Phase:** P1 | **File:** `agents/agent_01_discovery.py`
Enumerates all safes, accounts, platforms, and CCP/AAM application identities via PVWA REST API. Multi-signal NHI pre-classification feeds Agent 12. Raw inventory written to `output/state/raw/`.

### Agent 02 — Analyst (Gap Analysis)
**Phase:** P1 | **File:** `agents/agent_02_gap_analysis.py`
Scores readiness across 10 domains. Maps findings to PCI-DSS, NIST 800-53, HIPAA, SOX. Produces go/no-go recommendation for P2 advancement.

### Agent 03 — Mapper (Permission Mapping)
**Phase:** P1 + P3 | **File:** `agents/agent_03_permissions.py`
Maps all 22 CyberArk safe permissions 1:1 to KeeperPAM (no loss — same permission model). Flags 7 security-sensitive permissions for human review before P3.

### Agent 04 — Mover (ETL Orchestration)
**Phase:** P4 + P5 | **File:** `agents/agent_04_etl.py`
7-step ETL with real API calls. Watchdog timer auto-unfreezes at 120 min. Emergency unfreeze fires on any exception. Password retrieval via `POST /Accounts/{id}/Password/Retrieve`. Linked accounts via `POST /Accounts/{id}/LinkAccount`.

### Agent 05 — Validator (Heartbeat & Validation)
**Phase:** P4–P6 | **File:** `agents/agent_05_heartbeat.py`
10 post-migration checks: account access, CPM rotation, PSM session, safe membership, platform assignment, audit continuity, integration connectivity, NHI rotation, compliance posture, rollback readiness.

### Agent 06 — Rewirer (Integration Repointing)
**Phase:** P5 | **File:** `agents/agent_06_integration.py`
Scans codebases for CCP/AAM patterns. Generates KeeperPAM replacement code. Supports Python, Java, .NET, PowerShell, Bash.

### Agent 07 — Auditor (Compliance & Audit)
**Phase:** P5 + P7 | **File:** `agents/agent_07_compliance.py`
Generates compliance evidence for PCI-DSS, NIST 800-53, HIPAA, SOX. Validates SHA-256 audit chain continuity. Produces executive summary and control mapping.

### Agent 08 — Gatekeeper (Runbook)
**Phase:** All | **File:** `agents/agent_08_runbook.py`
Enforces phase gates. Collects human approvals via CLI (or Slack webhook). Logs approvals with timestamp and approver identity.

### Agent 09 — Mapper (Dependency Mapper)
**Phase:** P1 | **File:** `agents/agent_09_dependency_mapper.py`
6 scanners: IIS, Windows services, scheduled tasks, Jenkins, scripts, configs. Dependency graph gates ETL — unresolved dependencies block P4.

### Agent 10 — Tester (Staging Validation)
**Phase:** P2 | **File:** `agents/agent_10_staging.py`
10 assertions against staging KeeperPAM. Hard-blocks production on any failure. Supports rollback to on-prem baseline.

### Agent 11 — Importer (Source Adapter)
**Phase:** P1 | **File:** `agents/agent_11_source_adapter.py`
7 adapters: CyberArk, BeyondTrust, Secret Server, HashiCorp Vault, AWS Secrets Manager, Azure Key Vault, GCP Secret Manager. Normalizes all to CyberArk account schema.

### Agent 12 — Classifier (NHI Handler)
**Phase:** P1 | **File:** `agents/agent_12_nhi_handler.py`
7 NHI subtypes. Weighted 3-signal scoring (platform type, name pattern, safe pattern). Per-type migration strategy assigned on classification.

### Agent 13 — Porter (Platform Plugins)
**Phase:** P2 | **File:** `agents/agent_13_platform_plugins.py`
Export custom platforms from on-prem → validate → import to KeeperPAM. Flags non-standard CPM plugins requiring manual rebuild.

### Agent 14 — Onboarder (App Onboarding)
**Phase:** P3 + P5 | **File:** `agents/agent_14_onboarding.py`
10-step pipeline: safe → permissions → platform → account → CPM link → rotation → heartbeat → integration test → audit → notification.

### Agent 15 — Balancer (Hybrid Fleet)
**Phase:** P6 | **File:** `agents/agent_15_hybrid_fleet.py`
Manages accounts split across on-prem and KeeperPAM during parallel running. Routes CPM rotation to correct system. Tracks cutover readiness per account group.

---

## Orchestration

`coordinator.py` sequences agents per phase. Each `AgentResult` is validated before the next agent starts. SIGTERM/SIGINT handlers ensure safe shutdown with vault unfreeze.

State: `output/state/migration_state.json` — atomic writes, SHA-256 chain, crash recovery. Phase advancement: `python3 cli.py advance P1` (gate validation required).

---

## Status

| Agent | Status | Last Action |
|-------|--------|-------------|
| 01 Scout | ready | Pending P1 |
| 02 Analyst | ready | Pending P1 |
| 03 Mapper | ready | Pending P1 |
| 04 Mover | ready | Pending P4 |
| 05 Validator | ready | Pending P4 |
| 06 Rewirer | ready | Pending P5 |
| 07 Auditor | ready | Pending P5 |
| 08 Gatekeeper | active | All phases |
| 09 Mapper | ready | Pending P1 |
| 10 Tester | ready | Pending P2 |
| 11 Importer | ready | Pending P1 |
| 12 Classifier | ready | Pending P1 |
| 13 Porter | ready | Pending P2 |
| 14 Onboarder | ready | Pending P3 |
| 15 Balancer | ready | Pending P6 |

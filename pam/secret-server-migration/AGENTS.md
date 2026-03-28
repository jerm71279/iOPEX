# Secret Server Migration — Agent Roster

## Overview

15-agent AI orchestrator for CyberArk PAS on-prem → Delinea Secret Server migration. This is a cross-vendor, lossy migration — the permission model collapses from 22 to 4 roles, audit logs cannot transfer, and all integrations require full OAuth2 re-architecture. Every agent is aware of these constraints and documents compromises explicitly.

**Red Team Risk (Phase 7.5):** The #1 risk is unreviewed permission escalation. Agent 03's 22→4 collapse can silently grant MORE access than a member had (e.g., UnlockAccounts alone triggers "Edit" role, which also allows AddAccounts/Delete). If the loss report is not reviewed before P3, users arrive in Secret Server with elevated privileges.

---

## Agents

| # | Agent | Alias | Role | Failure Mode | Remediation Script |
|---|-------|-------|------|--------------|--------------------|
| 01 | agent_01_discovery.py | Scout | Enumerate safes, accounts, platforms via PVWA API | Silent pagination failure on large vaults — incomplete inventory | Re-run with `--resume`; verify count against PVWA UI |
| 02 | agent_02_gap_analysis.py | Analyst | 10-domain gap analysis + SS template readiness + permission model risk scoring | Marks custom platform gaps as low-risk — manual template creation is missed | Review `output/reports/gap_analysis.json`; all custom platforms need manual SS template before P2 |
| 03 | agent_03_permissions.py | Mapper | **LOSSY** 22→4 role mapping with escalation detection and per-member loss report | **CRITICAL**: Escalation not flagged if member has only one Edit-triggering permission — they get full Edit role | Run `--strict-escalation` flag; review all `role: Edit` assignments manually before P3 |
| 04 | agent_04_etl.py | Mover | FREEZE → EXPORT → TRANSFORM → FOLDER CREATION → IMPORT → HEARTBEAT → UNFREEZE | Vault stays frozen if watchdog fails or process is killed mid-pipeline | `python3 cli.py agent 04 --emergency-unfreeze`; watchdog fires at 120 min |
| 05 | agent_05_heartbeat.py | Validator | 10 post-migration checks including SS heartbeat API + RPC validation | RPC plugin not rebuilt for custom template — heartbeat passes ping but rotation fails silently | Check `output/reports/heartbeat.json` for `rpc_status: untested`; rebuild RPC plugin per template |
| 06 | agent_06_integration.py | Rewirer | CCP/AAM → SS REST API + OAuth2 full re-architecture | Partial repoint — old CCP calls replaced but OAuth2 token refresh logic not added | Review generated code for `token_refresh` pattern; SS tokens expire; must refresh proactively |
| 07 | agent_07_compliance.py | Auditor | PCI-DSS, NIST, HIPAA, SOX + SS-specific risks (audit discontinuity, permission collapse) | Audit discontinuity risk marked as mitigated if customer accepts risk in writing — but write-off not stored | Store signed risk acceptance in `output/reports/risk_acceptances/`; reference in compliance report |
| 08 | agent_08_runbook.py | Gatekeeper | Phase gate execution + human approval workflow | Approval timeout not enforced — runbook hangs indefinitely | Set `APPROVAL_TIMEOUT_MIN` in `agent_config.json`; configure escalation |
| 09 | agent_09_dependency_mapper.py | Mapper | 6-scanner dependency detection (IIS, services, tasks, Jenkins, scripts, configs) | Misses UNC path / network share dependencies | Add share paths to scanner config; manual review of dependency graph |
| 10 | agent_10_staging.py | Tester | 10 assertions against SS staging instance; hard-blocks production on failure | Staging SS instance not in sync with production SS config — passes staging, fails production | Keep staging config locked to production version; run `--compare-configs` before promoting |
| 11 | agent_11_source_adapter.py | Importer | 7 vendor source adapters normalized to CyberArk account schema | Vendor API token expiry mid-export on large vaults | Set smaller `ADAPTER_BATCH_SIZE`; implement proactive token refresh |
| 12 | agent_12_nhi_handler.py | Classifier | NHI classification via 3 signals; 7 subtypes; per-type migration strategy | Low-confidence NHIs treated as human accounts — skip NHI-specific migration path in SS | Review `confidence: low` entries; assign correct SS folder/template manually |
| 13 | agent_13_platform_plugins.py | Porter | CyberArk platform → SS Secret Template mapping; auto-create missing templates | Custom platform has no SS template equivalent — import fails silently, account not migrated | Check `output/reports/platform_import.json` for `status: no_template`; create template manually in SS |
| 14 | agent_14_onboarding.py | Onboarder | SS folders/templates/secrets onboarding pipeline for new service accounts | Partial pipeline if SS API rate-limited mid-run — folder created, secret not linked | Run `--cleanup-partial`; re-run from failed step with `--resume-step N` |
| 15 | agent_15_hybrid_fleet.py | Balancer | Hybrid fleet management during P6 parallel running (CyberArk on-prem + SS) | Split-brain: CyberArk CPM and SS RPC both attempt rotation simultaneously | Set `HYBRID_MODE=exclusive`; route by account group; validate mutex before P6 |

---

## Agent Details

### Agent 01 — Scout (Discovery)
**Phase:** P1 | **File:** `agents/agent_01_discovery.py`
Same discovery logic as Option A. Enumerates all safes, accounts, platforms, and CCP/AAM identities. Output feeds Agents 02, 03, 09, 11, 12 in P1.

### Agent 02 — Analyst (Gap Analysis)
**Phase:** P1 | **File:** `agents/agent_02_gap_analysis.py`
10-domain gap analysis plus two SS-specific checks: (1) Secret Template readiness for each CyberArk platform, (2) permission model risk score quantifying the 22→4 collapse impact. Flags custom platforms requiring manual SS template creation before P2.

### Agent 03 — Mapper (Permission Translation — LOSSY)
**Phase:** P1 + P3 | **File:** `agents/agent_03_permissions.py`
**This is the most critical agent in Option B.** Maps 22 CyberArk permissions to 4 SS roles (Owner, Edit, View, List). 9 permissions have no SS equivalent and are always lost. Escalation detection flags members who gain more access post-migration. Produces per-member loss report. **Must be reviewed by a human before P3 advances.**

Role mapping rules:
- **Owner**: requires ManageSafe AND ManageSafeMembers
- **Edit**: ANY of AddAccounts, UpdateAccountContent, UpdateAccountProperties, DeleteAccounts, RenameAccounts, UnlockAccounts
- **View**: ANY of UseAccounts, RetrieveAccounts
- **List**: ANY of ListAccounts, ViewSafeMembers, ViewAuditLog

### Agent 04 — Mover (ETL Orchestration)
**Phase:** P4 + P5 | **File:** `agents/agent_04_etl.py`
7-step ETL. Transform step: userName→username slug, address→machine slug, platformId→template lookup, platformAccountProperties→notes. Folder hierarchy: "Imported" root → per-safe child folders. Passwords retrieved via `POST /Accounts/{id}/Password/Retrieve` — failed retrievals skip the account (not imported with empty secret). Watchdog at 120 min.

### Agent 05 — Validator (Heartbeat & Validation)
**Phase:** P4–P6 | **File:** `agents/agent_05_heartbeat.py`
10 checks. SS-specific: SS heartbeat API (`POST /api/v1/secrets/{id}/heartbeat`), RPC plugin validation, audit log continuity check (CyberArk audit logs do NOT transfer — new SS audit trail starts at migration date).

### Agent 06 — Rewirer (Integration Repointing)
**Phase:** P5 | **File:** `agents/agent_06_integration.py`
Full re-architecture required. CCP/AAM credential retrieval → SS REST API + OAuth2. Generated code includes token acquisition, proactive refresh (60s before expiry), and secret field retrieval via SS template field names.

### Agent 07 — Auditor (Compliance)
**Phase:** P5 + P7 | **File:** `agents/agent_07_compliance.py`
Standard 4-framework evidence plus 3 SS-specific risks documented and tracked: (1) Audit Log Discontinuity (HIGH), (2) Permission Model Simplification (HIGH), (3) PSM Session Recording Loss (MEDIUM).

### Agent 08 — Gatekeeper (Runbook)
**Phase:** All | **File:** `agents/agent_08_runbook.py`
SS-specific phase gate names and approval checkpoints. P3 gate explicitly requires Agent 03 loss report sign-off.

### Agents 09–12
Same as Option A (dependency mapping, staging, source adapters, NHI classification). SS-aware where needed (staging targets SS instance, NHI strategies use SS folder/template structure).

### Agent 13 — Porter (Platform → Template)
**Phase:** P2 | **File:** `agents/agent_13_platform_plugins.py`
Maps CyberArk platforms to SS Secret Templates using the mapping table in `agent_config.json`. Auto-creates standard templates. Flags custom platforms with no mapping — these require manual SS template creation before ETL.

### Agent 14 — Onboarder (App Onboarding)
**Phase:** P3 + P5 | **File:** `agents/agent_14_onboarding.py`
SS-specific pipeline: folder creation → template selection → secret creation → RPC link → rotation test → heartbeat → integration test → audit → notification.

### Agent 15 — Balancer (Hybrid Fleet)
**Phase:** P6 | **File:** `agents/agent_15_hybrid_fleet.py`
Routes credential requests to CyberArk CPM (on-prem) or SS RPC (cloud) based on per-account cutover status. Tracks readiness for final cutover gate.

---

## Orchestration

`coordinator.py` sequences agents per phase. P3 has an explicit hard gate: Agent 03 loss report must be acknowledged before folder/template migration begins. SIGTERM/SIGINT trigger safe shutdown with vault unfreeze.

State: `output/state/migration_state.json` — atomic writes, SHA-256 chain, crash recovery.

---

## Status

| Agent | Status | Last Action |
|-------|--------|-------------|
| 01 Scout | ready | Pending P1 |
| 02 Analyst | ready | Pending P1 |
| 03 Mapper ⚠ | ready | Pending P1 — loss report review required before P3 |
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

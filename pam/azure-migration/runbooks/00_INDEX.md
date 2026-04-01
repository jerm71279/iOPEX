# CyberArk → KeeperPAM Migration Runbooks
## iOPEX SHIFT Migration System — Azure Deployment

---

## Runbook Index

| # | File | Scope | Duration |
|---|------|-------|----------|
| 00 | This file | Index & overview | — |
| 01 | [01_azure_deployment.md](01_azure_deployment.md) | Azure infra deploy + container build | Day 1 |
| 02 | [02_stakeholder_dashboard.md](02_stakeholder_dashboard.md) | Activate live dashboard for iOPEX + client visibility | 30 min |
| 03 | [P0_environment_setup.md](P0_environment_setup.md) | Secrets, config, connectivity tests | Day 1–2 |
| 04 | [P1_discovery.md](P1_discovery.md) | Full source discovery, gap analysis, permissions inventory | Weeks 1–4 |
| 05 | [P2_staging.md](P2_staging.md) | Platform validation, staging ETL run | Weeks 5–7 |
| 06 | [P3_safe_migration.md](P3_safe_migration.md) | Vault creation, permission apply, app onboarding setup | Weeks 8–10 |
| 07 | [P4_pilot.md](P4_pilot.md) | Pilot wave ETL + heartbeat validation | Weeks 11–12 |
| 08 | [P5_production.md](P5_production.md) | Production waves 1–5, integration repointing | Weeks 13–18 |
| 09 | [P6_parallel_running.md](P6_parallel_running.md) | Parallel running, fleet management, cutover | Weeks 19–24 |
| 10 | [P7_decommission.md](P7_decommission.md) | Source decommission, final audit, close-out | Weeks 25–27 |

---

## Agent Quick Reference

| Agent | Key | CLI | Phases |
|-------|-----|-----|--------|
| 01 DiscoveryAgent | `01-discovery` | `python3 cli.py agent 01-discovery` | P1 |
| 02 GapAnalysisAgent | `02-gap-analysis` | `python3 cli.py agent 02-gap-analysis` | P1 |
| 03 PermissionMappingAgent | `03-permissions` | `python3 cli.py agent 03-permissions` | P1, P3 |
| 04 ETLOrchestrationAgent | `04-etl` | `python3 cli.py agent 04-etl` | P4, P5 |
| 05 HeartbeatAgent | `05-heartbeat` | `python3 cli.py agent 05-heartbeat` | P4, P5, P6 |
| 06 IntegrationRepointingAgent | `06-integration` | `python3 cli.py agent 06-integration` | P5, P6 |
| 07 ComplianceAgent | `07-compliance` | `python3 cli.py agent 07-compliance` | P5, P6, P7 |
| 08 RunbookAgent | `08-runbook` | `python3 cli.py agent 08-runbook` | P0–P7 |
| 09 DependencyMapperAgent | `09-dependency-mapper` | `python3 cli.py agent 09-dependency-mapper` | P1 |
| 10 StagingValidationAgent | `10-staging` | `python3 cli.py agent 10-staging` | P2 |
| 11 SourceAdapterAgent | `11-source-adapter` | `python3 cli.py agent 11-source-adapter` | P0, P1 |
| 12 NHIClassificationAgent | `12-nhi-handler` | `python3 cli.py agent 12-nhi-handler` | P1 |
| 13 PlatformPluginAgent | `13-platform-plugins` | `python3 cli.py agent 13-platform-plugins` | P2, P4 |
| 14 OnboardingAgent | `14-onboarding` | `python3 cli.py agent 14-onboarding` | P3, P5 |
| 15 HybridFleetAgent | `15-hybrid-fleet` | `python3 cli.py agent 15-hybrid-fleet` | P5, P6 |

---

## Yellow Checkpoint Gates

Human approval required at each gate before the next phase begins.

| Gate | After | Approver | Block Condition |
|------|-------|----------|-----------------|
| YC-P1 | P1 complete | Migration Lead + Security | Gap analysis HIGH risks unresolved |
| YC-P2 | P2 complete | Migration Lead | Staging validation < 10/10 assertions |
| YC-P3 | P3 complete | Security + Compliance | Permission loss > 0% without sign-off |
| YC-P4 | P4 complete | Migration Lead + Client | Pilot heartbeat < 95% pass rate |
| YC-P5 | Each wave | Migration Lead | Heartbeat failure or integration miss |
| YC-P6 | P6 weekly | All stakeholders | Any stuck accounts or CPM failures |
| YC-P7 | P7 complete | Client + Compliance | Open audit items |

---

## Architecture Decision Points

Decisions that must be made before the project starts. Each is documented in full in the relevant runbook.

| ID | Decision | Options | Default | Runbook |
|----|----------|---------|---------|---------|
| DP-01 | How migration phases are triggered | A: Manual CLI / **B: OpenClaw → Azure (recommended)** / C: OpenClaw in Azure | B | [P0_environment_setup.md](P0_environment_setup.md) |

> **DP-01 — Operator Trigger Method:** The 15 SHIFT agents run in Azure Container App.
> Option B (recommended) keeps the OpenClaw AI PMO agent on the delivery engineer's PC
> and wires it to Azure via `az containerapp exec`. The engineer directs OpenClaw;
> OpenClaw runs the phase, monitors output, and reports back. Requires `az` CLI on the PC.
> Option C (cloud-hosted OpenClaw) is a future evolution — not needed for this engagement.

---

## Emergency Procedures

```bash
# Safe shutdown (SIGTERM — allows current agent to finish cleanly)
kill -TERM <coordinator_pid>

# Force stop (SIGINT)
kill -INT <coordinator_pid>

# Check current state
python3 cli.py status

# View audit log
tail -f output/logs/audit.jsonl

# View last 50 audit entries
tail -50 output/logs/audit.jsonl | python3 -m json.tool
```

---

## Glossary

| Term | Meaning |
|------|---------|
| Safe (CyberArk) | Vault (KeeperPAM) |
| Account (CyberArk) | Record (KeeperPAM) |
| Platform (CyberArk) | Record Type (KeeperPAM) |
| CPM | KeeperPAM rotation engine |
| NHI | Non-Human Identity (service account, API key, bot) |
| Wave | Batch of accounts migrated together by risk tier |
| Heartbeat | Post-migration password rotation verification |
| FREEZE | Disabling CPM rotation on source during ETL |
| UNFREEZE | Re-enabling CPM rotation (source or target) |

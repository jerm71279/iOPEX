# Terraform Justification: iOPEX PAM Migration Infrastructure

**Project:** CyberArk PAS On-Prem Migration (2,847 Privileged Accounts)
**Target Paths:** Option A -- Delinea Secret Server + StrongDM (80 weeks) | Option B -- CyberArk Privilege Cloud (50 weeks)
**Date:** March 2026
**Author:** iOPEX Migration Architecture Team

---

## 1. Executive Summary

The iOPEX PAM migration is a 50-to-80-week enterprise initiative responsible for migrating 2,847 privileged accounts from CyberArk PAS on-premises to one of two target platforms. A 15-agent AI orchestrator handles the imperative migration work -- discovery, ETL, permission mapping, heartbeat validation, compliance auditing, and integration repointing across eight migration phases.

The infrastructure underpinning this migration -- Azure VMs, networking, Key Vault, Docker hosts, DNS, monitoring, and PAM platform connectors -- requires the same Infrastructure-as-Code discipline and governance standards that we apply to the privileged assets being migrated. Manual provisioning of this infrastructure introduces drift, audit gaps, and reproducibility failures that directly undermine the compliance posture of the migration itself.

Terraform provides declarative, auditable, and repeatable infrastructure management for every environment the migration touches. All infrastructure changes flow through version-controlled pull requests with plan review before apply, producing a complete audit trail from initial provisioning through final decommission.

**Compliance alignment:**

- **PCI-DSS 4.0 Requirement 2** -- Configuration standards enforced as code across all environments
- **NIST 800-53 CM-2** -- Baseline configurations maintained as Terraform state, the single source of truth
- **SOX IT General Controls** -- Change management enforced through PR-based plan/apply workflows with approval gates

---

## 2. Phase-by-Phase Value Mapping

The following table maps each migration phase to the specific value Terraform delivers, contrasted with the manual alternative.

| Phase | Name | Duration | With Terraform | Without Terraform |
|-------|------|----------|----------------|-------------------|
| **P0** | Environment Setup | -- | Single `terraform apply` provisions Azure VM, VNet, Key Vault, Docker host, DNS records, and monitoring. Entire environment stands up in minutes from a single tfvars file. | Manual Azure Portal clicks across 6+ resource blades. Each environment provisioned differently. No reproducibility guarantee. |
| **P1** | Discovery | 3-4 weeks | No Terraform role. AI orchestrator agents (11, 01, 09, 12, 02, 03) discover and classify accounts, dependencies, and NHIs. | Same -- discovery is an imperative operation handled by the orchestrator. |
| **P2** | Infrastructure / Staging | 2-3 weeks | Staging environments mirror production via the same Terraform modules with different tfvars. Identical network topology, Key Vault policies, and Docker configuration. | Ad-hoc staging with configuration drift. Staging does not match production, causing false positives/negatives in validation. |
| **P3** | Safe / Folder Migration | 2-3 weeks | Production safe structures (Option B) or folder hierarchies (Option A) created declaratively via CyberArk or StrongDM providers. Infrastructure containers are version-controlled. | Manual creation of safes/folders through platform UI. No audit trail for container provisioning. |
| **P4** | Pilot Migration | 1-2 weeks | No Terraform role. ETL pipeline (Agent 04) runs FREEZE through UNFREEZE for pilot batch. | Same -- ETL is an imperative pipeline operation. |
| **P5** | Production Waves | 4-6 weeks | No Terraform role. ETL pipeline runs across Waves 1-5 with heartbeat validation. | Same -- wave execution is orchestrator-managed. |
| **P6** | Parallel Running | 4-6 weeks | `terraform plan` provides drift detection during the critical cutover window. Any unauthorized infrastructure changes are surfaced before they impact parallel running. | Manual configuration audits during the highest-risk phase. Drift goes undetected until it causes an incident. |
| **P7** | Decommission | 2-3 weeks | `terraform destroy -target` enables controlled, surgical teardown of migration infrastructure. Resources removed in dependency order with full audit trail. | Manual decommission with orphaned resources, dangling DNS records, and forgotten Key Vault entries. |

---

## 3. Clear Boundary -- Terraform vs AI Orchestrator

The migration architecture maintains a strict separation between declarative infrastructure (Terraform) and imperative operations (AI Orchestrator). Neither tool encroaches on the other's domain.

### Terraform Manages (Declarative Infrastructure)

- Azure VM provisioning, sizing, and OS configuration
- Virtual network topology, subnets, and NSG rules
- Azure Key Vault instances, access policies, and RBAC assignments
- Azure Monitor and Log Analytics workspace configuration
- Docker host setup and container runtime dependencies
- DNS zone and record management
- StrongDM gateway infrastructure and role definitions (Option A)
- Safe container structures -- empty shells without secrets (Option B)
- Folder hierarchy structures -- empty containers without secrets (Option A)
- Environment-specific configuration via tfvars (dev, staging, production)

### AI Orchestrator Manages (Imperative Operations)

- **ETL pipeline** -- FREEZE, EXPORT, TRANSFORM, CREATE, IMPORT, HEARTBEAT, UNFREEZE (Agent 04)
- **Password retrieval** and secret migration via `POST /Accounts/{id}/Password/Retrieve`
- **Permission mapping** -- 22-to-22 for Privilege Cloud; 22-to-4 LOSSY for Secret Server with escalation detection (Agent 03)
- **NHI classification** -- 7 subtypes with weighted multi-signal detection across platform, name pattern, and safe name signals (Agent 12)
- **Heartbeat validation** -- 10 post-migration checks per account (Agent 05)
- **Integration repointing** -- CCP/AAM code scanning and replacement patterns (Agent 06)
- **Compliance audit generation** -- PCI-DSS, NIST 800-53, HIPAA, SOX reporting (Agent 07)
- **Dependency mapping** -- IIS bindings, Windows services, scheduled tasks, Jenkins jobs, scripts, config files (Agent 09)
- **Linked account migration** via `POST /Accounts/{id}/LinkAccount`
- **Wave classification and batch sequencing** across production waves

### The Handoff

```
Terraform provisions infrastructure
        |
        v
terraform output -json > tf-outputs.json
        |
        v
tf-output-to-config.py parses outputs (endpoints, Key Vault URIs, credentials references)
        |
        v
Generates orchestrator's config.json with connection details
        |
        v
AI Orchestrator uses endpoints to execute migration phases
```

Terraform's responsibility ends at infrastructure provisioning and connection detail output. The orchestrator's responsibility begins at consuming those endpoints for migration execution. This boundary is enforced by the `tf-output-to-config.py` bridge script, which is the only coupling point between the two systems.

---

## 4. Cost Analysis

Monthly Azure resource estimates per environment. All prices are approximate based on East US 2 region pricing as of early 2026.

| Resource | Dev | Staging | Prod | Notes |
|----------|-----|---------|------|-------|
| VM (D2s v5 / D4s v5 / D8s v5) | $70 | $140 | $280 | 2/4/8 vCPU, 8/16/32 GB RAM |
| Managed Disk (128 GB P10) | $10 | $10 | $10 | Premium SSD for state files and logs |
| VPN Gateway (Basic) | -- | $140 | $140 | Required for on-prem CyberArk connectivity |
| Key Vault (Standard) | $1 | $1 | $1 | Per-vault cost; operations billed separately |
| Log Analytics (5 / 15 / 50 GB/month) | $5 | $15 | $50 | Ingestion at ~$2.30/GB |
| DNS Zone | $1 | $1 | $1 | Hosted zone + query charges |
| **Monthly Total** | **~$87** | **~$307** | **~$482** |  |

**Important notes:**

- PAM platform licensing costs (CyberArk Privilege Cloud, Delinea Secret Server, StrongDM) are separate line items negotiated directly with vendors. These are not Terraform-managed costs.
- Terraform CLI is free and open source (BSL-licensed). No Terraform Cloud or Terraform Enterprise subscription is required for this project.
- Dev environment can be paused or destroyed between active development periods to reduce cost.
- Staging environment should remain running during phases P2 through P6 (approximately 15-21 weeks).
- Production environment runs for the full migration duration.

---

## 5. Risk Mitigation

| Risk | Impact | Terraform Mitigation |
|------|--------|---------------------|
| **Environment drift** | Staging no longer matches production, causing validation failures and false confidence in pilot results. | `terraform plan` executed in CI/CD on every pull request detects all drift between desired state and actual infrastructure. Drift is surfaced before it causes migration failures. |
| **Inconsistent environments** | Dev, staging, and production have different network topologies, Key Vault policies, or VM configurations, leading to "works in staging, fails in production" scenarios. | Same Terraform modules with different tfvars files per environment. Module reuse guarantees structural consistency. |
| **Audit trail gaps** | Compliance auditors cannot determine who changed what infrastructure and when, creating findings during PCI-DSS or SOX audits. | Terraform state file history combined with `terraform plan` outputs stored in CI/CD logs provide a complete, timestamped record of every infrastructure change. |
| **Failed decommission** | Orphaned resources remain after migration completes -- running VMs, dangling DNS records, forgotten Key Vault entries accumulating cost and attack surface. | `terraform destroy` with targeted `-target` flags enables surgical teardown in dependency order. State file tracks every resource for complete cleanup. |
| **Secret sprawl** | Connection strings, API keys, and credentials stored in environment variables, config files, or CI/CD variables with no rotation or access control. | Azure Key Vault integration ensures all secrets are stored in a managed vault with RBAC access policies. No secrets in Terraform code, state, or environment variables. |
| **Configuration rollback** | A bad infrastructure change cannot be reversed quickly during a critical migration window. | `git revert` on the infrastructure commit followed by `terraform apply` restores the prior known-good state. Rollback is as fast as a CI/CD pipeline run. |
| **Unauthorized changes** | Infrastructure modified outside of the approved change process, bypassing review and approval gates. | PR-based workflow requires `terraform plan` output review and team approval before any `terraform apply` execution. Manual Portal changes are detected as drift on the next plan. |

---

## 6. Compliance Alignment

| Framework | Control | Control Description | Terraform Value |
|-----------|---------|--------------------|-----------------|
| PCI-DSS 4.0 | Req 1.2.5 | Network documentation must be accurate and up to date | NSG rules defined as code in Terraform modules -- version-controlled, peer-reviewed, and always current. Network documentation is the code itself. |
| PCI-DSS 4.0 | Req 2.2.1 | Configuration standards for system components | Terraform modules enforce configuration baselines across all environments. Deviation from the baseline requires a code change and PR approval. |
| PCI-DSS 4.0 | Req 6.5.1 | Changes are managed using change management processes | PR-based plan/apply workflow with mandatory approval gates. Every infrastructure change has a plan diff, reviewer approval, and apply log. |
| NIST 800-53 | CM-2 | Baseline Configuration | Terraform state file serves as the single source of truth for infrastructure baseline. Current state is queryable via `terraform show` at any time. |
| NIST 800-53 | CM-3 | Configuration Change Control | Git commit history combined with Terraform plan outputs produces a complete change record: who proposed the change, what the change does, who approved it, and when it was applied. |
| NIST 800-53 | AU-3 | Content of Audit Records | Terraform state file captures resource identity, configuration, timestamps, and provider metadata for every managed resource. CI/CD logs capture the operator identity. |
| SOX | ITGC -- Change Management | Changes to IT infrastructure follow documented procedures with approval | GitHub Actions workflows enforce PR review and approval before any `terraform apply` execution. No infrastructure changes bypass the review process. |
| SOX | ITGC -- Access Controls | Access to systems and data is appropriately restricted | Key Vault RBAC and managed identity assignments defined as code. No shared credentials. Access grants are peer-reviewed before application. |
| HIPAA | 164.312(a)(1) | Technical access control mechanisms | NSG rules restricting network access and Key Vault RBAC policies controlling secret access are both defined declaratively in Terraform. Access control is auditable and reproducible. |

---

## 7. Provider Maturity Assessment

Four Terraform providers are relevant to the PAM migration. Their maturity levels vary significantly and directly influence what can be managed declaratively versus what must remain in the AI orchestrator.

| Provider | Registry Path | Version | Status | Capabilities | Limitations |
|----------|--------------|---------|--------|-------------|-------------|
| `cyberark/cyberark` | Certified Partner | 0.2.0 | Early but officially supported by CyberArk | Safe creation and management, account provisioning, secret store configuration | No permission/policy management, no PSM session configuration, no CPM plugin management, limited resource type coverage |
| `cyberark/idsec` | Community | 0.1.x | Very early stage | Identity security platform integration | Immature provider with limited documentation, narrow resource coverage, not recommended for production use |
| `DelineaXPM/tss` | Community | 3.0.0 | Stable for its scope | Read-only secret access via data sources, secret value retrieval for use in other Terraform resources | **No write resources** -- data sources only. Cannot create folders, secrets, templates, or roles. Cannot modify Secret Server configuration. |
| `strongdm/sdm` | Certified Partner | 16.14.0 | Very mature, production-grade | Full CRUD operations: relay and gateway nodes, datasource and server resources, roles, composite roles, account grants, resource grants | Most capable PAM provider in the Terraform registry. Actively maintained with frequent releases. |

### Recommendations

**StrongDM provider (`strongdm/sdm`)** is production-ready for full Infrastructure-as-Code management. Gateway infrastructure, resource definitions, role hierarchies, and access grants should all be managed declaratively through Terraform. This provider has the maturity and resource coverage to serve as the primary IaC interface for StrongDM in Option A.

**CyberArk provider (`cyberark/cyberark`)** covers basic safe and account provisioning, which is sufficient for creating empty safe container structures during P3 in Option B. Permission assignments and policy configuration remain in the AI orchestrator (Agent 03) due to provider limitations.

**Delinea provider (`DelineaXPM/tss`)** is read-only. Use it exclusively for validation and drift detection -- confirming that folders and secrets created by the AI orchestrator match expected state. All folder creation, secret migration, and template management must remain in the AI orchestrator's ETL pipeline (Agent 04) because the provider cannot perform write operations.

**CyberArk Identity Security provider (`cyberark/idsec`)** is not recommended for production use at this time. Monitor for maturity improvements in future releases.

---

*This document should be reviewed and updated at the start of each migration phase to reflect provider version changes, cost adjustments, and lessons learned from prior phases.*

# iOPEX PAM Migration Infrastructure (Terraform)

Infrastructure-as-Code for the CyberArk PAS on-premises migration initiative (2,847 privileged accounts).
Covers Azure VMs, networking, Key Vault, Docker hosts, DNS, monitoring, and PAM platform connectors.

## Stack
- **IaC**: Terraform
- **Cloud**: Azure (primary)
- **Environments**: `dev`, `staging`, `prod` (separate `.tfvars` per env)

## Directory Structure
```
modules/
  azure-keyvault/           Key Vault provisioning + access policies
  azure-monitoring/         Prometheus + alerting resources
  azure-networking/         VNets, subnets, NSGs, peering
  azure-orchestrator-vm/    Migration orchestrator VM (15-agent host)
  cyberark-safes/           CyberArk safe provisioning via provider
  delinea-folders/          Secret Server folder structure (Option B)
  strongdm-infrastructure/  StrongDM gateway and enrollment (Option A alt path)
environments/
  dev.tfvars                Dev environment variable overrides
  staging.tfvars            Staging variable overrides
  prod.tfvars               Production variable overrides
compositions/               Environment-level root modules combining sub-modules
scripts/                    Helper scripts (plan, apply, destroy wrappers)
JUSTIFICATION.md            Architecture rationale and compliance alignment doc
```

## Run Commands
```bash
# Initialize
terraform init

# Plan (always review before apply)
terraform plan -var-file=environments/dev.tfvars

# Apply
terraform apply -var-file=environments/dev.tfvars

# Destroy (dev/staging only — NEVER run on prod without explicit approval)
terraform destroy -var-file=environments/dev.tfvars
```

## Compliance Alignment
- **PCI-DSS 4.0 Req 2**: Configuration standards enforced as code
- **NIST 800-53**: Audit trail via Terraform plan review → PR → apply pipeline
- All infra changes: version-controlled PR → plan review → apply (no manual changes)

## Environment Variables
See `.env` — Azure credentials for Terraform provider auth.

## Rules
- NEVER apply directly to prod without PR review
- NEVER run `terraform destroy` on prod
- `prod.tfvars` may contain non-sensitive config overrides — real secrets go in Azure Key Vault
- State backend should be Azure Blob Storage (remote state) — not local

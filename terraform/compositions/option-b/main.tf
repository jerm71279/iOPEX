## ─── Option B: CyberArk Privilege Cloud ──────────────────────────────────────
##
## Provisions PAM target infrastructure for the 50-week migration plan:
##   - Privilege Cloud safe containers (via cyberark provider)
##
## The AI orchestrator's Agent 04 ETL populates safes with accounts via the
## imperative 7-step pipeline. Terraform manages containers; orchestrator
## manages contents.
##
## Depends on shared composition for Azure VM, networking, Key Vault.

locals {
  tags = merge({
    project     = "pam-migration"
    environment = var.environment
    option      = "b"
    target      = "privilege-cloud"
    managed_by  = "terraform"
  }, var.extra_tags)
}

## ─── Shared State Reference ──────────────────────────────────────────────────

data "terraform_remote_state" "shared" {
  backend = "azurerm"
  config = {
    resource_group_name  = "rg-pam-tfstate"
    storage_account_name = "stpamtfstate"
    container_name       = "tfstate"
    key                  = var.shared_state_key
  }
}

## ─── CyberArk Privilege Cloud — Safe Structures ─────────────────────────────

module "cyberark_safes" {
  source = "../../modules/cyberark-safes"

  safes       = var.target_safes
  environment = var.environment
}

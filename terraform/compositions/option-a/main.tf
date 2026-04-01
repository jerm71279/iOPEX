## ─── Option A: Delinea Secret Server + StrongDM ─────────────────────────────
##
## Provisions PAM target infrastructure for the 80-week migration plan:
##   - Secret Server folder validation (read-back via tss provider)
##   - StrongDM gateway, resources, roles (full CRUD via sdm provider)
##
## Depends on shared composition for Azure VM, networking, Key Vault.

locals {
  tags = merge({
    project     = "pam-migration"
    environment = var.environment
    option      = "a"
    target      = "delinea-strongdm"
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

## ─── Delinea Secret Server — Validation ──────────────────────────────────────

module "delinea_folders" {
  source = "../../modules/delinea-folders"

  secret_server_url  = var.secret_server_url
  client_id          = var.ss_client_id
  client_secret      = var.ss_client_secret
  expected_secrets   = var.expected_secrets
  environment        = var.environment
}

## ─── StrongDM — Session Proxy Infrastructure ─────────────────────────────────

module "strongdm" {
  source = "../../modules/strongdm-infrastructure"

  gateway_name           = var.gateway_name
  gateway_listen_address = var.gateway_listen_address
  resources              = var.strongdm_resources
  roles                  = var.strongdm_roles
  role_grants            = var.strongdm_role_grants
  environment            = var.environment
  tags                   = local.tags
}

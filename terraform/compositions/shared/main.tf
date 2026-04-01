## ─── PAM Migration — Shared Infrastructure ──────────────────────────────────
##
## Foundation layer for BOTH migration options (A and B).
## Provisions: Azure VM, networking, Key Vault, monitoring.
## The AI orchestrator and Control Center run on this infrastructure.

locals {
  tags = merge({
    project     = "pam-migration"
    environment = var.environment
    option      = var.migration_option
    managed_by  = "terraform"
  }, var.extra_tags)

  kv_name = var.key_vault_name != "" ? var.key_vault_name : "kv-pam-${var.environment}"
}

## ─── Resource Group ───────────────────────────────────────────────────────────

resource "azurerm_resource_group" "pam_migration" {
  name     = "rg-pam-migration-${var.environment}"
  location = var.location
  tags     = local.tags
}

## ─── Networking ───────────────────────────────────────────────────────────────

module "networking" {
  source = "../../modules/azure-networking"

  resource_group_name        = azurerm_resource_group.pam_migration.name
  location                   = azurerm_resource_group.pam_migration.location
  vnet_address_space         = var.vnet_address_space
  subnet_orchestrator_prefix = var.subnet_orchestrator_prefix
  subnet_connectors_prefix   = var.subnet_connectors_prefix
  subnet_management_prefix   = var.subnet_management_prefix
  admin_cidr                 = var.admin_cidr
  on_prem_cidr               = var.on_prem_cidr
  on_prem_gateway_ip         = var.on_prem_gateway_ip
  enable_vpn_gateway         = var.enable_vpn_gateway
  tags                       = local.tags
}

## ─── Orchestrator VM ──────────────────────────────────────────────────────────

module "orchestrator_vm" {
  source = "../../modules/azure-orchestrator-vm"

  resource_group_name = azurerm_resource_group.pam_migration.name
  location            = azurerm_resource_group.pam_migration.location
  vm_name             = "pam-orchestrator-${var.environment}"
  vm_size             = var.vm_size
  admin_username      = var.admin_username
  ssh_public_key      = var.ssh_public_key
  subnet_id           = module.networking.subnet_orchestrator_id
  data_disk_size_gb   = var.data_disk_size_gb
  cloud_init_script   = var.cloud_init_script
  tags                = local.tags
}

## ─── Key Vault ────────────────────────────────────────────────────────────────

module "keyvault" {
  source = "../../modules/azure-keyvault"

  resource_group_name      = azurerm_resource_group.pam_migration.name
  location                 = azurerm_resource_group.pam_migration.location
  key_vault_name           = local.kv_name
  vm_identity_principal_id = module.orchestrator_vm.vm_identity_principal_id
  tags                     = local.tags
}

## ─── Monitoring ───────────────────────────────────────────────────────────────

module "monitoring" {
  source = "../../modules/azure-monitoring"

  resource_group_name = azurerm_resource_group.pam_migration.name
  location            = azurerm_resource_group.pam_migration.location
  workspace_name      = "la-pam-migration-${var.environment}"
  retention_days      = var.retention_days
  alert_email         = var.alert_email
  vm_id               = module.orchestrator_vm.vm_id
  tags                = local.tags
}

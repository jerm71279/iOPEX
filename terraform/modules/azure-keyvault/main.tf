###############################################################################
# Azure Key Vault Module — PAM Migration Control Center
# Phase P0: Key Vault with RBAC for storing PAM migration credentials
# VM managed identity gets Secrets User; deploying principal gets Secrets Officer
###############################################################################

# -----------------------------------------------------------------------------
# Current Client Config (for tenant_id and deployer principal)
# -----------------------------------------------------------------------------
data "azurerm_client_config" "current" {}

# -----------------------------------------------------------------------------
# Key Vault
# -----------------------------------------------------------------------------
resource "azurerm_key_vault" "pam" {
  name                = var.key_vault_name
  location            = var.location
  resource_group_name = var.resource_group_name
  tenant_id           = data.azurerm_client_config.current.tenant_id
  sku_name            = "standard"

  enable_rbac_authorization  = true
  purge_protection_enabled   = true
  soft_delete_retention_days = 90

  tags = var.tags
}

# -----------------------------------------------------------------------------
# RBAC — Orchestrator VM Managed Identity (read secrets at runtime)
# -----------------------------------------------------------------------------
resource "azurerm_role_assignment" "vm_secrets_user" {
  scope                = azurerm_key_vault.pam.id
  role_definition_name = "Key Vault Secrets User"
  principal_id         = var.vm_identity_principal_id
}

# -----------------------------------------------------------------------------
# RBAC — Deploying Principal (manage secrets during provisioning)
# -----------------------------------------------------------------------------
resource "azurerm_role_assignment" "admin_secrets_officer" {
  scope                = azurerm_key_vault.pam.id
  role_definition_name = "Key Vault Secrets Officer"
  principal_id         = data.azurerm_client_config.current.object_id
}

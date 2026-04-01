###############################################################################
# Azure Key Vault Module — Outputs
###############################################################################

output "key_vault_id" {
  value       = azurerm_key_vault.pam.id
  description = "Resource ID of the PAM migration Key Vault."
}

output "key_vault_uri" {
  value       = azurerm_key_vault.pam.vault_uri
  description = "URI of the Key Vault for SDK/CLI access."
}

output "key_vault_name" {
  value       = azurerm_key_vault.pam.name
  description = "Name of the Key Vault."
}

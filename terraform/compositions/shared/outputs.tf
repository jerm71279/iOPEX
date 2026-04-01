## ─── Resource Group ────────────────────────────────────────────────────────────

output "resource_group_name" {
  description = "Name of the PAM migration resource group"
  value       = azurerm_resource_group.pam_migration.name
}

output "resource_group_id" {
  description = "Resource group ID"
  value       = azurerm_resource_group.pam_migration.id
}

## ─── Networking ───────────────────────────────────────────────────────────────

output "vnet_id" {
  description = "Virtual network ID"
  value       = module.networking.vnet_id
}

output "subnet_orchestrator_id" {
  description = "Orchestrator subnet ID"
  value       = module.networking.subnet_orchestrator_id
}

output "subnet_connectors_id" {
  description = "PAM connectors subnet ID"
  value       = module.networking.subnet_connectors_id
}

## ─── Orchestrator VM ──────────────────────────────────────────────────────────

output "orchestrator_vm_id" {
  description = "Orchestrator VM resource ID"
  value       = module.orchestrator_vm.vm_id
}

output "orchestrator_private_ip" {
  description = "Orchestrator VM private IP"
  value       = module.orchestrator_vm.private_ip
}

output "orchestrator_public_ip" {
  description = "Orchestrator VM public IP"
  value       = module.orchestrator_vm.public_ip
}

output "orchestrator_identity_principal_id" {
  description = "Orchestrator VM managed identity principal ID"
  value       = module.orchestrator_vm.vm_identity_principal_id
}

## ─── Key Vault ────────────────────────────────────────────────────────────────

output "key_vault_id" {
  description = "Key Vault resource ID"
  value       = module.keyvault.key_vault_id
}

output "key_vault_uri" {
  description = "Key Vault URI for secret retrieval"
  value       = module.keyvault.key_vault_uri
}

## ─── Monitoring ───────────────────────────────────────────────────────────────

output "log_analytics_workspace_id" {
  description = "Log Analytics workspace ID"
  value       = module.monitoring.workspace_id
}

output "action_group_id" {
  description = "Monitor action group ID for alert routing"
  value       = module.monitoring.action_group_id
}

## ─── Environment Info ─────────────────────────────────────────────────────────

output "environment" {
  description = "Current environment name"
  value       = var.environment
}

output "migration_option" {
  description = "Selected migration option (a or b)"
  value       = var.migration_option
}

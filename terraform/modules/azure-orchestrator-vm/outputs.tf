###############################################################################
# Azure Orchestrator VM Module — Outputs
###############################################################################

output "vm_id" {
  value       = azurerm_linux_virtual_machine.orchestrator.id
  description = "Resource ID of the orchestrator virtual machine."
}

output "vm_name" {
  value       = azurerm_linux_virtual_machine.orchestrator.name
  description = "Name of the orchestrator virtual machine."
}

output "private_ip" {
  value       = azurerm_network_interface.orchestrator.private_ip_address
  description = "Private IP address of the orchestrator VM."
}

output "public_ip" {
  value       = azurerm_public_ip.orchestrator.ip_address
  description = "Public IP address of the orchestrator VM."
}

output "vm_identity_principal_id" {
  value       = azurerm_linux_virtual_machine.orchestrator.identity[0].principal_id
  description = "Principal ID of the system-assigned managed identity for RBAC assignments."
}

output "data_disk_id" {
  value       = azurerm_managed_disk.data.id
  description = "Resource ID of the attached data disk."
}

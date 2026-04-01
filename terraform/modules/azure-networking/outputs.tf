###############################################################################
# Azure Networking Module — Outputs
###############################################################################

output "vnet_id" {
  value       = azurerm_virtual_network.pam_migration.id
  description = "Resource ID of the PAM migration virtual network."
}

output "vnet_name" {
  value       = azurerm_virtual_network.pam_migration.name
  description = "Name of the PAM migration virtual network."
}

output "subnet_orchestrator_id" {
  value       = azurerm_subnet.orchestrator.id
  description = "Resource ID of the orchestrator subnet."
}

output "subnet_connectors_id" {
  value       = azurerm_subnet.connectors.id
  description = "Resource ID of the connectors subnet."
}

output "subnet_management_id" {
  value       = azurerm_subnet.management.id
  description = "Resource ID of the management subnet."
}

output "nsg_orchestrator_id" {
  value       = azurerm_network_security_group.orchestrator.id
  description = "Resource ID of the orchestrator network security group."
}

output "vpn_gateway_id" {
  value       = var.enable_vpn_gateway ? azurerm_virtual_network_gateway.vpn[0].id : ""
  description = "Resource ID of the VPN gateway. Empty string if VPN is not enabled."
}

###############################################################################
# Azure Monitoring Module — Outputs
###############################################################################

output "workspace_id" {
  value       = azurerm_log_analytics_workspace.pam.id
  description = "Resource ID of the Log Analytics workspace."
}

output "workspace_key" {
  value       = azurerm_log_analytics_workspace.pam.primary_shared_key
  description = "Primary shared key for the Log Analytics workspace. Use for agent enrollment."
  sensitive   = true
}

output "action_group_id" {
  value       = azurerm_monitor_action_group.pam_alerts.id
  description = "Resource ID of the PAM alerts action group."
}

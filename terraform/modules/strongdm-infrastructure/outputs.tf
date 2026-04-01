output "gateway_id" {
  description = "StrongDM gateway node ID"
  value       = sdm_node.gateway.id
}

output "gateway_token" {
  description = "Gateway authentication token (use to start the gateway process)"
  value       = sdm_node.gateway.gateway[0].token
  sensitive   = true
}

output "resource_ids" {
  description = "Map of resource name to StrongDM resource ID"
  value       = { for k, v in sdm_resource.targets : k => v.id }
}

output "role_ids" {
  description = "Map of role name to StrongDM role ID"
  value       = { for k, v in sdm_role.access_roles : k => v.id }
}

output "resource_count" {
  description = "Number of resources registered"
  value       = length(sdm_resource.targets)
}

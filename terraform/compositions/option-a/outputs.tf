## ─── Delinea Secret Server ────────────────────────────────────────────────────

output "ss_validation_all_valid" {
  description = "Whether all expected secrets were found in Secret Server"
  value       = module.delinea_folders.all_valid
}

output "ss_validation_expected" {
  description = "Number of expected secrets"
  value       = module.delinea_folders.expected_count
}

output "ss_validation_found" {
  description = "Number of secrets actually found"
  value       = module.delinea_folders.found_count
}

## ─── StrongDM ─────────────────────────────────────────────────────────────────

output "strongdm_gateway_id" {
  description = "StrongDM gateway node ID"
  value       = module.strongdm.gateway_id
}

output "strongdm_gateway_token" {
  description = "Gateway token for starting the StrongDM gateway process"
  value       = module.strongdm.gateway_token
  sensitive   = true
}

output "strongdm_resource_ids" {
  description = "Map of resource name to StrongDM resource ID"
  value       = module.strongdm.resource_ids
}

output "strongdm_role_ids" {
  description = "Map of role name to StrongDM role ID"
  value       = module.strongdm.role_ids
}

output "strongdm_resource_count" {
  description = "Number of StrongDM resources registered"
  value       = module.strongdm.resource_count
}

## ─── Shared References ───────────────────────────────────────────────────────

output "orchestrator_public_ip" {
  description = "Orchestrator VM public IP (from shared state)"
  value       = data.terraform_remote_state.shared.outputs.orchestrator_public_ip
}

output "key_vault_uri" {
  description = "Key Vault URI (from shared state)"
  value       = data.terraform_remote_state.shared.outputs.key_vault_uri
}

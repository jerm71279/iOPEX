## ─── CyberArk Privilege Cloud ─────────────────────────────────────────────────

output "safe_ids" {
  description = "Map of safe name to Privilege Cloud safe ID"
  value       = module.cyberark_safes.safe_ids
}

output "safe_count" {
  description = "Number of safes created in Privilege Cloud"
  value       = module.cyberark_safes.safe_count
}

output "safe_names" {
  description = "List of created safe names"
  value       = module.cyberark_safes.safe_names
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

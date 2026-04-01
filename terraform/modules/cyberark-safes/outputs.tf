output "safe_ids" {
  description = "Map of safe name to safe resource ID"
  value       = { for k, v in cyberark_safe.migration_target : k => v.id }
}

output "safe_count" {
  description = "Number of safes created"
  value       = length(cyberark_safe.migration_target)
}

output "safe_names" {
  description = "List of created safe names"
  value       = [for s in cyberark_safe.migration_target : s.safe_name]
}

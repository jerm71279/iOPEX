output "validation_results" {
  description = "Map of secret ID to validation result"
  value       = local.validation_results
}

output "expected_count" {
  description = "Number of expected secrets"
  value       = local.expected_count
}

output "found_count" {
  description = "Number of secrets found"
  value       = local.found_count
}

output "all_valid" {
  description = "Whether all expected secrets were found"
  value       = local.all_valid
}

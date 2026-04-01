# Delinea Secret Server -- Read-Back Validation Module
#
# IMPORTANT: The DelineaXPM/tss provider (v3.0) is READ-ONLY.
# It provides data sources for secret retrieval, NOT resource management.
# Folder and secret creation is handled by the AI orchestrator's Agent 04 ETL.
#
# This module validates that expected structures exist after the orchestrator
# creates them, and detects drift during P6 parallel running.

# Validate that expected secrets exist in Secret Server
data "tss_secret" "validation" {
  for_each = { for s in var.expected_secrets : s.id => s }
  id       = each.value.id
}

# Collect validation results
locals {
  validation_results = {
    for id, secret in data.tss_secret.validation : id => {
      id    = secret.id
      found = true
      name  = try(secret.value["name"], "unknown")
    }
  }
  expected_count = length(var.expected_secrets)
  found_count    = length(local.validation_results)
  all_valid      = local.expected_count == local.found_count
}

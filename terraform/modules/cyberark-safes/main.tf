# CyberArk Privilege Cloud Safe Structures
# Creates empty safe containers that the AI orchestrator's Agent 04 ETL
# then populates via the 7-step pipeline (FREEZE->EXPORT->TRANSFORM->CREATE->IMPORT->HEARTBEAT->UNFREEZE)
# Terraform manages containers; the orchestrator manages contents.

resource "cyberark_safe" "migration_target" {
  for_each = { for s in var.safes : s.name => s }

  safe_name                    = each.value.name
  safe_desc                    = each.value.description
  managing_cpm                 = each.value.managing_cpm
  number_of_versions_retention = each.value.number_of_versions
  number_of_days_retention     = each.value.retention_days
}

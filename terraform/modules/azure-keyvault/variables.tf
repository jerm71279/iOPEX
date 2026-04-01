###############################################################################
# Azure Key Vault Module — Variables
###############################################################################

variable "resource_group_name" {
  type        = string
  description = "Name of the resource group to deploy the Key Vault into."
}

variable "location" {
  type        = string
  description = "Azure region for the Key Vault."
}

variable "key_vault_name" {
  type        = string
  description = "Globally unique name for the Key Vault (3-24 chars, alphanumeric and hyphens)."
}

variable "vm_identity_principal_id" {
  type        = string
  description = "Managed identity principal ID of the orchestrator VM. Granted Key Vault Secrets User role."
}

variable "tags" {
  type        = map(string)
  default     = {}
  description = "Tags to apply to Key Vault resources."
}

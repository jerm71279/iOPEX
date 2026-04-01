###############################################################################
# Azure Monitoring Module — Variables
###############################################################################

variable "resource_group_name" {
  type        = string
  description = "Name of the resource group to deploy monitoring resources into."
}

variable "location" {
  type        = string
  description = "Azure region for monitoring resources."
}

variable "workspace_name" {
  type        = string
  default     = "la-pam-migration"
  description = "Name of the Log Analytics workspace."
}

variable "retention_days" {
  type        = number
  default     = 90
  description = "Number of days to retain log data in the workspace."
}

variable "alert_email" {
  type        = string
  description = "Email address to receive PAM migration metric alert notifications."
}

variable "vm_id" {
  type        = string
  description = "Resource ID of the orchestrator VM for metric alert scoping."
}

variable "tags" {
  type        = map(string)
  default     = {}
  description = "Tags to apply to all monitoring resources."
}

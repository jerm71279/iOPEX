## ─── Environment ──────────────────────────────────────────────────────────────

variable "environment" {
  type        = string
  description = "Environment name (dev, staging, prod)"
  validation {
    condition     = contains(["dev", "staging", "prod"], var.environment)
    error_message = "Environment must be dev, staging, or prod."
  }
}

## ─── Shared State ─────────────────────────────────────────────────────────────

variable "shared_state_key" {
  type        = string
  default     = "shared.tfstate"
  description = "State file key for the shared composition (include environment suffix)"
}

## ─── CyberArk Privilege Cloud ─────────────────────────────────────────────────

variable "privilege_cloud_tenant" {
  type        = string
  description = "Privilege Cloud tenant ID"
}

variable "privilege_cloud_domain" {
  type        = string
  description = "Privilege Cloud domain (e.g., cyberark.cloud)"
}

variable "pcloud_client_id" {
  type        = string
  sensitive   = true
  description = "OAuth2 client ID for Privilege Cloud (via CyberArk Identity)"
}

variable "pcloud_client_secret" {
  type        = string
  sensitive   = true
  description = "OAuth2 client secret for Privilege Cloud"
}

variable "target_safes" {
  description = "List of target safes to create in Privilege Cloud"
  type = list(object({
    name               = string
    description        = string
    managing_cpm       = optional(string, "PasswordManager")
    number_of_versions = optional(number, 5)
    retention_days     = optional(number, 30)
  }))
  default = []
}

## ─── Tags ─────────────────────────────────────────────────────────────────────

variable "extra_tags" {
  type        = map(string)
  default     = {}
  description = "Additional tags to apply to all resources"
}

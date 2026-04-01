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

## ─── Delinea Secret Server ────────────────────────────────────────────────────

variable "secret_server_url" {
  type        = string
  description = "Secret Server base URL (e.g., https://secretserver.company.com/SecretServer)"
}

variable "ss_client_id" {
  type        = string
  sensitive   = true
  description = "OAuth2 client ID for Secret Server"
}

variable "ss_client_secret" {
  type        = string
  sensitive   = true
  description = "OAuth2 client secret for Secret Server"
}

variable "expected_secrets" {
  description = "Secret IDs expected to exist in SS (for read-back validation)"
  type = list(object({
    id   = number
    name = optional(string, "")
  }))
  default = []
}

## ─── StrongDM ─────────────────────────────────────────────────────────────────

variable "sdm_api_access_key" {
  type        = string
  sensitive   = true
  description = "StrongDM API access key"
}

variable "sdm_api_secret_key" {
  type        = string
  sensitive   = true
  description = "StrongDM API secret key"
}

variable "gateway_name" {
  type        = string
  default     = "pam-migration-gateway"
  description = "StrongDM gateway node name"
}

variable "gateway_listen_address" {
  type        = string
  default     = "0.0.0.0:5000"
  description = "Address the StrongDM gateway listens on"
}

variable "strongdm_resources" {
  description = "Target resources to register in StrongDM"
  type = list(object({
    name     = string
    type     = string
    hostname = string
    port     = number
    username = optional(string, "")
    password = optional(string, "")
    database = optional(string, "")
    tags     = optional(map(string), {})
  }))
  default = []
}

variable "strongdm_roles" {
  description = "Access roles to create in StrongDM"
  type = list(object({
    name = string
    tags = optional(map(string), {})
  }))
  default = []
}

variable "strongdm_role_grants" {
  description = "Role-to-resource access grants"
  type = list(object({
    role_name     = string
    resource_name = string
  }))
  default = []
}

## ─── Tags ─────────────────────────────────────────────────────────────────────

variable "extra_tags" {
  type        = map(string)
  default     = {}
  description = "Additional tags to apply to all resources"
}

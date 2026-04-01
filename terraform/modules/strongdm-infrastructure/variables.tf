variable "gateway_name" {
  type        = string
  default     = "pam-migration-gateway"
  description = "StrongDM gateway node name"
}

variable "gateway_listen_address" {
  type        = string
  default     = "0.0.0.0:5000"
  description = "Address the gateway listens on"
}

variable "gateway_bind_address" {
  type        = string
  default     = "0.0.0.0:5001"
  description = "Address the gateway binds to for relay connections"
}

variable "resources" {
  description = "Target resources to register in StrongDM"
  type = list(object({
    name     = string
    type     = string # ssh, rdp, postgres, mysql
    hostname = string
    port     = number
    username = optional(string, "")
    password = optional(string, "")
    database = optional(string, "")
    tags     = optional(map(string), {})
  }))
  default = []
}

variable "roles" {
  description = "Access roles to create in StrongDM"
  type = list(object({
    name = string
    tags = optional(map(string), {})
  }))
  default = []
}

variable "role_grants" {
  description = "Role-to-resource access grants"
  type = list(object({
    role_name     = string
    resource_name = string
  }))
  default = []
}

variable "environment" {
  type        = string
  description = "Environment name (dev, staging, prod)"
}

variable "tags" {
  type        = map(string)
  default     = {}
  description = "Tags applied to all resources"
}

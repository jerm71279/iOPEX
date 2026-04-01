variable "safes" {
  description = "List of target safes to create in Privilege Cloud"
  type = list(object({
    name               = string
    description        = string
    managing_cpm       = optional(string, "PasswordManager")
    number_of_versions = optional(number, 5)
    retention_days     = optional(number, 30)
  }))
}

variable "environment" {
  type        = string
  description = "Environment name (dev, staging, prod)"
}

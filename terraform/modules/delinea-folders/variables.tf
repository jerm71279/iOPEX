variable "secret_server_url" {
  type        = string
  description = "Secret Server base URL (e.g., https://secretserver.company.com/SecretServer)"
}

variable "client_id" {
  type        = string
  sensitive   = true
  description = "OAuth2 client ID for Secret Server"
}

variable "client_secret" {
  type        = string
  sensitive   = true
  description = "OAuth2 client secret for Secret Server"
}

variable "expected_secrets" {
  description = "List of secrets expected to exist (for read-back validation)"
  type = list(object({
    id   = number
    name = optional(string, "")
  }))
  default = []
}

variable "environment" {
  type        = string
  description = "Environment name (dev, staging, prod)"
}

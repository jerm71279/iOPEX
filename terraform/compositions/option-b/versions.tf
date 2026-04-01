terraform {
  required_version = ">= 1.6.0"

  required_providers {
    cyberark = {
      source  = "cyberark/cyberark"
      version = "~> 0.2"
    }
  }
}

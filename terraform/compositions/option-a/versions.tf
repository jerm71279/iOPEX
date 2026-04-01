terraform {
  required_version = ">= 1.6.0"

  required_providers {
    tss = {
      source  = "DelineaXPM/tss"
      version = "~> 3.0"
    }
    sdm = {
      source  = "strongdm/sdm"
      version = "~> 16.0"
    }
  }
}

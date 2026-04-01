provider "azurerm" {
  features {
    key_vault {
      purge_soft_delete_on_destroy = false
    }
    virtual_machine {
      delete_os_disk_on_deletion = true
    }
  }

  subscription_id = var.azure_subscription_id
}

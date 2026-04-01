terraform {
  backend "azurerm" {
    resource_group_name  = "rg-pam-tfstate"
    storage_account_name = "stpamtfstate"
    container_name       = "tfstate"
    key                  = "option-a.tfstate"
    # Environment suffix set via: -backend-config="key=option-a.ENV.tfstate"
  }
}

###############################################################################
# Azure Networking Module — Variables
###############################################################################

variable "resource_group_name" {
  type        = string
  description = "Name of the resource group to deploy networking resources into."
}

variable "location" {
  type        = string
  description = "Azure region for all networking resources."
}

variable "vnet_name" {
  type        = string
  default     = "vnet-pam-migration"
  description = "Name of the virtual network."
}

variable "vnet_address_space" {
  type        = list(string)
  default     = ["10.200.0.0/16"]
  description = "Address space for the PAM migration VNet."
}

variable "subnet_orchestrator_prefix" {
  type        = string
  default     = "10.200.1.0/24"
  description = "CIDR prefix for the orchestrator subnet."
}

variable "subnet_connectors_prefix" {
  type        = string
  default     = "10.200.2.0/24"
  description = "CIDR prefix for the connectors subnet (PSM, CPM, CCP components)."
}

variable "subnet_management_prefix" {
  type        = string
  default     = "10.200.3.0/24"
  description = "CIDR prefix for the management subnet."
}

variable "admin_cidr" {
  type        = string
  description = "CIDR block permitted for SSH management access to orchestrator resources."
}

variable "on_prem_cidr" {
  type        = string
  default     = "10.0.0.0/8"
  description = "On-premises network CIDR for PVWA callback and VPN routing."
}

variable "on_prem_gateway_ip" {
  type        = string
  default     = ""
  description = "Public IP of the on-premises VPN gateway device. Required when enable_vpn_gateway is true."
}

variable "enable_vpn_gateway" {
  type        = bool
  default     = false
  description = "Whether to deploy a site-to-site VPN gateway for on-premises connectivity."
}

variable "tags" {
  type        = map(string)
  default     = {}
  description = "Tags to apply to all networking resources."
}

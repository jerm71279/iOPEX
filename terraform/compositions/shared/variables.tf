## ─── Azure Subscription ───────────────────────────────────────────────────────

variable "azure_subscription_id" {
  type        = string
  description = "Azure subscription ID for PAM migration resources"
}

## ─── Environment ──────────────────────────────────────────────────────────────

variable "environment" {
  type        = string
  description = "Environment name (dev, staging, prod)"
  validation {
    condition     = contains(["dev", "staging", "prod"], var.environment)
    error_message = "Environment must be dev, staging, or prod."
  }
}

variable "location" {
  type        = string
  default     = "eastus2"
  description = "Azure region for all resources"
}

variable "migration_option" {
  type        = string
  default     = "a"
  description = "Migration target: a = Delinea SS + StrongDM, b = CyberArk Privilege Cloud"
  validation {
    condition     = contains(["a", "b"], var.migration_option)
    error_message = "Migration option must be a or b."
  }
}

## ─── Networking ───────────────────────────────────────────────────────────────

variable "vnet_address_space" {
  type        = list(string)
  default     = ["10.200.0.0/16"]
  description = "VNet address space"
}

variable "subnet_orchestrator_prefix" {
  type        = string
  default     = "10.200.1.0/24"
  description = "Subnet CIDR for the orchestrator VM"
}

variable "subnet_connectors_prefix" {
  type        = string
  default     = "10.200.2.0/24"
  description = "Subnet CIDR for PAM connectors (CPM, PSM, Distributed Engine)"
}

variable "subnet_management_prefix" {
  type        = string
  default     = "10.200.3.0/24"
  description = "Subnet CIDR for management access"
}

variable "admin_cidr" {
  type        = string
  description = "CIDR for SSH management access to the orchestrator VM"
}

variable "on_prem_cidr" {
  type        = string
  default     = "10.0.0.0/8"
  description = "On-premises network CIDR (for VPN/ExpressRoute and NSG rules)"
}

variable "on_prem_gateway_ip" {
  type        = string
  default     = ""
  description = "On-premises VPN gateway public IP address"
}

variable "enable_vpn_gateway" {
  type        = bool
  default     = false
  description = "Whether to provision an Azure VPN Gateway for on-prem connectivity"
}

variable "pvwa_ip" {
  type        = string
  default     = ""
  description = "On-prem CyberArk PVWA IP address for NSG rules"
}

## ─── Compute ──────────────────────────────────────────────────────────────────

variable "vm_size" {
  type        = string
  default     = "Standard_D4s_v5"
  description = "VM SKU: D2s_v5 (dev), D4s_v5 (staging), D8s_v5 (prod)"
}

variable "admin_username" {
  type        = string
  default     = "pamadmin"
  description = "SSH admin username for the orchestrator VM"
}

variable "ssh_public_key" {
  type        = string
  description = "SSH public key for the orchestrator VM"
}

variable "data_disk_size_gb" {
  type        = number
  default     = 128
  description = "Data disk size for orchestrator output (state, logs, reports)"
}

variable "cloud_init_script" {
  type        = string
  default     = ""
  description = "Cloud-init script to bootstrap the VM (Python 3.12, Docker, pip deps). If empty, cloud-init-nexus-core.yaml is rendered via templatefile()."
}

variable "nexus_wheel_storage_account" {
  type        = string
  default     = "stpamtfstate"
  description = "Storage account containing the nexus-core wheel for VM cloud-init download"
}

variable "nexus_wheel_version" {
  type        = string
  default     = "0.1.0"
  description = "nexus-core wheel version to install on the orchestrator VM (must match wheel in blob storage)"
}

## ─── Key Vault ────────────────────────────────────────────────────────────────

variable "key_vault_name" {
  type        = string
  default     = ""
  description = "Key Vault name (auto-generated if empty)"
}

## ─── Monitoring ───────────────────────────────────────────────────────────────

variable "alert_email" {
  type        = string
  description = "Email address for Azure Monitor alert notifications"
}

variable "retention_days" {
  type        = number
  default     = 90
  description = "Log Analytics retention (90 dev/staging, 365 prod)"
}

## ─── DNS ──────────────────────────────────────────────────────────────────────

variable "dns_zone_name" {
  type        = string
  default     = ""
  description = "Azure DNS zone name (leave empty to skip DNS provisioning)"
}

## ─── Tags ─────────────────────────────────────────────────────────────────────

variable "extra_tags" {
  type        = map(string)
  default     = {}
  description = "Additional tags to apply to all resources"
}

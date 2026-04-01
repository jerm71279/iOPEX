###############################################################################
# Azure Orchestrator VM Module — Variables
###############################################################################

variable "resource_group_name" {
  type        = string
  description = "Name of the resource group to deploy the VM into."
}

variable "location" {
  type        = string
  description = "Azure region for the virtual machine."
}

variable "vm_name" {
  type        = string
  default     = "pam-orchestrator"
  description = "Name of the orchestrator virtual machine."
}

variable "vm_size" {
  type        = string
  default     = "Standard_D4s_v5"
  description = "Azure VM size. D4s_v5 provides 4 vCPUs and 16 GB RAM suitable for the 15-agent orchestrator."
}

variable "admin_username" {
  type        = string
  default     = "pamadmin"
  description = "Admin username for SSH access to the VM."
}

variable "ssh_public_key" {
  type        = string
  description = "SSH public key for admin authentication. Paste the full public key string."
}

variable "subnet_id" {
  type        = string
  description = "Resource ID of the subnet to attach the VM network interface to."
}

variable "data_disk_size_gb" {
  type        = number
  default     = 128
  description = "Size in GB of the attached data disk for migration state, logs, and reports."
}

variable "cloud_init_script" {
  type        = string
  default     = ""
  description = "Cloud-init script to run on first boot. Passed as custom_data (base64-encoded automatically)."
}

variable "tags" {
  type        = map(string)
  default     = {}
  description = "Tags to apply to all VM resources."
}

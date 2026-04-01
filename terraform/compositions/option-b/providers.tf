# CyberArk Privilege Cloud — safe and account management
provider "cyberark" {
  tenant        = var.privilege_cloud_tenant
  domain        = var.privilege_cloud_domain
  client_id     = var.pcloud_client_id
  client_secret = var.pcloud_client_secret
}

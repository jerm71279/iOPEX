# Delinea Secret Server — read-only validation
provider "tss" {
  server_url = var.secret_server_url
  username   = var.ss_client_id
  password   = var.ss_client_secret
}

# StrongDM — full CRUD session proxy management
provider "sdm" {
  api_access_key = var.sdm_api_access_key
  api_secret_key = var.sdm_api_secret_key
}

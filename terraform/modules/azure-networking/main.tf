###############################################################################
# Azure Networking Module — PAM Migration Control Center
# Phase P0: VNet, subnets, NSGs, optional site-to-site VPN gateway
###############################################################################

# -----------------------------------------------------------------------------
# Virtual Network
# -----------------------------------------------------------------------------
resource "azurerm_virtual_network" "pam_migration" {
  name                = var.vnet_name
  location            = var.location
  resource_group_name = var.resource_group_name
  address_space       = var.vnet_address_space

  tags = var.tags
}

# -----------------------------------------------------------------------------
# Subnets
# -----------------------------------------------------------------------------
resource "azurerm_subnet" "orchestrator" {
  name                 = "snet-orchestrator"
  resource_group_name  = var.resource_group_name
  virtual_network_name = azurerm_virtual_network.pam_migration.name
  address_prefixes     = [var.subnet_orchestrator_prefix]
}

resource "azurerm_subnet" "connectors" {
  name                 = "snet-connectors"
  resource_group_name  = var.resource_group_name
  virtual_network_name = azurerm_virtual_network.pam_migration.name
  address_prefixes     = [var.subnet_connectors_prefix]
}

resource "azurerm_subnet" "management" {
  name                 = "snet-management"
  resource_group_name  = var.resource_group_name
  virtual_network_name = azurerm_virtual_network.pam_migration.name
  address_prefixes     = [var.subnet_management_prefix]
}

# GatewaySubnet is required by Azure for VPN gateways and must use this exact name.
resource "azurerm_subnet" "gateway" {
  count = var.enable_vpn_gateway ? 1 : 0

  name                 = "GatewaySubnet"
  resource_group_name  = var.resource_group_name
  virtual_network_name = azurerm_virtual_network.pam_migration.name
  address_prefixes     = [cidrsubnet(var.vnet_address_space[0], 11, 1023)] # /27 from the end of the VNet space
}

# -----------------------------------------------------------------------------
# Network Security Group — Orchestrator Subnet
# -----------------------------------------------------------------------------
resource "azurerm_network_security_group" "orchestrator" {
  name                = "nsg-pam-orchestrator"
  location            = var.location
  resource_group_name = var.resource_group_name

  # --- Inbound Rules ---

  security_rule {
    name                       = "AllowSSHFromAdmin"
    priority                   = 100
    direction                  = "Inbound"
    access                     = "Allow"
    protocol                   = "Tcp"
    source_port_range          = "*"
    destination_port_range     = "22"
    source_address_prefix      = var.admin_cidr
    destination_address_prefix = "*"
    description                = "Allow SSH management access from admin CIDR"
  }

  security_rule {
    name                       = "AllowHTTPSFromOnPrem"
    priority                   = 110
    direction                  = "Inbound"
    access                     = "Allow"
    protocol                   = "Tcp"
    source_port_range          = "*"
    destination_port_range     = "443"
    source_address_prefix      = var.on_prem_cidr
    destination_address_prefix = "*"
    description                = "Allow HTTPS inbound from on-prem network (PVWA callback)"
  }

  security_rule {
    name                       = "DenyAllInbound"
    priority                   = 4096
    direction                  = "Inbound"
    access                     = "Deny"
    protocol                   = "*"
    source_port_range          = "*"
    destination_port_range     = "*"
    source_address_prefix      = "*"
    destination_address_prefix = "*"
    description                = "Deny all other inbound traffic"
  }

  # --- Outbound Rules ---

  security_rule {
    name                       = "AllowHTTPSOutbound"
    priority                   = 100
    direction                  = "Outbound"
    access                     = "Allow"
    protocol                   = "Tcp"
    source_port_range          = "*"
    destination_port_range     = "443"
    source_address_prefix      = "*"
    destination_address_prefix = "Internet"
    description                = "Allow HTTPS outbound to PAM platforms (Privilege Cloud, Secret Server, CyberArk Identity)"
  }

  tags = var.tags
}

resource "azurerm_subnet_network_security_group_association" "orchestrator" {
  subnet_id                 = azurerm_subnet.orchestrator.id
  network_security_group_id = azurerm_network_security_group.orchestrator.id
}

# -----------------------------------------------------------------------------
# VPN Gateway (conditional)
# -----------------------------------------------------------------------------
resource "azurerm_public_ip" "vpn_gw" {
  count = var.enable_vpn_gateway ? 1 : 0

  name                = "pip-pam-vpn-gw"
  location            = var.location
  resource_group_name = var.resource_group_name
  allocation_method   = "Static"
  sku                 = "Standard"

  tags = var.tags
}

resource "azurerm_virtual_network_gateway" "vpn" {
  count = var.enable_vpn_gateway ? 1 : 0

  name                = "vgw-pam-migration"
  location            = var.location
  resource_group_name = var.resource_group_name

  type     = "Vpn"
  vpn_type = "RouteBased"
  sku      = "VpnGw1"

  ip_configuration {
    name                          = "vgw-ip-config"
    public_ip_address_id          = azurerm_public_ip.vpn_gw[0].id
    private_ip_address_allocation = "Dynamic"
    subnet_id                     = azurerm_subnet.gateway[0].id
  }

  tags = var.tags
}

resource "azurerm_local_network_gateway" "on_prem" {
  count = var.enable_vpn_gateway ? 1 : 0

  name                = "lgw-on-prem"
  location            = var.location
  resource_group_name = var.resource_group_name
  gateway_address     = var.on_prem_gateway_ip
  address_space       = [var.on_prem_cidr]

  tags = var.tags
}

###############################################################################
# Azure Orchestrator VM Module — PAM Migration Control Center
# Phase P0: Ubuntu 22.04 VM with managed identity for the 15-agent AI orchestrator
###############################################################################

# -----------------------------------------------------------------------------
# Public IP
# -----------------------------------------------------------------------------
resource "azurerm_public_ip" "orchestrator" {
  name                = "pip-${var.vm_name}"
  location            = var.location
  resource_group_name = var.resource_group_name
  allocation_method   = "Static"
  sku                 = "Standard"

  tags = var.tags
}

# -----------------------------------------------------------------------------
# Network Interface
# -----------------------------------------------------------------------------
resource "azurerm_network_interface" "orchestrator" {
  name                = "nic-${var.vm_name}"
  location            = var.location
  resource_group_name = var.resource_group_name

  ip_configuration {
    name                          = "internal"
    subnet_id                     = var.subnet_id
    private_ip_address_allocation = "Dynamic"
    public_ip_address_id          = azurerm_public_ip.orchestrator.id
  }

  tags = var.tags
}

# -----------------------------------------------------------------------------
# Linux Virtual Machine
# -----------------------------------------------------------------------------
resource "azurerm_linux_virtual_machine" "orchestrator" {
  name                = var.vm_name
  location            = var.location
  resource_group_name = var.resource_group_name
  size                = var.vm_size

  admin_username                  = var.admin_username
  disable_password_authentication = true

  admin_ssh_key {
    username   = var.admin_username
    public_key = var.ssh_public_key
  }

  network_interface_ids = [
    azurerm_network_interface.orchestrator.id,
  ]

  os_disk {
    name                 = "osdisk-${var.vm_name}"
    caching              = "ReadWrite"
    storage_account_type = "StandardSSD_LRS"
    disk_size_gb         = 64
  }

  source_image_reference {
    publisher = "Canonical"
    offer     = "0001-com-ubuntu-server-jammy"
    sku       = "22_04-lts"
    version   = "latest"
  }

  identity {
    type = "SystemAssigned"
  }

  custom_data = var.cloud_init_script != "" ? base64encode(var.cloud_init_script) : null

  tags = var.tags
}

# -----------------------------------------------------------------------------
# Data Disk
# -----------------------------------------------------------------------------
resource "azurerm_managed_disk" "data" {
  name                 = "datadisk-${var.vm_name}"
  location             = var.location
  resource_group_name  = var.resource_group_name
  storage_account_type = "StandardSSD_LRS"
  create_option        = "Empty"
  disk_size_gb         = var.data_disk_size_gb

  tags = var.tags
}

resource "azurerm_virtual_machine_data_disk_attachment" "data" {
  managed_disk_id    = azurerm_managed_disk.data.id
  virtual_machine_id = azurerm_linux_virtual_machine.orchestrator.id
  lun                = 0
  caching            = "ReadWrite"
}

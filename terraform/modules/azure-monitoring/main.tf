###############################################################################
# Azure Monitoring Module — PAM Migration Control Center
# Phase P0: Log Analytics workspace, action group, and metric alerts for the
# orchestrator VM (CPU, disk, memory)
###############################################################################

# -----------------------------------------------------------------------------
# Log Analytics Workspace
# -----------------------------------------------------------------------------
resource "azurerm_log_analytics_workspace" "pam" {
  name                = var.workspace_name
  location            = var.location
  resource_group_name = var.resource_group_name
  sku                 = "PerGB2018"
  retention_in_days   = var.retention_days

  tags = var.tags
}

# -----------------------------------------------------------------------------
# Action Group — email notifications for PAM migration alerts
# -----------------------------------------------------------------------------
resource "azurerm_monitor_action_group" "pam_alerts" {
  name                = "ag-pam-migration-alerts"
  resource_group_name = var.resource_group_name
  short_name          = "PAMAlerts"

  email_receiver {
    name                    = "pam-admin"
    email_address           = var.alert_email
    use_common_alert_schema = true
  }

  tags = var.tags
}

# -----------------------------------------------------------------------------
# Metric Alert — CPU utilization > 90% for 5 minutes
# -----------------------------------------------------------------------------
resource "azurerm_monitor_metric_alert" "cpu_high" {
  name                = "alert-pam-orchestrator-cpu-high"
  resource_group_name = var.resource_group_name
  scopes              = [var.vm_id]
  description         = "PAM orchestrator VM CPU utilization exceeds 90 percent for 5 minutes."
  severity            = 2
  frequency           = "PT1M"
  window_size         = "PT5M"

  criteria {
    metric_namespace = "Microsoft.Compute/virtualMachines"
    metric_name      = "Percentage CPU"
    aggregation      = "Average"
    operator         = "GreaterThan"
    threshold        = 90
  }

  action {
    action_group_id = azurerm_monitor_action_group.pam_alerts.id
  }

  tags = var.tags
}

# -----------------------------------------------------------------------------
# Metric Alert — OS Disk Queue Depth > 10 for 5 minutes
# -----------------------------------------------------------------------------
resource "azurerm_monitor_metric_alert" "disk_high" {
  name                = "alert-pam-orchestrator-disk-queue-high"
  resource_group_name = var.resource_group_name
  scopes              = [var.vm_id]
  description         = "PAM orchestrator VM OS disk queue depth exceeds 10 for 5 minutes, indicating disk saturation."
  severity            = 2
  frequency           = "PT1M"
  window_size         = "PT5M"

  criteria {
    metric_namespace = "Microsoft.Compute/virtualMachines"
    metric_name      = "OS Disk Queue Depth"
    aggregation      = "Average"
    operator         = "GreaterThan"
    threshold        = 10
  }

  action {
    action_group_id = azurerm_monitor_action_group.pam_alerts.id
  }

  tags = var.tags
}

# -----------------------------------------------------------------------------
# Metric Alert — Available Memory < 1 GB for 5 minutes
# -----------------------------------------------------------------------------
resource "azurerm_monitor_metric_alert" "memory_high" {
  name                = "alert-pam-orchestrator-memory-low"
  resource_group_name = var.resource_group_name
  scopes              = [var.vm_id]
  description         = "PAM orchestrator VM available memory is below 1 GB for 5 minutes."
  severity            = 2
  frequency           = "PT1M"
  window_size         = "PT5M"

  criteria {
    metric_namespace = "Microsoft.Compute/virtualMachines"
    metric_name      = "Available Memory Bytes"
    aggregation      = "Average"
    operator         = "LessThan"
    threshold        = 1073741824 # 1 GB in bytes
  }

  action {
    action_group_id = azurerm_monitor_action_group.pam_alerts.id
  }

  tags = var.tags
}

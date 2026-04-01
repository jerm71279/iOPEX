# StrongDM Infrastructure -- Session Proxy Layer
# Replaces CyberArk PSM for privileged session management in Option A.
# The sdm provider (v16.14) is the most mature PAM provider -- full CRUD.

# Gateway node -- runs on the orchestrator VM
resource "sdm_node" "gateway" {
  gateway {
    name           = var.gateway_name
    listen_address = var.gateway_listen_address
    bind_address   = var.gateway_bind_address
    tags           = var.tags
  }
}

# Target resources -- servers, databases, clusters
resource "sdm_resource" "targets" {
  for_each = { for r in var.resources : r.name => r }

  dynamic "ssh" {
    for_each = each.value.type == "ssh" ? [1] : []
    content {
      name     = each.value.name
      hostname = each.value.hostname
      port     = each.value.port
      username = each.value.username
      tags     = merge(var.tags, each.value.tags)
    }
  }

  dynamic "rdp" {
    for_each = each.value.type == "rdp" ? [1] : []
    content {
      name     = each.value.name
      hostname = each.value.hostname
      port     = each.value.port
      username = each.value.username
      password = each.value.password
      tags     = merge(var.tags, each.value.tags)
    }
  }

  dynamic "postgres" {
    for_each = each.value.type == "postgres" ? [1] : []
    content {
      name     = each.value.name
      hostname = each.value.hostname
      port     = each.value.port
      database = each.value.database
      username = each.value.username
      password = each.value.password
      tags     = merge(var.tags, each.value.tags)
    }
  }

  dynamic "mysql" {
    for_each = each.value.type == "mysql" ? [1] : []
    content {
      name     = each.value.name
      hostname = each.value.hostname
      port     = each.value.port
      database = each.value.database
      username = each.value.username
      password = each.value.password
      tags     = merge(var.tags, each.value.tags)
    }
  }
}

# Access roles -- mapped from CyberArk safe memberships
resource "sdm_role" "access_roles" {
  for_each = { for r in var.roles : r.name => r }
  name     = each.value.name
  tags     = merge(var.tags, each.value.tags)
}

# Role grants -- bind roles to resources
resource "sdm_role_grant" "grants" {
  for_each    = { for g in var.role_grants : "${g.role_name}-${g.resource_name}" => g }
  role_id     = sdm_role.access_roles[each.value.role_name].id
  resource_id = sdm_resource.targets[each.value.resource_name].id
}

// iOPEX PAM Migration — Azure Resource Group Deployment
// Security-hardened infrastructure for the 15-agent SHIFT migration system
//
// Deploy:
//   az deployment group create \
//     --resource-group <rg-name> \
//     --template-file azure/bicep/main.bicep \
//     --parameters @azure/bicep/parameters.json

@description('Environment name — used as prefix for all resources')
param envName string = 'pam-migration'

@description('Azure region')
param location string = resourceGroup().location

@description('Container image tag (use digest in production: sha256:...)')
param imageTag string = 'latest'

@description('VNet address space')
param vnetAddressPrefix string = '10.0.0.0/16'

@description('Container Apps subnet — must be /23 minimum, delegated to Microsoft.App/environments')
param caSubnetPrefix string = '10.0.0.0/23'

@description('Private endpoint subnet')
param peSubnetPrefix string = '10.0.2.0/24'

@description('Log Analytics retention in days')
param logRetentionDays int = 90

// ── Virtual Network ────────────────────────────────────────────────────────
// Security [HIGH]: All migration workloads run inside a private VNet.
// Traffic to Key Vault and SQL never traverses the public internet.
resource vnet 'Microsoft.Network/virtualNetworks@2023-05-01' = {
  name: '${envName}-vnet'
  location: location
  properties: {
    addressSpace: {
      addressPrefixes: [ vnetAddressPrefix ]
    }
    subnets: [
      {
        name: 'container-apps'
        properties: {
          addressPrefix: caSubnetPrefix
          delegations: [
            {
              name: 'ca-delegation'
              properties: { serviceName: 'Microsoft.App/environments' }
            }
          ]
          serviceEndpoints: [
            { service: 'Microsoft.Sql', locations: [ location ] }
            { service: 'Microsoft.Storage', locations: [ location ] }
            { service: 'Microsoft.KeyVault', locations: [ location ] }
          ]
        }
      }
      {
        name: 'private-endpoints'
        properties: {
          addressPrefix: peSubnetPrefix
          privateEndpointNetworkPolicies: 'Disabled'
        }
      }
    ]
  }
}

var caSubnetId = '${vnet.id}/subnets/container-apps'
var peSubnetId = '${vnet.id}/subnets/private-endpoints'

// ── Log Analytics Workspace ─────────────────────────────────────────────────
// Security [HIGH]: Centralised SIEM for all resource diagnostic logs.
// Required for PCI-DSS Req 10, NIST AU-2, SOX audit trail.
resource logAnalytics 'Microsoft.OperationalInsights/workspaces@2022-10-01' = {
  name: '${envName}-logs'
  location: location
  properties: {
    sku: { name: 'PerGB2018' }
    retentionInDays: logRetentionDays
    features: {
      enableLogAccessUsingOnlyResourcePermissions: true
    }
    publicNetworkAccessForIngestion: 'Enabled'
    publicNetworkAccessForQuery: 'Enabled'
  }
}

// ── Container Registry ─────────────────────────────────────────────────────
// Security [HIGH]: Standard SKU minimum for production (Basic has no content trust).
// Admin user disabled — Container App uses managed identity for pull.
resource acr 'Microsoft.ContainerRegistry/registries@2023-07-01' = {
  name: replace('${envName}acr', '-', '')
  location: location
  sku: { name: 'Standard' }
  properties: {
    adminUserEnabled: false
    policies: {
      retentionPolicy: {
        status: 'enabled'
        days: 30
      }
    }
  }
}

resource acrDiag 'Microsoft.Insights/diagnosticSettings@2021-05-01-preview' = {
  name: 'acr-diag'
  scope: acr
  properties: {
    workspaceId: logAnalytics.id
    logs: [
      { category: 'ContainerRegistryLoginEvents', enabled: true, retentionPolicy: { enabled: true, days: logRetentionDays } }
      { category: 'ContainerRegistryRepositoryEvents', enabled: true, retentionPolicy: { enabled: true, days: logRetentionDays } }
    ]
    metrics: [
      { category: 'AllMetrics', enabled: true, retentionPolicy: { enabled: true, days: logRetentionDays } }
    ]
  }
}

// ── Key Vault ───────────────────────────────────────────────────────────────
// Security [CRITICAL]: Purge protection prevents permanent deletion of PAM credentials.
// 90-day soft delete satisfies PCI-DSS and SOX minimum retention requirements.
// Network ACLs restrict access to VNet service endpoints + Azure trusted services only.
resource keyVault 'Microsoft.KeyVault/vaults@2023-07-01' = {
  name: '${envName}-kv'
  location: location
  properties: {
    sku: { family: 'A', name: 'standard' }
    tenantId: subscription().tenantId
    enableRbacAuthorization: true
    enablePurgeProtection: true
    softDeleteRetentionInDays: 90
    networkAcls: {
      defaultAction: 'Deny'
      bypass: 'AzureServices'
      virtualNetworkRules: [
        { id: caSubnetId, ignoreMissingVnetServiceEndpoint: false }
      ]
      ipRules: []
    }
  }
}

resource kvDiag 'Microsoft.Insights/diagnosticSettings@2021-05-01-preview' = {
  name: 'kv-diag'
  scope: keyVault
  properties: {
    workspaceId: logAnalytics.id
    logs: [
      { category: 'AuditEvent', enabled: true, retentionPolicy: { enabled: true, days: logRetentionDays } }
      { category: 'AzurePolicyEvaluationDetails', enabled: true, retentionPolicy: { enabled: true, days: logRetentionDays } }
    ]
    metrics: [
      { category: 'AllMetrics', enabled: true, retentionPolicy: { enabled: true, days: logRetentionDays } }
    ]
  }
}

// Key Vault private endpoint
resource kvPrivateEndpoint 'Microsoft.Network/privateEndpoints@2023-05-01' = {
  name: '${envName}-kv-pe'
  location: location
  properties: {
    subnet: { id: peSubnetId }
    privateLinkServiceConnections: [
      {
        name: '${envName}-kv-plsc'
        properties: {
          privateLinkServiceId: keyVault.id
          groupIds: [ 'vault' ]
        }
      }
    ]
  }
}

resource kvPrivateDnsZone 'Microsoft.Network/privateDnsZones@2020-06-01' = {
  name: 'privatelink.vaultcore.azure.net'
  location: 'global'
}

resource kvPrivateDnsZoneVnetLink 'Microsoft.Network/privateDnsZones/virtualNetworkLinks@2020-06-01' = {
  parent: kvPrivateDnsZone
  name: '${envName}-kv-dns-link'
  location: 'global'
  properties: {
    virtualNetwork: { id: vnet.id }
    registrationEnabled: false
  }
}

resource kvPrivateDnsZoneGroup 'Microsoft.Network/privateEndpoints/privateDnsZoneGroups@2023-05-01' = {
  parent: kvPrivateEndpoint
  name: 'kv-dns-zone-group'
  properties: {
    privateDnsZoneConfigs: [
      {
        name: 'privatelink-vaultcore'
        properties: { privateDnsZoneId: kvPrivateDnsZone.id }
      }
    ]
  }
}

// ── Storage Account (audit logs + state backups) ────────────────────────────
// Security [MEDIUM]: Network ACLs restrict to VNet + Azure trusted services.
// Public blob access disabled, TLS 1.2 enforced.
resource storage 'Microsoft.Storage/storageAccounts@2023-01-01' = {
  name: replace('${envName}store', '-', '')
  location: location
  sku: { name: 'Standard_LRS' }
  kind: 'StorageV2'
  properties: {
    minimumTlsVersion: 'TLS1_2'
    allowBlobPublicAccess: false
    supportsHttpsTrafficOnly: true
    networkAcls: {
      defaultAction: 'Deny'
      bypass: 'AzureServices, Logging, Metrics'
      virtualNetworkRules: [
        { id: caSubnetId, action: 'Allow' }
      ]
      ipRules: []
    }
  }
}

// Azure Files share for persistent Container App output/ volume
// Security [MEDIUM]: Migration state and reports persist across container restarts.
resource migrationFileShare 'Microsoft.Storage/storageAccounts/fileServices/shares@2023-01-01' = {
  name: '${storage.name}/default/migration-output'
  properties: {
    shareQuota: 100
    enabledProtocols: 'SMB'
  }
}

resource storageDiag 'Microsoft.Insights/diagnosticSettings@2021-05-01-preview' = {
  name: 'storage-diag'
  scope: storage
  properties: {
    workspaceId: logAnalytics.id
    metrics: [
      { category: 'Transaction', enabled: true, retentionPolicy: { enabled: true, days: logRetentionDays } }
    ]
  }
}

// ── Azure SQL Database ──────────────────────────────────────────────────────
// Security [HIGH]: Azure AD-only auth, VNet firewall rule, auditing to Log Analytics.
// No SQL password auth — managed identity only.
resource sqlServer 'Microsoft.Sql/servers@2023-05-01-preview' = {
  name: '${envName}-sql'
  location: location
  properties: {
    administrators: {
      azureADOnlyAuthentication: true
      administratorType: 'ActiveDirectory'
    }
    publicNetworkAccess: 'Disabled'
    minimalTlsVersion: '1.2'
  }
}

resource sqlDb 'Microsoft.Sql/servers/databases@2023-05-01-preview' = {
  parent: sqlServer
  name: 'pam-migration'
  location: location
  sku: { name: 'Basic', tier: 'Basic' }
}

// SQL firewall: allow Container Apps subnet via service endpoint
resource sqlVnetRule 'Microsoft.Sql/servers/virtualNetworkRules@2023-05-01-preview' = {
  parent: sqlServer
  name: 'allow-container-apps'
  properties: {
    virtualNetworkSubnetId: caSubnetId
    ignoreMissingVnetServiceEndpoint: false
  }
}

// SQL auditing to Log Analytics
// Security [HIGH]: All SQL operations logged — satisfies PCI-DSS Req 10.
resource sqlAudit 'Microsoft.Sql/servers/auditingSettings@2023-05-01-preview' = {
  parent: sqlServer
  name: 'default'
  properties: {
    state: 'Enabled'
    isAzureMonitorTargetEnabled: true
    auditActionsAndGroups: [
      'SUCCESSFUL_DATABASE_AUTHENTICATION_GROUP'
      'FAILED_DATABASE_AUTHENTICATION_GROUP'
      'BATCH_COMPLETED_GROUP'
      'DATABASE_OBJECT_ACCESS_GROUP'
    ]
  }
}

// SQL private endpoint
resource sqlPrivateEndpoint 'Microsoft.Network/privateEndpoints@2023-05-01' = {
  name: '${envName}-sql-pe'
  location: location
  properties: {
    subnet: { id: peSubnetId }
    privateLinkServiceConnections: [
      {
        name: '${envName}-sql-plsc'
        properties: {
          privateLinkServiceId: sqlServer.id
          groupIds: [ 'sqlServer' ]
        }
      }
    ]
  }
}

resource sqlPrivateDnsZone 'Microsoft.Network/privateDnsZones@2020-06-01' = {
  name: 'privatelink.database.windows.net'
  location: 'global'
}

resource sqlPrivateDnsZoneVnetLink 'Microsoft.Network/privateDnsZones/virtualNetworkLinks@2020-06-01' = {
  parent: sqlPrivateDnsZone
  name: '${envName}-sql-dns-link'
  location: 'global'
  properties: {
    virtualNetwork: { id: vnet.id }
    registrationEnabled: false
  }
}

resource sqlPrivateDnsZoneGroup 'Microsoft.Network/privateEndpoints/privateDnsZoneGroups@2023-05-01' = {
  parent: sqlPrivateEndpoint
  name: 'sql-dns-zone-group'
  properties: {
    privateDnsZoneConfigs: [
      {
        name: 'privatelink-database'
        properties: { privateDnsZoneId: sqlPrivateDnsZone.id }
      }
    ]
  }
}

// ── Application Insights ────────────────────────────────────────────────────
resource appInsights 'Microsoft.Insights/components@2020-02-02' = {
  name: '${envName}-ai'
  location: location
  kind: 'other'
  properties: {
    Application_Type: 'other'
    WorkspaceResourceId: logAnalytics.id
  }
}

// Store App Insights connection string in Key Vault
// Security [CRITICAL]: Connection string never appears as a plaintext env var.
// Container App reads it via managed identity at runtime.
resource aiConnectionStringSecret 'Microsoft.KeyVault/vaults/secrets@2023-07-01' = {
  parent: keyVault
  name: 'appinsights-connection-string'
  properties: {
    value: appInsights.properties.ConnectionString
    attributes: { enabled: true }
  }
}

// ── Container Apps Environment ─────────────────────────────────────────────
// Security [HIGH]: VNet-integrated — all outbound traffic stays in the VNet.
resource caEnvironment 'Microsoft.App/managedEnvironments@2023-05-01' = {
  name: '${envName}-env'
  location: location
  properties: {
    daprAIConnectionString: appInsights.properties.ConnectionString
    vnetConfiguration: {
      infrastructureSubnetId: caSubnetId
      internal: false
    }
  }
  dependsOn: [ vnet ]
}

// Mount Azure Files share as persistent volume for output/
resource caEnvStorage 'Microsoft.App/managedEnvironments/storages@2023-05-01' = {
  parent: caEnvironment
  name: 'migration-output'
  properties: {
    azureFile: {
      accountName: storage.name
      accountKey: storage.listKeys().keys[0].value
      shareName: 'migration-output'
      accessMode: 'ReadWrite'
    }
  }
}

// ── Container App ─────────────────────────────────────────────────────────
// Security [HIGH]: SystemAssigned managed identity — no service principal password.
// App Insights connection string injected via Key Vault secret reference.
// All credential env vars supplied at deploy time via secretRef (not hardcoded).
resource containerApp 'Microsoft.App/containerApps@2023-05-01' = {
  name: '${envName}-app'
  location: location
  identity: { type: 'SystemAssigned' }
  properties: {
    managedEnvironmentId: caEnvironment.id
    configuration: {
      // Key Vault secret references — resolved at runtime via managed identity
      secrets: [
        {
          name: 'ai-connection-string'
          keyVaultUrl: '${keyVault.properties.vaultUri}secrets/appinsights-connection-string'
          identity: 'system'
        }
      ]
      registries: [
        {
          server: acr.properties.loginServer
          identity: 'system'
        }
      ]
      ingress: null  // No HTTP ingress — CLI-only access via az containerapp exec
    }
    template: {
      containers: [
        {
          name: 'migration-agent'
          image: '${acr.properties.loginServer}/${envName}:${imageTag}'
          resources: {
            cpu: json('1.0')
            memory: '2Gi'
          }
          env: [
            {
              name: 'AZURE_KEYVAULT_URL'
              value: keyVault.properties.vaultUri
            }
            {
              // Security [CRITICAL]: App Insights string from Key Vault — never plaintext
              name: 'APPLICATIONINSIGHTS_CONNECTION_STRING'
              secretRef: 'ai-connection-string'
            }
            {
              name: 'LOG_LEVEL'
              value: 'INFO'
            }
          ]
          volumeMounts: [
            {
              // Security [MEDIUM]: Persistent volume prevents state loss on container restart
              volumeName: 'migration-output'
              mountPath: '/app/output'
            }
          ]
          probes: [
            {
              type: 'Liveness'
              exec: {
                command: [ 'python3', '-c', 'import sys; sys.exit(0)' ]
              }
              initialDelaySeconds: 10
              periodSeconds: 30
              failureThreshold: 3
            }
          ]
        }
      ]
      volumes: [
        {
          name: 'migration-output'
          storageType: 'AzureFile'
          storageName: 'migration-output'
        }
      ]
      scale: {
        minReplicas: 0
        maxReplicas: 1  // Enforces single instance — prevents concurrent ETL runs
      }
    }
  }
  dependsOn: [ caEnvStorage ]
}

// ── Role Assignments ────────────────────────────────────────────────────────
// Security [HIGH]: Least privilege — each role grants minimum required access.

// Key Vault Secrets User — read secrets only
resource kvRoleAssignment 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(keyVault.id, containerApp.id, 'kv-secrets-user')
  scope: keyVault
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', '4633458b-17de-408a-b874-0445c86b69e6')
    principalId: containerApp.identity.principalId
    principalType: 'ServicePrincipal'
  }
}

// AcrPull — pull images from ACR
// Security [HIGH]: Managed identity pulls images — no admin credential required
resource acrPullRoleAssignment 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(acr.id, containerApp.id, 'acr-pull')
  scope: acr
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', '7f951dda-4ed3-4680-a7ca-43fe172d538d')
    principalId: containerApp.identity.principalId
    principalType: 'ServicePrincipal'
  }
}

// Storage Blob Data Contributor — read/write audit log archive
resource storageBlobRoleAssignment 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(storage.id, containerApp.id, 'storage-blob-contrib')
  scope: storage
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', 'ba92f5b4-2d11-453d-a403-e96b0029c9fe')
    principalId: containerApp.identity.principalId
    principalType: 'ServicePrincipal'
  }
}

// NOTE: SQL DB role (db_datareader + db_datawriter) must be granted via T-SQL
// after deployment — cannot be assigned through ARM/Bicep.
// Run in P0 setup: EXEC sp_addrolemember 'db_datawriter', '<managed-identity-name>'
// See runbooks/P0_environment_setup.md — Step 3a.

// ── Container App diagnostic settings ──────────────────────────────────────
resource caDiag 'Microsoft.Insights/diagnosticSettings@2021-05-01-preview' = {
  name: 'ca-diag'
  scope: caEnvironment
  properties: {
    workspaceId: logAnalytics.id
    logs: [
      { category: 'ContainerAppConsoleLogs', enabled: true, retentionPolicy: { enabled: true, days: logRetentionDays } }
      { category: 'ContainerAppSystemLogs', enabled: true, retentionPolicy: { enabled: true, days: logRetentionDays } }
    ]
    metrics: [
      { category: 'AllMetrics', enabled: true, retentionPolicy: { enabled: true, days: logRetentionDays } }
    ]
  }
}

// ── Dashboard Storage Account ───────────────────────────────────────────────
// Separate public-read storage for stakeholder dashboard blob.
// Migration data (state, audit logs) stays in the private VNet-locked storage account above.
// This account only contains sanitised progress stats — no credentials or raw data.

resource dashStore 'Microsoft.Storage/storageAccounts@2023-01-01' = {
  name: '${replace(envName, '-', '')}dash'
  location: location
  sku: { name: 'Standard_LRS' }
  kind: 'StorageV2'
  properties: {
    allowBlobPublicAccess: true          // Required: dashboard blob is publicly readable
    minimumTlsVersion: 'TLS1_2'
    supportsHttpsTrafficOnly: true
    // Note: no network ACL restrictions — this account serves public stakeholder traffic
  }
}

resource dashBlobService 'Microsoft.Storage/storageAccounts/blobServices@2023-01-01' = {
  parent: dashStore
  name: 'default'
  properties: {
    cors: {
      corsRules: [
        {
          allowedOrigins: ['*']          // Allow any origin to fetch status.json in browser
          allowedMethods: ['GET', 'HEAD', 'OPTIONS']
          allowedHeaders: ['*']
          exposedHeaders: ['*']
          maxAgeInSeconds: 60
        }
      ]
    }
  }
}

resource dashContainer 'Microsoft.Storage/storageAccounts/blobServices/containers@2023-01-01' = {
  parent: dashBlobService
  name: 'dashboard'
  properties: {
    publicAccess: 'Blob'                 // Anonymous read on individual blobs (not container list)
  }
}

// Grant Container App managed identity write access to push status.json
resource dashStoreRole 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(dashStore.id, containerApp.id, 'storage-blob-data-contributor')
  scope: dashStore
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', 'ba92f5b4-2d11-453d-a403-e96b0029c9fe') // Storage Blob Data Contributor
    principalId: containerApp.identity.principalId
    principalType: 'ServicePrincipal'
  }
}

// ── Outputs ─────────────────────────────────────────────────────────────────
output acrLoginServer string = acr.properties.loginServer
output keyVaultUri string = keyVault.properties.vaultUri
output containerAppName string = containerApp.name
output sqlServerFqdn string = sqlServer.properties.fullyQualifiedDomainName
output logAnalyticsWorkspaceId string = logAnalytics.id
output vnetId string = vnet.id
output dashboardUrl string = 'https://${dashStore.properties.primaryEndpoints.blob}dashboard/status.json'

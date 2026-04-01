# Network Isolation Architecture
## CyberArk → KeeperPAM Migration | SHIFT System

**Document ID:** SEC-NET-001
**Last Updated:** 2026-03-30
**Owner:** Migration Infrastructure Lead
**Applies To:** Azure deployment of the SHIFT migration platform

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────────┐
│  ON-PREMISES                                                            │
│                                                                         │
│  ┌──────────────────┐    ┌───────────────────┐                         │
│  │  CyberArk PVWA   │    │  Source Systems   │                         │
│  │  (on-prem)       │    │  (AD, Unix, DB)   │                         │
│  └────────┬─────────┘    └────────┬──────────┘                         │
│           │ :443 HTTPS            │                                     │
└───────────┼───────────────────────┼─────────────────────────────────────┘
            │                       │
            │  VPN Gateway or ExpressRoute (private, encrypted)
            │
┌───────────┼───────────────────────────────────────────────────────────────┐
│  AZURE VNET  (10.10.0.0/16)                                               │
│                                                                           │
│  ┌────────────────────────────────────────────────────────────────────┐   │
│  │  Container Apps Subnet  10.10.0.0/23                               │   │
│  │  (delegated: Microsoft.App/environments)                           │   │
│  │                                                                     │   │
│  │  ┌──────────────────────────────────────────────────────────────┐  │   │
│  │  │  Container App Environment                                   │  │   │
│  │  │                                                               │  │   │
│  │  │  ┌────────────────────────────────┐                          │  │   │
│  │  │  │  shift-migration-app           │                          │  │   │
│  │  │  │  (Container App, maxReplicas=1)│                          │  │   │
│  │  │  │                                │                          │  │   │
│  │  │  │  Managed Identity ────────────────────────────────────┐  │  │   │
│  │  │  └────────────────────────────────┘                      │  │  │   │
│  │  └──────────────────────────────────────────────────────────┼──┘  │   │
│  └──────────────────────────────────────────────────────────────┼─────┘   │
│                                                                  │         │
│  ┌────────────────────────────────────────────────────────────── ┼ ──────┐  │
│  │  Private Endpoint Subnet  10.10.2.0/24                        │      │  │
│  │                                                                │      │  │
│  │  ┌─────────────────────────┐  ┌──────────────────────────┐   │      │  │
│  │  │  Private Endpoint       │  │  Private Endpoint        │   │      │  │
│  │  │  Key Vault              │  │  Azure SQL               │   │      │  │
│  │  │  10.10.2.4              │  │  10.10.2.5               │   │      │  │
│  │  └────────────┬────────────┘  └────────────┬─────────────┘   │      │  │
│  └───────────────┼────────────────────────────┼─────────────────┼──────┘  │
│                  │                            │                  │         │
│  ┌───────────────┼────────────────────────────┼─────────────────┼──────┐  │
│  │  Private DNS Zones (linked to VNet)        │                  │      │  │
│  │                                            │                  │      │  │
│  │  privatelink.vaultcore.azure.net ──────────┘                  │      │  │
│  │  privatelink.database.windows.net ────────────────────────────┘      │  │
│  └───────────────────────────────────────────────────────────────────────┘  │
│                                                                              │
│  ┌──────────────────────────┐  ┌────────────────────────────────┐           │
│  │  Azure Key Vault         │  │  Azure SQL Database            │           │
│  │  (public access: DISABLED│  │  (public access: DISABLED)     │           │
│  └──────────────────────────┘  └────────────────────────────────┘           │
│                                                                              │
└──────────────────────────────────────────────────────────────────────────────┘
            │
            │  HTTPS :443 outbound (egress)
            │
┌───────────┴─────────────────────────────────┐
│  EXTERNAL SERVICES                          │
│                                             │
│  KeeperPAM Cloud API  (api.keepersecurity.com) │
│  Azure Container Registry  (ACR)            │
│  Azure Monitor / App Insights               │
└─────────────────────────────────────────────┘
```

---

## VNet Design

### Address Space

| Parameter | Value | Notes |
|-----------|-------|-------|
| VNet address space | `10.10.0.0/16` | Adjust to avoid overlap with on-prem CIDR |
| Container Apps subnet | `10.10.0.0/23` | /23 minimum required by Azure Container Apps |
| Private endpoint subnet | `10.10.2.0/24` | /24 recommended; no delegation required |
| VPN Gateway subnet | `10.10.3.0/27` | `GatewaySubnet` — reserved name, no NSG |

> **Important:** The Container Apps subnet must NOT overlap with the on-prem network. Coordinate with the client network team before deployment. Common on-prem ranges to avoid: `10.0.0.0/8`, `192.168.0.0/16`, `172.16.0.0/12`.

### Subnet Delegation

The Container Apps subnet requires delegation to `Microsoft.App/environments`. This is enforced in `main.bicep`:

```bicep
resource caSubnet 'Microsoft.Network/virtualNetworks/subnets@2023-09-01' = {
  name: 'container-apps-subnet'
  properties: {
    addressPrefix: '10.10.0.0/23'
    delegations: [
      {
        name: 'Microsoft.App.environments'
        properties: { serviceName: 'Microsoft.App/environments' }
      }
    ]
  }
}
```

> Note: A delegated subnet cannot be used for other resource types. Do not place private endpoints or VPN gateways in the Container Apps subnet.

---

## Private Endpoints

### Key Vault Private Endpoint

**DNS Zone:** `privatelink.vaultcore.azure.net`

```bicep
resource kvPrivateEndpoint 'Microsoft.Network/privateEndpoints@2023-09-01' = {
  name: 'pe-keyvault'
  location: location
  properties: {
    subnet: { id: peSubnet.id }
    privateLinkServiceConnections: [
      {
        name: 'kv-connection'
        properties: {
          privateLinkServiceId: keyVault.id
          groupIds: ['vault']
        }
      }
    ]
  }
}
```

### Azure SQL Private Endpoint

**DNS Zone:** `privatelink.database.windows.net`

```bicep
resource sqlPrivateEndpoint 'Microsoft.Network/privateEndpoints@2023-09-01' = {
  name: 'pe-sql'
  location: location
  properties: {
    subnet: { id: peSubnet.id }
    privateLinkServiceConnections: [
      {
        name: 'sql-connection'
        properties: {
          privateLinkServiceId: sqlServer.id
          groupIds: ['sqlServer']
        }
      }
    ]
  }
}
```

---

## Private DNS Zones Setup

Both private DNS zones must be created and linked to the VNet. Without this, the Container App will resolve the public IP of Key Vault and SQL, and connections will fail because public access is disabled.

```bash
# Create Key Vault private DNS zone
az network private-dns zone create \
  --resource-group <rg-name> \
  --name privatelink.vaultcore.azure.net

# Link to VNet
az network private-dns link vnet create \
  --resource-group <rg-name> \
  --zone-name privatelink.vaultcore.azure.net \
  --name kv-dns-link \
  --virtual-network <vnet-name> \
  --registration-enabled false

# Create DNS record group for Key Vault private endpoint
az network private-endpoint dns-zone-group create \
  --resource-group <rg-name> \
  --endpoint-name pe-keyvault \
  --name kv-dns-zone-group \
  --private-dns-zone privatelink.vaultcore.azure.net \
  --zone-name vault

# Repeat for SQL
az network private-dns zone create \
  --resource-group <rg-name> \
  --name privatelink.database.windows.net

az network private-dns link vnet create \
  --resource-group <rg-name> \
  --zone-name privatelink.database.windows.net \
  --name sql-dns-link \
  --virtual-network <vnet-name> \
  --registration-enabled false

az network private-endpoint dns-zone-group create \
  --resource-group <rg-name> \
  --endpoint-name pe-sql \
  --name sql-dns-zone-group \
  --private-dns-zone privatelink.database.windows.net \
  --zone-name sqlServer
```

**Verification:**

```bash
# From within the Container App, verify private IP resolution
az containerapp exec \
  --name shift-migration-app \
  --resource-group <rg-name> \
  --command "nslookup <keyvault-name>.vault.azure.net"
# Expected: resolves to 10.10.2.4 (private IP), NOT a public IP
```

---

## On-Premises Connectivity

### Decision Matrix: VPN Gateway vs ExpressRoute

| Criteria | VPN Gateway | ExpressRoute |
|----------|-------------|--------------|
| Cost | ~$140-$280/month (VpnGw1-VpnGw2) | $55-$1,500+/month depending on circuit |
| Bandwidth | Up to 1 Gbps | Up to 10 Gbps |
| Latency | Variable (internet path) | Consistent (<10ms typical) |
| Setup time | 1-2 days | 4-12 weeks (carrier provisioning) |
| Encryption | IPsec/IKE (always on) | Optional MACsec (requires premium) |
| SLA | 99.9% | 99.95% |
| Suitable for migration? | YES — for most migration volumes | Preferred for >500k accounts or streaming logs |
| CyberArk PVWA compat. | YES | YES |

**Recommendation:** For a time-boxed migration project, VPN Gateway is sufficient unless the client has an existing ExpressRoute circuit that can be extended to the migration VNet.

### VPN Gateway Setup (if not already in place)

```bash
# Create VPN Gateway subnet (must be named GatewaySubnet)
az network vnet subnet create \
  --resource-group <rg-name> \
  --vnet-name <vnet-name> \
  --name GatewaySubnet \
  --address-prefix 10.10.3.0/27

# Create public IP for VPN Gateway
az network public-ip create \
  --resource-group <rg-name> \
  --name vpn-gateway-pip \
  --sku Standard \
  --allocation-method Static

# Create VPN Gateway (takes 25-45 minutes)
az network vnet-gateway create \
  --resource-group <rg-name> \
  --name shift-vpn-gateway \
  --vnet <vnet-name> \
  --gateway-type Vpn \
  --vpn-type RouteBased \
  --sku VpnGw1 \
  --public-ip-address vpn-gateway-pip
```

---

## NSG Rules — Container Apps Subnet

The NSG on the Container Apps subnet controls inbound and outbound traffic. Container Apps requires specific inbound rules to function.

### Required Inbound Rules (Azure Container Apps infrastructure)

| Priority | Name | Source | Destination | Port | Protocol | Action |
|----------|------|--------|-------------|------|----------|--------|
| 100 | AllowACAInfraInbound | AzureCloud | VirtualNetwork | 443 | TCP | Allow |
| 110 | AllowACAInfraUDP | AzureCloud | VirtualNetwork | 1194 | UDP | Allow |
| 120 | AllowNTP | * | VirtualNetwork | 123 | UDP | Allow |

### Outbound Rules (SHIFT-specific)

| Priority | Name | Source | Destination | Port | Protocol | Action |
|----------|------|--------|-------------|------|----------|--------|
| 100 | AllowPVWAOutbound | VirtualNetwork | `<pvwa-ip-or-cidr>` | 443 | TCP | Allow |
| 110 | AllowKeeperPAMOutbound | VirtualNetwork | `<keeperpam-api-ip>` | 443 | TCP | Allow |
| 120 | AllowAzureServicesOutbound | VirtualNetwork | AzureCloud | 443 | TCP | Allow |
| 130 | AllowPrivateEndpointsOutbound | VirtualNetwork | 10.10.2.0/24 | 1433,443 | TCP | Allow |
| 900 | DenyAllOutbound | VirtualNetwork | * | * | * | Deny |

> **Note:** Rule 120 (`AllowAzureServicesOutbound`) permits traffic to ACR, Key Vault, SQL, App Insights, and Azure Monitor over public IPs for services not covered by private endpoints. If Azure Firewall is deployed, replace this with FQDN-based rules (see Azure Firewall section below).

### Applying NSG Rules

```bash
az network nsg rule create \
  --resource-group <rg-name> \
  --nsg-name <ca-nsg-name> \
  --name AllowPVWAOutbound \
  --priority 100 \
  --direction Outbound \
  --source-address-prefixes VirtualNetwork \
  --destination-address-prefixes <pvwa-ip-or-cidr> \
  --destination-port-ranges 443 \
  --protocol Tcp \
  --access Allow
```

---

## Azure Firewall Option

### Overview

Azure Firewall provides FQDN-based egress filtering, threat intelligence, and centralised logging. It is recommended but optional for the SHIFT migration system.

**Estimated Cost:** Azure Firewall Standard ~$1.50/hour (~$1,095/month). Azure Firewall Basic ~$0.42/hour (~$306/month).

### FQDN Allow-List (replace NSG Rule 120 if Azure Firewall deployed)

```
# CyberArk PVWA (on-prem — use IP in NSG instead)
<pvwa-fqdn>

# KeeperPAM
*.keepersecurity.com
*.keepersecurity.eu  (if EU region)

# Azure services
*.azurecr.io
*.blob.core.windows.net
*.vault.azure.net
*.database.windows.net
*.monitor.azure.com
*.applicationinsights.azure.com
dc.applicationinsights.azure.com
*.ods.opinsights.azure.com
*.oms.opinsights.azure.com
management.azure.com

# OS updates (if container needs to pull updates)
*.ubuntu.com
*.debian.org
```

### NSG vs Azure Firewall Decision

| Consideration | NSG Only | Azure Firewall |
|---------------|----------|----------------|
| Cost | $0 | ~$300-$1,095/month |
| FQDN filtering | No | Yes |
| Threat intelligence | No | Yes (Standard SKU) |
| Centralised logging | No (NSG flow logs only) | Yes (structured FQDN logs) |
| Setup complexity | Low | Medium |
| Recommendation | Short-term migration (<6 months) | Long-term or security-critical |

---

## Testing Connectivity from Container App

### Test PVWA reachability

```bash
az containerapp exec \
  --name shift-migration-app \
  --resource-group <rg-name> \
  --command "python3 -c \"
import urllib.request, ssl
ctx = ssl.create_default_context()
req = urllib.request.Request('https://<pvwa-fqdn>/PasswordVault/api/auth/cyberark/logon')
try:
    urllib.request.urlopen(req, timeout=10, context=ctx)
except Exception as e:
    print('Reachable (got response):', type(e).__name__)
\""
```

Expected: `Reachable (got response): HTTPError` (401 Unauthorized is expected — it means the endpoint is reachable)

### Test Key Vault private endpoint resolution

```bash
az containerapp exec \
  --name shift-migration-app \
  --resource-group <rg-name> \
  --command "python3 -c \"
import socket
ip = socket.gethostbyname('<keyvault-name>.vault.azure.net')
print('Resolved to:', ip)
assert ip.startswith('10.10.'), f'Expected private IP, got {ip}'
print('Private endpoint confirmed')
\""
```

### Run full connectivity preflight

```bash
az containerapp exec \
  --name shift-migration-app \
  --resource-group <rg-name> \
  --command "python3 cli.py preflight"
```

The preflight checks CyberArk connectivity, KeeperPAM OAuth2 authentication, Key Vault secret retrieval, SQL connectivity, and output volume mount.

---

*End of Network Isolation Architecture*

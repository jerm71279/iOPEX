# CyberArk to Secret Server API Mapping

Complete reference for converting CyberArk CCP/AAM API calls to Delinea Secret Server equivalents.

## Authentication

| Aspect | CyberArk CCP | Secret Server |
|--------|--------------|---------------|
| Method | AppID + IP allowlist | OAuth2 client credentials |
| Header | None (IP-based) | `Authorization: Bearer {token}` |
| Token Endpoint | N/A | `POST /oauth2/token` |
| Token Lifetime | N/A | Configurable (default 3600s) |

### CyberArk (No Auth Header)
```
GET /AIMWebService/api/Accounts?AppID=MyApp&Safe=MySafe&Object=MyAccount
```

### Secret Server (OAuth2)
```bash
# Step 1: Get token
POST /oauth2/token
Content-Type: application/x-www-form-urlencoded

grant_type=client_credentials&client_id={id}&client_secret={secret}

# Step 2: Use token
GET /api/v1/secrets/{id}/fields/password
Authorization: Bearer {access_token}
```

## Core Operations

### Retrieve Password

| CyberArk | Secret Server |
|----------|---------------|
| `GET /AIMWebService/api/Accounts?AppID=X&Safe=Y&Object=Z` | `GET /api/v1/secrets/{id}/fields/password` |

**CyberArk Response:**
```json
{
  "Content": "P@ssw0rd123",
  "UserName": "admin",
  "Address": "server01.domain.com",
  "Safe": "MySafe",
  "Name": "MyAccount"
}
```

**Secret Server Response:**
```json
{
  "itemId": 12345,
  "fieldId": 108,
  "fieldName": "password",
  "slug": "password",
  "value": "P@ssw0rd123"
}
```

### Retrieve Full Secret

| CyberArk | Secret Server |
|----------|---------------|
| Same as above (returns all fields) | `GET /api/v1/secrets/{id}` |

**Secret Server Full Secret Response:**
```json
{
  "id": 1234,
  "name": "server01-admin",
  "folderId": 56,
  "templateId": 6001,
  "items": [
    {"fieldName": "Machine", "itemValue": "server01.domain.com"},
    {"fieldName": "Username", "itemValue": "admin"},
    {"fieldName": "Password", "itemValue": "P@ssw0rd123"}
  ]
}
```

### Search for Secret

| CyberArk | Secret Server |
|----------|---------------|
| Query by Safe+Object | `GET /api/v1/secrets?filter.searchText={text}` |

**Secret Server Search:**
```
GET /api/v1/secrets?filter.searchText=server01&filter.folderId=56
```

## Parameter Mapping

| CyberArk Parameter | Secret Server Parameter | Notes |
|-------------------|------------------------|-------|
| `AppID` | OAuth2 `client_id` | Different auth model |
| `Safe` | `folderId` or folder path | Requires ID lookup |
| `Object` | `secretId` | Requires ID lookup |
| `UserName` (filter) | `filter.searchText` | Less precise |
| `Address` (filter) | `filter.searchText` | Less precise |
| `Reason` | `comment` (in request body) | For auditing |

## Lookup Strategies

Since CyberArk uses Safe+Object names but Secret Server uses numeric IDs, you need a lookup strategy:

### Option 1: Pre-Migration Mapping File
```json
{
  "mappings": [
    {
      "cyberark_safe": "MySafe",
      "cyberark_object": "server01-admin",
      "secret_server_id": 1234
    }
  ]
}
```

### Option 2: Runtime Search (Slower)
```python
# Search by name, then get by ID
results = search_secrets(f"{safe}-{object}")
secret_id = results[0]["id"]
password = get_password(secret_id)
```

### Option 3: Naming Convention
Store Secret Server ID in secret name: `1234_server01-admin`

## Error Code Mapping

| CyberArk Error | Secret Server Equivalent | Meaning |
|----------------|-------------------------|---------|
| `APPAP004E` | 401 Unauthorized | Invalid credentials |
| `APPAP005E` | 403 Forbidden | Insufficient permissions |
| `APPAP006E` | 404 Not Found | Secret doesn't exist |
| `APPAP007E` | 404 Not Found | Safe doesn't exist |
| `ITATS006E` | 403 Forbidden | Account locked |
| `PASWS027E` | 404 Not Found | Safe not found |

## SDK Equivalents

### .NET

| CyberArk | Secret Server |
|----------|---------------|
| `CyberArk.AIM.PasswordSDK` | `Thycotic.SecretServer.SDK` |
| `new PasswordRequest()` | `new SecretServerClient()` |
| `passwordSDK.GetPassword()` | `client.GetSecret(id)` |

### PowerShell

| CyberArk (psPAS) | Secret Server (Thycotic.SecretServer) |
|------------------|--------------------------------------|
| `New-PASSession` | `New-TssSession` |
| `Get-PASAccount` | `Search-TssSecret` |
| `Get-PASAccountPassword` | `Get-TssSecret` + field access |

### Python

| CyberArk | Secret Server |
|----------|---------------|
| `requests.get(ccp_url, params={...})` | `requests.get(ss_url, headers={auth})` |
| Response: `json["Content"]` | Response: `json["value"]` |

## Request/Response Examples

### Python: CyberArk to Secret Server

**Before (CyberArk):**
```python
response = requests.get(
    "https://cyberark/AIMWebService/api/Accounts",
    params={
        "AppID": "MyApp",
        "Safe": "MySafe",
        "Object": "server01-admin"
    }
)
password = response.json()["Content"]
```

**After (Secret Server):**
```python
# Get token first
token_response = requests.post(
    "https://secretserver/oauth2/token",
    data={
        "grant_type": "client_credentials",
        "client_id": client_id,
        "client_secret": client_secret
    }
)
token = token_response.json()["access_token"]

# Get password
response = requests.get(
    f"https://secretserver/api/v1/secrets/{secret_id}/fields/password",
    headers={"Authorization": f"Bearer {token}"}
)
password = response.json()["value"]
```

### PowerShell: CyberArk to Secret Server

**Before (psPAS):**
```powershell
New-PASSession -BaseURI $cyberArkUrl -Credential $cred -Type LDAP
$password = Get-PASAccountPassword -AccountID $accountId -Reason "App access"
```

**After (Thycotic.SecretServer):**
```powershell
$session = New-TssSession -SecretServer $ssUrl -Credential $cred
$secret = Get-TssSecret -TssSession $session -Id $secretId
$password = $secret.GetFieldValue("password")
```

## Migration Checklist per Application

- [ ] Identify all CyberArk API calls in codebase
- [ ] Map CyberArk Safe+Object to Secret Server Secret ID
- [ ] Update authentication (add OAuth2 token handling)
- [ ] Update API endpoint URLs
- [ ] Update response parsing (Content → value)
- [ ] Update error handling for new error codes
- [ ] Test in non-production environment
- [ ] Coordinate maintenance window for production cutover
- [ ] Have rollback plan ready

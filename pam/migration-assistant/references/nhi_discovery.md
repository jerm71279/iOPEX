# Non-Human Identity (NHI) Discovery Guide

## What Are NHIs?

Non-Human Identities are credentials used by applications, services, and automated processes rather than humans. They are the highest-risk accounts in PAM migrations because:

1. **Undocumented dependencies** - No one knows all the places they're used
2. **24/7 usage** - Breaking them causes immediate outages
3. **Hardcoded references** - Often embedded in code, configs, scripts
4. **No human to ask** - Can't send an email saying "please update your password"

## NHI Categories

| Category | Examples | Risk Level | Discovery Method |
|----------|----------|------------|-----------------|
| **Service Accounts** | Windows services, Linux daemons | HIGH | Audit logs, service configs |
| **Application Credentials (CCP/AAM)** | Apps calling CyberArk API | CRITICAL | CCP audit logs |
| **Scheduled Tasks** | Batch jobs, cron jobs | HIGH | Task scheduler, crontab |
| **Database Connections** | Connection strings | HIGH | App configs, connection pools |
| **API Keys** | REST API authentication | MEDIUM | Code scanning |
| **DevOps Credentials** | CI/CD pipelines | HIGH | Pipeline configs |
| **Machine Identities** | Certificates, SSH keys | MEDIUM | Certificate stores |

## Discovery Methods

### 1. CyberArk Audit Log Analysis

The best way to identify NHIs is by analyzing CyberArk access patterns:

```powershell
# Get all account activity
$accounts = Get-PASAccount
$nhiCandidates = @()

foreach ($account in $accounts) {
    $activity = Get-PASAccountActivity -AccountID $account.id -Limit 500
    
    # Look for programmatic access patterns
    $programmaticAccess = $activity | Where-Object {
        # CCP/AAM access
        $_.PerformedBy -like "*CCP*" -or
        $_.PerformedBy -like "*AAM*" -or
        $_.PerformedBy -like "*AppUser*" -or
        
        # Non-PVWA client
        $_.ClientApp -ne "PVWA" -or
        
        # High frequency access (more than 10/day)
        $_.Action -eq "Retrieve Password"
    }
    
    if ($programmaticAccess.Count -gt 10) {
        $nhiCandidates += [PSCustomObject]@{
            AccountId = $account.id
            AccountName = $account.name
            Safe = $account.safeName
            AccessCount = $programmaticAccess.Count
            AccessPatterns = ($programmaticAccess.PerformedBy | Select-Object -Unique) -join ", "
            LastAccess = ($programmaticAccess | Sort-Object Date -Descending)[0].Date
        }
    }
}

$nhiCandidates | Export-Csv "NHI_Candidates.csv" -NoTypeInformation
```

### 2. CCP/AAM Application Inventory

Query CyberArk for registered CCP applications:

```powershell
# Get CCP application details
$ccpApps = Get-PASApplication
$ccpApps | Select-Object AppID, Description, Location, AccessPermittedFrom | 
    Export-Csv "CCP_Applications.csv" -NoTypeInformation
```

### 3. Code Scanning

Use the `ccp_code_scanner.py` script to find CyberArk references in code:

```bash
python ccp_code_scanner.py /path/to/codebase --output nhi_code_scan.json
```

### 4. Service Account Identification

**Windows:**
```powershell
# Find services using specific accounts
Get-WmiObject Win32_Service | 
    Where-Object { $_.StartName -notlike "LocalSystem" -and 
                   $_.StartName -notlike "NT AUTHORITY*" } |
    Select-Object Name, StartName, State |
    Export-Csv "Service_Accounts.csv" -NoTypeInformation
```

**Linux:**
```bash
# Find processes running as non-root users
ps aux | awk '$1 != "root" {print $1, $11}' | sort | uniq -c | sort -rn
```

### 5. Scheduled Task Analysis

**Windows:**
```powershell
Get-ScheduledTask | 
    Where-Object { $_.Principal.UserId -notlike "SYSTEM" } |
    Select-Object TaskName, @{N='RunAs';E={$_.Principal.UserId}} |
    Export-Csv "Scheduled_Tasks.csv" -NoTypeInformation
```

**Linux:**
```bash
# List all crontabs
for user in $(cut -f1 -d: /etc/passwd); do 
    crontab -u $user -l 2>/dev/null | grep -v "^#"
done
```

## NHI Classification Matrix

After discovery, classify each NHI:

| Classification | Criteria | Migration Priority | Approach |
|---------------|----------|-------------------|----------|
| **Critical CCP** | Active CCP/AAM integration | Wave 5 (Last) | Coordinate with app team |
| **High-Frequency Service** | >100 accesses/day | Wave 4 | Maintenance window required |
| **Scheduled Task** | Runs on schedule | Wave 4 | Update task credentials |
| **Low-Frequency Service** | <10 accesses/day | Wave 3 | Standard migration |
| **Dormant** | No access in 90+ days | Wave 2 | Validate still needed |

## NHI Documentation Template

For each identified NHI, document:

```markdown
## NHI: {account_name}

### Identity
- CyberArk Account ID: {id}
- CyberArk Safe: {safe}
- Platform: {platform}
- Username: {username}
- Target System: {address}

### Usage Profile
- Access Frequency: {count}/day
- Access Pattern: {CCP/Service/Task/etc}
- Last Accessed: {date}
- Accessed By: {application/service names}

### Dependencies
- Application(s): {list of apps using this credential}
- Service(s): {list of Windows/Linux services}
- Scheduled Task(s): {list of tasks}
- Code Location(s): {paths to code files}

### Application Owner
- Name: {owner name}
- Email: {owner email}
- Team: {team name}

### Migration Plan
- Secret Server Secret ID: {id after migration}
- Migration Wave: {1-5}
- Maintenance Window Required: {Yes/No}
- Cutover Date: {planned date}
- Rollback Plan: {description}

### Validation
- [ ] Credential migrated to Secret Server
- [ ] Application code updated (if CCP)
- [ ] Service credential updated (if service)
- [ ] Task credential updated (if scheduled task)
- [ ] Tested in non-production
- [ ] Production cutover complete
- [ ] Monitoring confirmed working
```

## Risk Assessment

Score each NHI for migration risk:

| Factor | Low (1) | Medium (2) | High (3) |
|--------|---------|------------|----------|
| Access Frequency | <10/day | 10-100/day | >100/day |
| Business Criticality | Dev/Test | Internal app | Customer-facing |
| Documentation | Well documented | Partially known | Unknown |
| Owner Availability | Available | Busy but responsive | Unknown/departed |
| Code Changes Required | None | Config only | Code changes |

**Risk Score = Sum of factors**
- 5-8: Low risk - Standard migration
- 9-12: Medium risk - Extra validation
- 13-15: High risk - Dedicated cutover window

## Common NHI Patterns

### Pattern 1: CCP Web Application
```
App Server → CyberArk CCP → Vault
                  ↓
           Password returned
                  ↓
           App connects to DB
```

**Migration:** Update app code to call Secret Server API

### Pattern 2: Windows Service
```
Windows Service → Stored credential → Target system
```

**Migration:** Update service "Log On As" after Secret Server migration

### Pattern 3: Scheduled Task
```
Task Scheduler → Runs as service account → Accesses resources
```

**Migration:** Update task credentials in Task Scheduler

### Pattern 4: CI/CD Pipeline
```
Jenkins/Azure DevOps → Retrieves credential → Deploys to servers
```

**Migration:** Update pipeline secrets configuration

## Cutover Checklist per NHI

- [ ] NHI documented in inventory
- [ ] Application owner identified and notified
- [ ] Credential migrated to Secret Server
- [ ] Secret Server Secret ID mapped to CyberArk reference
- [ ] Maintenance window scheduled (if needed)
- [ ] Code/config changes prepared
- [ ] Rollback plan documented
- [ ] Non-production test complete
- [ ] Production cutover executed
- [ ] Post-cutover validation (access working)
- [ ] Monitoring confirmed (no errors)
- [ ] CyberArk credential marked for decommission

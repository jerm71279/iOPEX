# CyberArk to Secret Server Permission Matrix

> **IMPORTANT CORRECTION**: The "22→4" narrative only describes **folder-level** permissions.
> Secret Server has **200+ granular role-level permissions** at the system level, which are
> MORE granular than CyberArk's 22 safe permissions. The 4-tier folder permissions
> (Owner, Edit, Add Secret, View) are just one layer of SS's permission model.


## Overview

CyberArk has ~15 granular Safe-level permissions. Secret Server uses a simpler role-based model with 4 primary roles. This matrix documents the translation and what granularity is lost.

## Permission Translation

| CyberArk Permission | Description | Secret Server Role | Notes |
|--------------------|--------------|--------------------|-------|
| `ListAccounts` | See account names in Safe | **List** | Direct mapping |
| `UseAccounts` | Connect via PSM (no password view) | **View** | SS doesn't separate connect vs view |
| `RetrieveAccounts` | View/copy passwords | **View** | Combined with UseAccounts |
| `AddAccounts` | Create new accounts | **Edit** | Combined with update/delete |
| `UpdateAccountContent` | Change passwords manually | **Edit** | Direct mapping |
| `UpdateAccountProperties` | Modify account metadata | **Edit** | Direct mapping |
| `DeleteAccounts` | Remove accounts | **Edit** | Cannot separate add from delete |
| `RenameAccounts` | Change account names | **Edit** | Part of Edit role |
| `UnlockAccounts` | Unlock locked accounts | **Edit** | Part of Edit role |
| `InitiateCPMAccountManagementOperations` | Trigger verify/change/reconcile | **View** + RPC permission | May need custom role |
| `SpecifyNextAccountContent` | Set next password for CPM | **Edit** | Part of Edit role |
| `ManageSafe` | Update Safe properties | **Owner** | Full admin access |
| `ManageSafeMembers` | Add/remove Safe members | **Owner** | Full admin access |
| `BackupSafe` | Backup Safe contents | **Owner** | Part of Owner role |
| `ViewAuditLog` | View Safe audit logs | **List** + Audit | May need additional role |
| `ViewSafeMembers` | See Safe membership | **List** | Direct mapping |
| `AccessWithoutConfirmation` | Bypass dual control | N/A | Configure in Secret policy |
| `CreateFolders` | Create folders in Safe | **Edit** | Part of Edit role |
| `DeleteFolders` | Delete folders in Safe | **Edit** | Part of Edit role |
| `MoveAccountsAndFolders` | Move items between folders | **Edit** | Part of Edit role |

## Secret Server Roles Summary

| Role | Permissions |
|------|-------------|
| **List** | View secret names, basic metadata |
| **View** | List + view secret values (passwords) |
| **Edit** | View + create, modify, delete secrets |
| **Owner** | Edit + manage folder permissions, settings |

## What's Lost in Translation

### 1. UseAccounts vs RetrieveAccounts Separation
**CyberArk:** Can allow PSM connection without showing password
**Secret Server:** View permission includes both
**Workaround:** Use Session Recording / Launcher without exposing password field

### 2. Add vs Delete Separation
**CyberArk:** Can grant AddAccounts without DeleteAccounts
**Secret Server:** Edit includes both
**Workaround:** None - this granularity is lost

### 3. CPM Trigger Permission
**CyberArk:** InitiateCPMAccountManagementOperations is separate
**Secret Server:** RPC permissions are separate from folder permissions
**Workaround:** Configure RPC permissions on secret template

### 4. Dual Control / Approval Workflows
**CyberArk:** AccessWithoutConfirmation permission
**Secret Server:** Configure in Secret Policy with approval workflow
**Workaround:** Enable "Require Approval" in Secret Policy

## Translation Decision Matrix

Use this to determine target Secret Server role:

```
Has ManageSafe AND ManageSafeMembers?
  └─ YES → Owner
  └─ NO ↓

Has AddAccounts OR UpdateAccountContent OR DeleteAccounts?
  └─ YES → Edit
  └─ NO ↓

Has RetrieveAccounts OR UseAccounts?
  └─ YES → View
  └─ NO ↓

Has ListAccounts?
  └─ YES → List
  └─ NO → No access (remove from folder)
```

## PowerShell Translation Function

```powershell
function Convert-CyberArkPermission {
    param(
        [Parameter(Mandatory)]
        [PSCustomObject]$SafeMember
    )
    
    # Owner: Full administrative access
    if ($SafeMember.ManageSafe -eq $true -and $SafeMember.ManageSafeMembers -eq $true) {
        return @{
            Role = "Owner"
            LostPermissions = @()
        }
    }
    
    # Edit: Can modify secrets
    if ($SafeMember.AddAccounts -eq $true -or 
        $SafeMember.UpdateAccountContent -eq $true -or
        $SafeMember.DeleteAccounts -eq $true) {
        
        $lost = @()
        if ($SafeMember.AddAccounts -eq $true -and $SafeMember.DeleteAccounts -ne $true) {
            $lost += "Add-without-delete not possible"
        }
        if ($SafeMember.DeleteAccounts -eq $true -and $SafeMember.AddAccounts -ne $true) {
            $lost += "Delete-without-add not possible"
        }
        
        return @{
            Role = "Edit"
            LostPermissions = $lost
        }
    }
    
    # View: Can see passwords
    if ($SafeMember.RetrieveAccounts -eq $true -or $SafeMember.UseAccounts -eq $true) {
        $lost = @()
        if ($SafeMember.UseAccounts -eq $true -and $SafeMember.RetrieveAccounts -ne $true) {
            $lost += "Connect-only (no password view) not possible"
        }
        
        return @{
            Role = "View"
            LostPermissions = $lost
        }
    }
    
    # List: Can see names only
    if ($SafeMember.ListAccounts -eq $true) {
        return @{
            Role = "List"
            LostPermissions = @()
        }
    }
    
    # No meaningful access
    return @{
        Role = "None"
        LostPermissions = @("User had no access permissions")
    }
}
```

## Special Cases

### CPM User Permissions
CyberArk CPM requires specific Safe membership. Secret Server equivalent:

| CyberArk CPM Permission | Secret Server Equivalent |
|------------------------|-------------------------|
| UseAccounts | View role on folder |
| RetrieveAccounts | View role on folder |
| ListAccounts | List role on folder |
| InitiateCPMAccountManagementOperations | RPC enabled on template |
| UpdateAccountContent | Edit role (or RPC only) |

### PSM User Permissions
For session recording/proxy access:

| CyberArk PSM Permission | Secret Server Equivalent |
|------------------------|-------------------------|
| UseAccounts | View + Launcher configured |
| ListAccounts | List role |

### Auditor Permissions

| CyberArk Auditor Permission | Secret Server Equivalent |
|----------------------------|-------------------------|
| ListAccounts | List role |
| ViewAuditLog | "View Secret Audit" permission |
| ViewSafeMembers | List role (members visible) |

## Stakeholder Approval Template

Before migration, get approval for permission translations:

```markdown
## Permission Translation Approval

Safe: {safe_name}
Date: {date}

| User/Group | CyberArk Permissions | Proposed SS Role | Lost Granularity |
|------------|---------------------|------------------|------------------|
| {member1} | {perms} | {role} | {lost} |
| {member2} | {perms} | {role} | {lost} |

### Acknowledged Limitations:
- [ ] Add-only vs add+delete separation is lost
- [ ] Connect-only (UseAccounts) vs view password is lost
- [ ] CPM trigger permission handled via RPC settings

Approved by: _______________
Date: _______________
```

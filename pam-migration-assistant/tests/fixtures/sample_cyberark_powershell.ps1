# Sample CyberArk Integration - PowerShell
# Used for testing ccp_code_scanner.py pattern detection.
#
# This file contains intentional CyberArk patterns that should be detected.

# Pattern: POWERSHELL_PSPAS - psPAS module import
Import-Module psPAS

# Pattern: CCP_APPID
$AppID = "PowerShellApp"

# Pattern: CCP_SAFE_REFERENCE
$SafeName = "Windows-Servers"

# Pattern: CCP_OBJECT_REFERENCE
$ObjectName = "domain-admin"

# Pattern: CONFIG_CYBERARK_URL
$CyberArkURL = "https://cyberark.company.com"
$pvwa_url = "https://pvwa.company.com/PasswordVault"

# Pattern: POWERSHELL_PSPAS - New-PASSession
function Connect-ToCyberArk {
    param(
        [string]$Credential
    )

    $session = New-PASSession -BaseURI $CyberArkURL -Credential $Credential -type LDAP
    return $session
}

# Pattern: POWERSHELL_PSPAS - Get-PASAccount
function Get-AllAccounts {
    $accounts = Get-PASAccount
    return $accounts
}

# Pattern: POWERSHELL_PSPAS - Get-PASAccountPassword
function Get-SecurePassword {
    param(
        [string]$AccountID
    )

    $password = Get-PASAccountPassword -AccountID $AccountID -Reason "Automated script access"
    return $password
}

# Combined workflow
function Get-CredentialFromVault {
    param(
        [string]$Safe,
        [string]$Object
    )

    # Connect to CyberArk
    $cred = Get-Credential
    New-PASSession -BaseURI $pvwa_url -Credential $cred

    # Find account
    $account = Get-PASAccount | Where-Object {
        $_.safeName -eq $Safe -and $_.name -eq $Object
    }

    # Get password
    if ($account) {
        return Get-PASAccountPassword -AccountID $account.id
    }

    return $null
}

# Additional patterns
$config = @{
    AppID = "ServiceApp"
    Safe = "Automation-Secrets"
    Object = "scheduled-task-account"
}

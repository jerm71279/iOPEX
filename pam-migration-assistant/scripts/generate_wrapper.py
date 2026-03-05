#!/usr/bin/env python3
"""
PAM Wrapper Generator

Generates an abstraction layer that allows applications to switch
between CyberArk and Secret Server without code changes.

The wrapper pattern enables:
- Gradual migration (switch backends per-application)
- Easy rollback (change one config value)
- Minimal application code changes

Usage:
    python generate_wrapper.py --language python --output pam_wrapper.py
"""

import argparse
import os

WRAPPER_TEMPLATES = {
    "python": '''#!/usr/bin/env python3
"""
PAM Abstraction Wrapper

This wrapper allows applications to retrieve credentials without being
tightly coupled to a specific PAM solution. During migration, the backend
can be switched via configuration without application code changes.

Configuration:
    Set environment variable PAM_BACKEND to:
    - "cyberark" : Use CyberArk CCP (legacy)
    - "secretserver" : Use Delinea Secret Server (target)
    - "both" : Try Secret Server first, fall back to CyberArk

Usage:
    from pam_wrapper import PAMClient
    
    client = PAMClient()
    password = client.get_password(
        secret_id=1234,                    # Secret Server ID
        cyberark_safe="MySafe",            # CyberArk fallback
        cyberark_object="MyAccount"        # CyberArk fallback
    )
"""

import os
import logging
from typing import Optional
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)


class PAMBackend(ABC):
    """Abstract base class for PAM backends."""
    
    @abstractmethod
    def get_password(self, **kwargs) -> str:
        """Retrieve password from PAM system."""
        pass
    
    @abstractmethod
    def test_connection(self) -> bool:
        """Test connectivity to PAM system."""
        pass


class CyberArkBackend(PAMBackend):
    """CyberArk CCP backend (legacy)."""
    
    def __init__(self):
        self.base_url = os.environ.get("CYBERARK_CCP_URL")
        self.app_id = os.environ.get("CYBERARK_APP_ID")
        
        if not self.base_url or not self.app_id:
            raise ValueError("CYBERARK_CCP_URL and CYBERARK_APP_ID environment variables required")
    
    def get_password(self, cyberark_safe: str = None, cyberark_object: str = None, **kwargs) -> str:
        """Retrieve password from CyberArk CCP."""
        import requests
        
        if not cyberark_safe or not cyberark_object:
            raise ValueError("cyberark_safe and cyberark_object required for CyberArk backend")
        
        response = requests.get(
            f"{self.base_url}/AIMWebService/api/Accounts",
            params={
                "AppID": self.app_id,
                "Safe": cyberark_safe,
                "Object": cyberark_object
            },
            verify=True,
            timeout=30
        )
        response.raise_for_status()
        return response.json()["Content"]
    
    def test_connection(self) -> bool:
        """Test CyberArk connectivity."""
        import requests
        try:
            response = requests.get(
                f"{self.base_url}/AIMWebService/api/",
                timeout=10
            )
            return response.status_code < 500
        except Exception:
            return False


class SecretServerBackend(PAMBackend):
    """Delinea Secret Server backend (target)."""
    
    def __init__(self):
        self.base_url = os.environ.get("SECRET_SERVER_URL")
        self.client_id = os.environ.get("SECRET_SERVER_CLIENT_ID")
        self.client_secret = os.environ.get("SECRET_SERVER_CLIENT_SECRET")
        
        if not all([self.base_url, self.client_id, self.client_secret]):
            raise ValueError(
                "SECRET_SERVER_URL, SECRET_SERVER_CLIENT_ID, and "
                "SECRET_SERVER_CLIENT_SECRET environment variables required"
            )
        
        self._token = None
        self._token_expiry = 0
    
    def _get_token(self) -> str:
        """Get OAuth2 access token."""
        import requests
        import time
        
        if self._token and time.time() < self._token_expiry - 60:
            return self._token
        
        response = requests.post(
            f"{self.base_url}/oauth2/token",
            data={
                "grant_type": "client_credentials",
                "client_id": self.client_id,
                "client_secret": self.client_secret
            },
            timeout=30
        )
        response.raise_for_status()
        data = response.json()
        
        self._token = data["access_token"]
        self._token_expiry = time.time() + data.get("expires_in", 3600)
        return self._token
    
    def get_password(self, secret_id: int = None, **kwargs) -> str:
        """Retrieve password from Secret Server."""
        import requests
        
        if not secret_id:
            raise ValueError("secret_id required for Secret Server backend")
        
        response = requests.get(
            f"{self.base_url}/api/v1/secrets/{secret_id}/fields/password",
            headers={"Authorization": f"Bearer {self._get_token()}"},
            timeout=30
        )
        response.raise_for_status()
        return response.json()["value"]
    
    def test_connection(self) -> bool:
        """Test Secret Server connectivity."""
        try:
            self._get_token()
            return True
        except Exception:
            return False


class PAMClient:
    """
    Unified PAM client that abstracts backend selection.
    
    Environment Variables:
        PAM_BACKEND: "cyberark", "secretserver", or "both"
        
        For CyberArk:
            CYBERARK_CCP_URL: CyberArk CCP URL
            CYBERARK_APP_ID: Application ID
        
        For Secret Server:
            SECRET_SERVER_URL: Secret Server URL
            SECRET_SERVER_CLIENT_ID: OAuth2 client ID
            SECRET_SERVER_CLIENT_SECRET: OAuth2 client secret
    """
    
    def __init__(self, backend: str = None):
        """
        Initialize PAM client.
        
        Args:
            backend: Override backend selection ("cyberark", "secretserver", "both")
                     If not provided, reads from PAM_BACKEND environment variable
        """
        self.backend_name = backend or os.environ.get("PAM_BACKEND", "secretserver")
        self._cyberark = None
        self._secretserver = None
        
        logger.info(f"PAM Client initialized with backend: {self.backend_name}")
    
    @property
    def cyberark(self) -> CyberArkBackend:
        """Lazy-load CyberArk backend."""
        if self._cyberark is None:
            self._cyberark = CyberArkBackend()
        return self._cyberark
    
    @property
    def secretserver(self) -> SecretServerBackend:
        """Lazy-load Secret Server backend."""
        if self._secretserver is None:
            self._secretserver = SecretServerBackend()
        return self._secretserver
    
    def get_password(
        self,
        secret_id: int = None,
        cyberark_safe: str = None,
        cyberark_object: str = None
    ) -> str:
        """
        Retrieve password from configured PAM backend.
        
        Args:
            secret_id: Secret Server secret ID
            cyberark_safe: CyberArk Safe name (for fallback)
            cyberark_object: CyberArk Object name (for fallback)
        
        Returns:
            Password string
        
        Raises:
            RuntimeError: If password retrieval fails
        """
        if self.backend_name == "cyberark":
            return self._get_from_cyberark(cyberark_safe, cyberark_object)
        
        elif self.backend_name == "secretserver":
            return self._get_from_secretserver(secret_id)
        
        elif self.backend_name == "both":
            # Try Secret Server first, fall back to CyberArk
            try:
                return self._get_from_secretserver(secret_id)
            except Exception as e:
                logger.warning(f"Secret Server failed, falling back to CyberArk: {e}")
                return self._get_from_cyberark(cyberark_safe, cyberark_object)
        
        else:
            raise ValueError(f"Unknown backend: {self.backend_name}")
    
    def _get_from_cyberark(self, safe: str, obj: str) -> str:
        """Retrieve from CyberArk."""
        logger.debug(f"Retrieving from CyberArk: Safe={safe}, Object={obj}")
        return self.cyberark.get_password(cyberark_safe=safe, cyberark_object=obj)
    
    def _get_from_secretserver(self, secret_id: int) -> str:
        """Retrieve from Secret Server."""
        logger.debug(f"Retrieving from Secret Server: SecretID={secret_id}")
        return self.secretserver.get_password(secret_id=secret_id)
    
    def test_backends(self) -> dict:
        """
        Test connectivity to all backends.
        
        Returns:
            Dict with backend names and their status
        """
        results = {}
        
        try:
            results["cyberark"] = self.cyberark.test_connection()
        except Exception as e:
            results["cyberark"] = False
            logger.error(f"CyberArk test failed: {e}")
        
        try:
            results["secretserver"] = self.secretserver.test_connection()
        except Exception as e:
            results["secretserver"] = False
            logger.error(f"Secret Server test failed: {e}")
        
        return results


# Convenience function for simple use cases
_default_client = None

def get_password(
    secret_id: int = None,
    cyberark_safe: str = None,
    cyberark_object: str = None
) -> str:
    """
    Convenience function to get password without managing client.
    
    Usage:
        from pam_wrapper import get_password
        password = get_password(secret_id=1234, cyberark_safe="Backup", cyberark_object="Backup")
    """
    global _default_client
    if _default_client is None:
        _default_client = PAMClient()
    return _default_client.get_password(secret_id, cyberark_safe, cyberark_object)


if __name__ == "__main__":
    # Self-test
    import sys
    
    print("PAM Wrapper Self-Test")
    print("=" * 50)
    
    client = PAMClient()
    print(f"Backend: {client.backend_name}")
    
    results = client.test_backends()
    for backend, status in results.items():
        status_str = "✓ Connected" if status else "✗ Failed"
        print(f"  {backend}: {status_str}")
    
    sys.exit(0 if any(results.values()) else 1)
''',

    "powershell": '''<#
.SYNOPSIS
    PAM Abstraction Wrapper for PowerShell
    
.DESCRIPTION
    This wrapper allows scripts to retrieve credentials without being
    tightly coupled to a specific PAM solution. During migration, the backend
    can be switched via configuration without script code changes.
    
.NOTES
    Configuration via environment variables:
    - PAM_BACKEND: "cyberark", "secretserver", or "both"
    
    For CyberArk:
    - CYBERARK_CCP_URL
    - CYBERARK_APP_ID
    
    For Secret Server:
    - SECRET_SERVER_URL
    - SECRET_SERVER_CLIENT_ID
    - SECRET_SERVER_CLIENT_SECRET
#>

# Configuration
$script:PAMConfig = @{
    Backend = $env:PAM_BACKEND ?? "secretserver"
    
    CyberArk = @{
        Url = $env:CYBERARK_CCP_URL
        AppId = $env:CYBERARK_APP_ID
    }
    
    SecretServer = @{
        Url = $env:SECRET_SERVER_URL
        ClientId = $env:SECRET_SERVER_CLIENT_ID
        ClientSecret = $env:SECRET_SERVER_CLIENT_SECRET
    }
}

# Token cache for Secret Server
$script:SSToken = $null
$script:SSTokenExpiry = [DateTime]::MinValue

function Get-SSAccessToken {
    <#
    .SYNOPSIS
        Get OAuth2 token for Secret Server
    #>
    
    if ($script:SSToken -and [DateTime]::UtcNow -lt $script:SSTokenExpiry.AddMinutes(-1)) {
        return $script:SSToken
    }
    
    $body = @{
        grant_type = "client_credentials"
        client_id = $script:PAMConfig.SecretServer.ClientId
        client_secret = $script:PAMConfig.SecretServer.ClientSecret
    }
    
    $response = Invoke-RestMethod `
        -Uri "$($script:PAMConfig.SecretServer.Url)/oauth2/token" `
        -Method Post `
        -Body $body
    
    $script:SSToken = $response.access_token
    $script:SSTokenExpiry = [DateTime]::UtcNow.AddSeconds($response.expires_in)
    
    return $script:SSToken
}

function Get-PAMPassword {
    <#
    .SYNOPSIS
        Retrieve password from configured PAM backend
    
    .PARAMETER SecretId
        Secret Server secret ID
    
    .PARAMETER CyberArkSafe
        CyberArk Safe name (for fallback)
    
    .PARAMETER CyberArkObject
        CyberArk Object name (for fallback)
    
    .EXAMPLE
        $password = Get-PAMPassword -SecretId 1234 -CyberArkSafe "MySafe" -CyberArkObject "MyAccount"
    #>
    [CmdletBinding()]
    param(
        [Parameter()]
        [int]$SecretId,
        
        [Parameter()]
        [string]$CyberArkSafe,
        
        [Parameter()]
        [string]$CyberArkObject
    )
    
    switch ($script:PAMConfig.Backend) {
        "cyberark" {
            return Get-CyberArkPassword -Safe $CyberArkSafe -Object $CyberArkObject
        }
        "secretserver" {
            return Get-SecretServerPassword -SecretId $SecretId
        }
        "both" {
            try {
                return Get-SecretServerPassword -SecretId $SecretId
            } catch {
                Write-Warning "Secret Server failed, falling back to CyberArk: $_"
                return Get-CyberArkPassword -Safe $CyberArkSafe -Object $CyberArkObject
            }
        }
        default {
            throw "Unknown PAM backend: $($script:PAMConfig.Backend)"
        }
    }
}

function Get-CyberArkPassword {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory)]
        [string]$Safe,
        
        [Parameter(Mandatory)]
        [string]$Object
    )
    
    $uri = "$($script:PAMConfig.CyberArk.Url)/AIMWebService/api/Accounts"
    $params = @{
        AppID = $script:PAMConfig.CyberArk.AppId
        Safe = $Safe
        Object = $Object
    }
    
    $response = Invoke-RestMethod -Uri $uri -Method Get -Body $params
    return $response.Content
}

function Get-SecretServerPassword {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory)]
        [int]$SecretId
    )
    
    $token = Get-SSAccessToken
    $headers = @{ Authorization = "Bearer $token" }
    
    $uri = "$($script:PAMConfig.SecretServer.Url)/api/v1/secrets/$SecretId/fields/password"
    $response = Invoke-RestMethod -Uri $uri -Method Get -Headers $headers
    
    return $response.value
}

function Test-PAMBackends {
    <#
    .SYNOPSIS
        Test connectivity to PAM backends
    #>
    
    $results = @{}
    
    # Test CyberArk
    try {
        $null = Invoke-WebRequest `
            -Uri "$($script:PAMConfig.CyberArk.Url)/AIMWebService/api/" `
            -Method Get `
            -TimeoutSec 10 `
            -ErrorAction Stop
        $results["CyberArk"] = $true
    } catch {
        $results["CyberArk"] = $false
    }
    
    # Test Secret Server
    try {
        $null = Get-SSAccessToken
        $results["SecretServer"] = $true
    } catch {
        $results["SecretServer"] = $false
    }
    
    return $results
}

# Export functions
Export-ModuleMember -Function Get-PAMPassword, Test-PAMBackends
''',
}


def generate_wrapper(language: str, output_path: str):
    """Generate wrapper file for specified language."""
    if language not in WRAPPER_TEMPLATES:
        print(f"Error: Unsupported language '{language}'")
        print(f"Supported: {', '.join(WRAPPER_TEMPLATES.keys())}")
        return False
    
    # Ensure directory exists
    output_dir = os.path.dirname(output_path)
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)
    
    with open(output_path, 'w') as f:
        f.write(WRAPPER_TEMPLATES[language])
    
    print(f"Generated wrapper: {output_path}")
    print(f"\nUsage:")
    print(f"  1. Set environment variables (PAM_BACKEND, SECRET_SERVER_*, CYBERARK_*)")
    print(f"  2. Import wrapper in your application")
    print(f"  3. Call get_password() with both Secret Server and CyberArk parameters")
    print(f"  4. Change PAM_BACKEND to switch between systems")
    
    return True


def main():
    parser = argparse.ArgumentParser(
        description="Generate PAM abstraction wrapper for gradual migration"
    )
    parser.add_argument(
        "--language", "-l",
        choices=["python", "powershell"],
        default="python",
        help="Target language (default: python)"
    )
    parser.add_argument(
        "--output", "-o",
        help="Output file path (default: pam_wrapper.py or pam_wrapper.psm1)"
    )
    
    args = parser.parse_args()
    
    if not args.output:
        ext = {"python": ".py", "powershell": ".psm1"}[args.language]
        args.output = f"pam_wrapper{ext}"
    
    success = generate_wrapper(args.language, args.output)
    return 0 if success else 1


if __name__ == "__main__":
    exit(main())

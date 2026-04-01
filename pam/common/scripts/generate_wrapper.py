#!/usr/bin/env python3
"""
PAM Wrapper Generator

Generates an abstraction layer that allows applications to switch between
CyberArk and a target PAM platform (KeeperPAM or Secret Server) without
application code changes.

The wrapper pattern enables:
- Gradual migration (switch backends per-application via PAM_BACKEND env var)
- Easy rollback (change one config value)
- Minimal application code changes

Platforms:
    --platform keeper       KeeperPAM / Keeper Secrets Manager SDK (live target)
    --platform secretserver Delinea Secret Server REST API (comparison path)

Languages:
    --language python       Python 3.8+
    --language powershell   PowerShell 5.1+ / PowerShell Core 7+

Usage:
    # KeeperPAM (live target)
    python generate_wrapper.py --platform keeper --language python --output keeper_wrapper.py
    python generate_wrapper.py --platform keeper --language powershell --output KeeperPAMWrapper.psm1

    # Secret Server (comparison path)
    python generate_wrapper.py --platform secretserver --language python --output ss_wrapper.py
    python generate_wrapper.py --platform secretserver --language powershell --output SSWrapper.psm1
"""

import argparse
import os

# ── KeeperPAM Wrapper Templates ───────────────────────────────────────────────

KEEPER_PYTHON = '''#!/usr/bin/env python3
"""
KeeperPAM Abstraction Wrapper

Retrieves credentials from Keeper Secrets Manager (KSM) with a CyberArk CCP
fallback during migration. Supports gradual cutover per application.

Install:
    pip install keeper-secrets-manager-core

Configuration (environment variables):
    PAM_BACKEND         : "keeper" | "cyberark" | "both" (default: "keeper")

    For KeeperPAM:
        KSM_CONFIG_FILE     : Path to KSM client config JSON (default: ksm_config.json)
        KSM_ONE_TIME_TOKEN  : One-time token for first-run initialization (ot:... format)
                              Set this on first run only; config file is created automatically.

    For CyberArk (fallback during migration):
        CYBERARK_CCP_URL    : CyberArk CCP base URL
        CYBERARK_APP_ID     : CyberArk Application ID

Usage:
    from keeper_wrapper import PAMClient

    client = PAMClient()

    # Retrieve by Keeper record UID (preferred)
    password = client.get_field(uid="XXXX-YYYY-ZZZZ", field="password")
    login    = client.get_field(uid="XXXX-YYYY-ZZZZ", field="login")

    # Retrieve with CyberArk fallback (migration mode)
    password = client.get_password(
        uid="XXXX-YYYY-ZZZZ",          # Keeper record UID
        cyberark_safe="MySafe",         # CyberArk fallback
        cyberark_object="MyAccount"     # CyberArk fallback
    )

    # Convenience function (no client management)
    from keeper_wrapper import get_password
    password = get_password(uid="XXXX-YYYY-ZZZZ", cyberark_safe="MySafe", cyberark_object="MyAccount")

Record UIDs:
    Find UIDs in Keeper Vault → select record → Details → Record UID.
    UIDs are stable identifiers that do not change when a record is renamed.
"""

import os
import logging
import time
from abc import ABC, abstractmethod
from typing import Optional

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────
# Abstract base
# ─────────────────────────────────────────────

class PAMBackend(ABC):
    """Abstract base class for PAM credential backends."""

    @abstractmethod
    def get_field(self, uid: str, field: str = "password") -> str:
        """Retrieve a field value from a secret/record."""

    @abstractmethod
    def test_connection(self) -> bool:
        """Verify connectivity to the PAM system."""


# ─────────────────────────────────────────────
# KeeperPAM backend (Keeper Secrets Manager SDK)
# ─────────────────────────────────────────────

class KeeperBackend(PAMBackend):
    """
    Keeper Secrets Manager (KSM) backend.

    Requires: pip install keeper-secrets-manager-core

    Auth is managed via a config file (JSON). On first run, provide
    KSM_ONE_TIME_TOKEN to initialize the config file. Subsequent runs
    use the config file directly — no token needed.

    The KSM SDK caches records locally (encrypted) for resilience.
    Records are identified by UID — a stable string that does not change
    when the record is renamed.
    """

    def __init__(self):
        try:
            from keeper_secrets_manager_core import SecretsManager
            from keeper_secrets_manager_core.storage import (
                FileKeyValueStorage,
                InMemoryKeyValueStorage,
            )
        except ImportError:
            raise ImportError(
                "keeper-secrets-manager-core is required for KeeperPAM backend.\\n"
                "Install: pip install keeper-secrets-manager-core"
            )

        self._SecretsManager = SecretsManager
        self._FileKeyValueStorage = FileKeyValueStorage
        self._InMemoryKeyValueStorage = InMemoryKeyValueStorage
        self._sm = None
        self._init_secrets_manager()

    def _init_secrets_manager(self):
        """Initialize KSM client from config file or one-time token."""
        one_time_token = os.environ.get("KSM_ONE_TIME_TOKEN")
        config_file = os.environ.get("KSM_CONFIG_FILE", "ksm_config.json")

        if one_time_token:
            # First-run: initialize from one-time token, persist to config file
            logger.info("KSM: Initializing from one-time token → %s", config_file)
            storage = self._FileKeyValueStorage(config_file)
            self._sm = self._SecretsManager(token=one_time_token, config=storage)
            logger.info("KSM: Config file created at %s — unset KSM_ONE_TIME_TOKEN", config_file)
        elif os.path.exists(config_file):
            # Normal run: load from existing config file
            logger.debug("KSM: Loading config from %s", config_file)
            storage = self._FileKeyValueStorage(config_file)
            self._sm = self._SecretsManager(config=storage)
        else:
            raise RuntimeError(
                f"KSM config not found: {config_file}\\n"
                "Set KSM_ONE_TIME_TOKEN for first-run initialization, or\\n"
                f"set KSM_CONFIG_FILE to point to an existing config file."
            )

    def get_field(self, uid: str, field: str = "password") -> str:
        """
        Retrieve a field value from a Keeper record by UID.

        Args:
            uid:   Keeper record UID (stable identifier, e.g. "XXXX-YYYY-ZZZZ")
            field: Field type to retrieve — "password", "login", "url",
                   "host", "port", or any custom field label.

        Returns:
            Field value as a string.

        Raises:
            ValueError: If the record or field is not found.
            RuntimeError: If KSM connectivity fails.
        """
        logger.debug("KSM: Retrieving field='%s' from record uid='%s'", field, uid)

        records = self._sm.get_secrets([uid])
        if not records:
            raise ValueError(
                f"Keeper record not found: uid={uid}\\n"
                "Verify the UID in Keeper Vault → record Details → Record UID."
            )

        record = records[0]

        # Standard field types: password, login, url, host, port, etc.
        try:
            value = record.field(field, single=True)
            if value is not None:
                return value
        except Exception:
            pass

        # Custom fields (user-defined labels)
        try:
            value = record.custom_field(field, single=True)
            if value is not None:
                return value
        except Exception:
            pass

        raise ValueError(
            f"Field '{field}' not found in Keeper record uid={uid}.\\n"
            "Available standard fields: password, login, url, host, port.\\n"
            "For custom fields, use the exact label as defined in Keeper Vault."
        )

    def get_password(self, uid: str, **kwargs) -> str:
        """Convenience method — retrieves the 'password' field."""
        return self.get_field(uid=uid, field="password")

    def test_connection(self) -> bool:
        """Test KSM connectivity by fetching record list (lightweight)."""
        try:
            # Fetch with no UIDs — returns empty list but validates auth
            self._sm.get_secrets([])
            return True
        except Exception as e:
            logger.error("KSM connection test failed: %s", e)
            return False


# ─────────────────────────────────────────────
# CyberArk CCP backend (migration fallback)
# ─────────────────────────────────────────────

class CyberArkBackend(PAMBackend):
    """
    CyberArk CCP (Central Credential Provider) backend.
    Used as fallback during migration — retire once Wave 5 is complete.
    """

    def __init__(self):
        self.base_url = os.environ.get("CYBERARK_CCP_URL")
        self.app_id = os.environ.get("CYBERARK_APP_ID")

        if not self.base_url or not self.app_id:
            raise ValueError(
                "CYBERARK_CCP_URL and CYBERARK_APP_ID environment variables required"
            )

    def get_field(self, uid: str = None, field: str = "password",
                  cyberark_safe: str = None, cyberark_object: str = None) -> str:
        """Retrieve from CyberArk CCP. uid is ignored — uses safe/object."""
        import requests

        if not cyberark_safe or not cyberark_object:
            raise ValueError("cyberark_safe and cyberark_object required for CyberArk backend")

        response = requests.get(
            f"{self.base_url}/AIMWebService/api/Accounts",
            params={
                "AppID": self.app_id,
                "Safe": cyberark_safe,
                "Object": cyberark_object,
            },
            verify=True,
            timeout=30,
        )
        response.raise_for_status()
        return response.json()["Content"]

    def get_password(self, cyberark_safe: str = None, cyberark_object: str = None, **kwargs) -> str:
        return self.get_field(
            field="password",
            cyberark_safe=cyberark_safe,
            cyberark_object=cyberark_object,
        )

    def test_connection(self) -> bool:
        import requests
        try:
            response = requests.get(
                f"{self.base_url}/AIMWebService/api/",
                timeout=10,
            )
            return response.status_code < 500
        except Exception:
            return False


# ─────────────────────────────────────────────
# Unified PAM client
# ─────────────────────────────────────────────

class PAMClient:
    """
    Unified PAM client — abstracts backend selection via PAM_BACKEND env var.

    Backends:
        "keeper"   — Keeper Secrets Manager SDK (production target)
        "cyberark" — CyberArk CCP (legacy source, migration fallback)
        "both"     — Try Keeper first; fall back to CyberArk on failure

    Environment variables:
        PAM_BACKEND         : Backend selection (default: "keeper")

        KeeperPAM:
            KSM_CONFIG_FILE     : Path to KSM client config (default: ksm_config.json)
            KSM_ONE_TIME_TOKEN  : First-run initialization token (ot:...)

        CyberArk (fallback):
            CYBERARK_CCP_URL    : CCP base URL
            CYBERARK_APP_ID     : Application ID
    """

    def __init__(self, backend: str = None):
        self.backend_name = backend or os.environ.get("PAM_BACKEND", "keeper")
        self._keeper: Optional[KeeperBackend] = None
        self._cyberark: Optional[CyberArkBackend] = None
        logger.info("PAMClient initialized with backend: %s", self.backend_name)

    @property
    def keeper(self) -> KeeperBackend:
        if self._keeper is None:
            self._keeper = KeeperBackend()
        return self._keeper

    @property
    def cyberark(self) -> CyberArkBackend:
        if self._cyberark is None:
            self._cyberark = CyberArkBackend()
        return self._cyberark

    def get_field(
        self,
        uid: str = None,
        field: str = "password",
        cyberark_safe: str = None,
        cyberark_object: str = None,
    ) -> str:
        """
        Retrieve a field value from the configured PAM backend.

        Args:
            uid:              Keeper record UID (required for keeper backend)
            field:            Field type to retrieve (default: "password")
            cyberark_safe:    CyberArk Safe name (for cyberark/both backends)
            cyberark_object:  CyberArk Object name (for cyberark/both backends)

        Returns:
            Field value as string.
        """
        if self.backend_name == "keeper":
            return self.keeper.get_field(uid=uid, field=field)

        elif self.backend_name == "cyberark":
            return self.cyberark.get_field(
                field=field,
                cyberark_safe=cyberark_safe,
                cyberark_object=cyberark_object,
            )

        elif self.backend_name == "both":
            try:
                return self.keeper.get_field(uid=uid, field=field)
            except Exception as e:
                logger.warning("Keeper failed, falling back to CyberArk: %s", e)
                return self.cyberark.get_field(
                    field=field,
                    cyberark_safe=cyberark_safe,
                    cyberark_object=cyberark_object,
                )

        else:
            raise ValueError(f"Unknown PAM_BACKEND: {self.backend_name!r}. Use: keeper, cyberark, both")

    def get_password(
        self,
        uid: str = None,
        cyberark_safe: str = None,
        cyberark_object: str = None,
    ) -> str:
        """Convenience method — retrieves the \'password\' field."""
        return self.get_field(
            uid=uid,
            field="password",
            cyberark_safe=cyberark_safe,
            cyberark_object=cyberark_object,
        )

    def test_backends(self) -> dict:
        """Test connectivity to all configured backends."""
        results = {}

        try:
            results["keeper"] = self.keeper.test_connection()
        except Exception as e:
            results["keeper"] = False
            logger.error("Keeper test failed: %s", e)

        try:
            results["cyberark"] = self.cyberark.test_connection()
        except Exception as e:
            results["cyberark"] = False
            logger.error("CyberArk test failed: %s", e)

        return results


# ─────────────────────────────────────────────
# Convenience function
# ─────────────────────────────────────────────

_default_client: Optional[PAMClient] = None


def get_password(
    uid: str = None,
    cyberark_safe: str = None,
    cyberark_object: str = None,
    field: str = "password",
) -> str:
    """
    Module-level convenience — retrieve a password without managing a PAMClient.

    Usage:
        from keeper_wrapper import get_password

        # KeeperPAM (PAM_BACKEND=keeper)
        password = get_password(uid="XXXX-YYYY-ZZZZ")

        # Migration mode (PAM_BACKEND=both)
        password = get_password(uid="XXXX-YYYY-ZZZZ", cyberark_safe="MySafe", cyberark_object="MyAccount")
    """
    global _default_client
    if _default_client is None:
        _default_client = PAMClient()
    return _default_client.get_field(
        uid=uid,
        field=field,
        cyberark_safe=cyberark_safe,
        cyberark_object=cyberark_object,
    )


# ─────────────────────────────────────────────
# Self-test
# ─────────────────────────────────────────────

if __name__ == "__main__":
    import sys

    print("KeeperPAM Wrapper Self-Test")
    print("=" * 50)

    client = PAMClient()
    print(f"Backend: {client.backend_name}")
    print()

    results = client.test_backends()
    for backend, ok in results.items():
        status = "Connected" if ok else "FAILED"
        print(f"  {backend}: {status}")

    print()
    if not any(results.values()):
        print("ERROR: No PAM backend reachable.")
        sys.exit(1)

    print("Self-test passed.")
    sys.exit(0)
'''

KEEPER_POWERSHELL = '''<#
.SYNOPSIS
    KeeperPAM Abstraction Wrapper for PowerShell

.DESCRIPTION
    Retrieves credentials from Keeper Secrets Manager (KSM) with a CyberArk
    CCP fallback during migration. Supports gradual cutover per script.

.NOTES
    Requires: Keeper Commander PowerShell module or KSM REST endpoint.
    See: https://github.com/Keeper-Security/secrets-manager

    Configuration via environment variables:
        PAM_BACKEND             : "keeper" | "cyberark" | "both" (default: "keeper")

        KeeperPAM:
            KSM_CONFIG_FILE     : Path to KSM client config JSON (default: ksm_config.json)
            KSM_ONE_TIME_TOKEN  : One-time token for first-run init (ot:... format)

        CyberArk (fallback):
            CYBERARK_CCP_URL    : CCP base URL
            CYBERARK_APP_ID     : Application ID

.EXAMPLE
    # Import module
    Import-Module ./KeeperPAMWrapper.psm1

    # Retrieve password by record UID
    $password = Get-PAMPassword -UID "XXXX-YYYY-ZZZZ"

    # Retrieve specific field
    $login = Get-PAMField -UID "XXXX-YYYY-ZZZZ" -Field "login"

    # Migration mode (tries Keeper first, falls back to CyberArk)
    $env:PAM_BACKEND = "both"
    $password = Get-PAMPassword -UID "XXXX-YYYY-ZZZZ" -CyberArkSafe "MySafe" -CyberArkObject "MyAccount"
#>

#Requires -Version 5.1

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

# ── Configuration ────────────────────────────────────────────────────

$script:PAMConfig = @{
    Backend    = if ($env:PAM_BACKEND) { $env:PAM_BACKEND } else { "keeper" }
    ConfigFile = if ($env:KSM_CONFIG_FILE) { $env:KSM_CONFIG_FILE } else { "ksm_config.json" }
    CyberArk   = @{
        Url   = $env:CYBERARK_CCP_URL
        AppId = $env:CYBERARK_APP_ID
    }
}

# ── KSM SDK detection ─────────────────────────────────────────────────

$script:KSMAvailable = $false
try {
    # Try loading the Keeper Secrets Manager PowerShell module if installed
    if (Get-Module -ListAvailable -Name "SecretManagement.Keeper" -ErrorAction SilentlyContinue) {
        Import-Module SecretManagement.Keeper -ErrorAction Stop
        $script:KSMAvailable = $true
        Write-Verbose "KSM: Using SecretManagement.Keeper module"
    }
} catch {
    Write-Verbose "KSM: SecretManagement.Keeper not available, using KSM REST fallback"
}

# ── KeeperPAM functions ───────────────────────────────────────────────

function Initialize-KSMConfig {
    <#
    .SYNOPSIS
        Initialize KSM config from one-time token (first run only).
    #>
    $token = $env:KSM_ONE_TIME_TOKEN
    if (-not $token) {
        if (-not (Test-Path $script:PAMConfig.ConfigFile)) {
            throw "KSM config not found: $($script:PAMConfig.ConfigFile)`n" +
                  "Set KSM_ONE_TIME_TOKEN for first-run initialization."
        }
        return
    }

    Write-Warning "KSM: Initializing from one-time token. Unset KSM_ONE_TIME_TOKEN after first run."

    if ($script:KSMAvailable) {
        # Use PS module if available
        Register-SecretVault -Name "KeeperVault" -ModuleName "SecretManagement.Keeper" `
            -VaultParameters @{ OneTimeToken = $token; ConfigFile = $script:PAMConfig.ConfigFile }
    } else {
        # Config-file based init via KSM REST is complex in PS — log guidance
        Write-Warning "KSM: Install SecretManagement.Keeper module for full PowerShell support:`n" +
                      "  Install-Module SecretManagement.Keeper"
        throw "KSM one-time token initialization requires SecretManagement.Keeper PS module."
    }
}

function Get-KeeperField {
    <#
    .SYNOPSIS
        Retrieve a field from a Keeper record by UID.

    .PARAMETER UID
        Keeper record UID (find in Vault → record Details → Record UID).

    .PARAMETER Field
        Field type: "password", "login", "url", "host", or custom field label.
    #>
    [CmdletBinding()]
    param(
        [Parameter(Mandatory)][string]$UID,
        [Parameter()][string]$Field = "password"
    )

    Write-Verbose "KSM: Retrieving field='$Field' from record uid='$UID'"

    if ($script:KSMAvailable) {
        # Use SecretManagement.Keeper PS module
        $secret = Get-Secret -Name $UID -Vault "KeeperVault" -ErrorAction Stop
        if ($Field -eq "password") { return $secret.GetNetworkCredential().Password }
        return $secret.$Field
    }

    # Fallback: attempt KSM REST endpoint (requires keeper-secrets-manager REST proxy)
    $ksmUrl = $env:KSM_REST_URL
    if (-not $ksmUrl) {
        throw "KSM retrieval failed: SecretManagement.Keeper module not installed and KSM_REST_URL not set.`n" +
              "Install module: Install-Module SecretManagement.Keeper"
    }

    $response = Invoke-RestMethod -Uri "$ksmUrl/secrets/$UID/fields/$Field" -Method Get -ErrorAction Stop
    return $response.value
}

function Test-KeeperConnection {
    <#
    .SYNOPSIS
        Test KSM connectivity.
    #>
    try {
        if ($script:KSMAvailable) {
            $null = Get-SecretVault -Name "KeeperVault" -ErrorAction Stop
            return $true
        }
        $ksmUrl = $env:KSM_REST_URL
        if ($ksmUrl) {
            $null = Invoke-RestMethod -Uri "$ksmUrl/health" -TimeoutSec 10 -ErrorAction Stop
            return $true
        }
        return $false
    } catch {
        return $false
    }
}

# ── CyberArk CCP functions ────────────────────────────────────────────

function Get-CyberArkPassword {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory)][string]$Safe,
        [Parameter(Mandatory)][string]$Object
    )

    $uri    = "$($script:PAMConfig.CyberArk.Url)/AIMWebService/api/Accounts"
    $params = @{ AppID = $script:PAMConfig.CyberArk.AppId; Safe = $Safe; Object = $Object }
    $response = Invoke-RestMethod -Uri $uri -Method Get -Body $params -ErrorAction Stop
    return $response.Content
}

function Test-CyberArkConnection {
    try {
        $null = Invoke-WebRequest -Uri "$($script:PAMConfig.CyberArk.Url)/AIMWebService/api/" `
            -Method Get -TimeoutSec 10 -ErrorAction Stop
        return $true
    } catch {
        return $false
    }
}

# ── Public API ────────────────────────────────────────────────────────

function Get-PAMField {
    <#
    .SYNOPSIS
        Retrieve any field from the configured PAM backend.

    .PARAMETER UID
        Keeper record UID (required for keeper backend).

    .PARAMETER Field
        Field type to retrieve (default: "password").

    .PARAMETER CyberArkSafe
        CyberArk Safe name (required for cyberark/both backends).

    .PARAMETER CyberArkObject
        CyberArk Object name (required for cyberark/both backends).

    .EXAMPLE
        $login = Get-PAMField -UID "XXXX-YYYY-ZZZZ" -Field "login"
    #>
    [CmdletBinding()]
    param(
        [Parameter()][string]$UID,
        [Parameter()][string]$Field = "password",
        [Parameter()][string]$CyberArkSafe,
        [Parameter()][string]$CyberArkObject
    )

    switch ($script:PAMConfig.Backend) {
        "keeper" {
            return Get-KeeperField -UID $UID -Field $Field
        }
        "cyberark" {
            return Get-CyberArkPassword -Safe $CyberArkSafe -Object $CyberArkObject
        }
        "both" {
            try {
                return Get-KeeperField -UID $UID -Field $Field
            } catch {
                Write-Warning "Keeper failed, falling back to CyberArk: $_"
                return Get-CyberArkPassword -Safe $CyberArkSafe -Object $CyberArkObject
            }
        }
        default {
            throw "Unknown PAM_BACKEND: $($script:PAMConfig.Backend). Use: keeper, cyberark, both"
        }
    }
}

function Get-PAMPassword {
    <#
    .SYNOPSIS
        Retrieve password from configured PAM backend.

    .PARAMETER UID
        Keeper record UID.

    .PARAMETER CyberArkSafe
        CyberArk Safe (fallback).

    .PARAMETER CyberArkObject
        CyberArk Object (fallback).

    .EXAMPLE
        $password = Get-PAMPassword -UID "XXXX-YYYY-ZZZZ"
    #>
    [CmdletBinding()]
    param(
        [Parameter()][string]$UID,
        [Parameter()][string]$CyberArkSafe,
        [Parameter()][string]$CyberArkObject
    )
    return Get-PAMField -UID $UID -Field "password" `
        -CyberArkSafe $CyberArkSafe -CyberArkObject $CyberArkObject
}

function Test-PAMBackends {
    <#
    .SYNOPSIS
        Test connectivity to all PAM backends.

    .EXAMPLE
        Test-PAMBackends
    #>
    $results = @{}

    Write-Host "Testing PAM backends..."
    Write-Host "Backend: $($script:PAMConfig.Backend)"
    Write-Host ""

    $results["Keeper"]   = Test-KeeperConnection
    $results["CyberArk"] = Test-CyberArkConnection

    foreach ($backend in $results.Keys) {
        $status = if ($results[$backend]) { "Connected" } else { "FAILED" }
        Write-Host "  ${backend}: ${status}"
    }

    return $results
}

# ── Module exports ────────────────────────────────────────────────────

Export-ModuleMember -Function Get-PAMField, Get-PAMPassword, Test-PAMBackends, Initialize-KSMConfig
'''

# ── Secret Server Wrapper Templates (retained for comparison path) ────────────

SECRETSERVER_PYTHON = '''#!/usr/bin/env python3
"""
Secret Server PAM Abstraction Wrapper

Retrieves credentials from Delinea Secret Server REST API with CyberArk
CCP fallback during migration. For KeeperPAM (live target), use keeper_wrapper.py.

Install:
    pip install requests

Configuration:
    PAM_BACKEND             : "secretserver" | "cyberark" | "both" (default: "secretserver")
    SECRET_SERVER_URL       : Secret Server base URL
    SECRET_SERVER_CLIENT_ID : OAuth2 client ID
    SECRET_SERVER_CLIENT_SECRET : OAuth2 client secret
    CYBERARK_CCP_URL        : CyberArk CCP URL (fallback)
    CYBERARK_APP_ID         : CyberArk App ID (fallback)

Usage:
    from ss_wrapper import PAMClient
    client = PAMClient()
    password = client.get_password(secret_id=1234, cyberark_safe="MySafe", cyberark_object="MyAccount")
"""

import os
import logging
import time
from abc import ABC, abstractmethod
from typing import Optional
import requests

logger = logging.getLogger(__name__)


class PAMBackend(ABC):
    @abstractmethod
    def get_password(self, **kwargs) -> str: pass
    @abstractmethod
    def test_connection(self) -> bool: pass


class SecretServerBackend(PAMBackend):
    def __init__(self):
        self.base_url = os.environ.get("SECRET_SERVER_URL")
        self.client_id = os.environ.get("SECRET_SERVER_CLIENT_ID")
        self.client_secret = os.environ.get("SECRET_SERVER_CLIENT_SECRET")
        if not all([self.base_url, self.client_id, self.client_secret]):
            raise ValueError("SECRET_SERVER_URL, SECRET_SERVER_CLIENT_ID, SECRET_SERVER_CLIENT_SECRET required")
        self._token = None
        self._token_expiry = 0

    def _get_token(self) -> str:
        if self._token and time.time() < self._token_expiry - 60:
            return self._token
        r = requests.post(f"{self.base_url}/oauth2/token",
            data={"grant_type": "client_credentials",
                  "client_id": self.client_id,
                  "client_secret": self.client_secret}, timeout=30)
        r.raise_for_status()
        data = r.json()
        self._token = data["access_token"]
        self._token_expiry = time.time() + data.get("expires_in", 3600)
        return self._token

    def get_password(self, secret_id: int = None, **kwargs) -> str:
        if not secret_id:
            raise ValueError("secret_id required")
        r = requests.get(f"{self.base_url}/api/v1/secrets/{secret_id}/fields/password",
            headers={"Authorization": f"Bearer {self._get_token()}"}, timeout=30)
        r.raise_for_status()
        return r.json()["value"]

    def test_connection(self) -> bool:
        try: self._get_token(); return True
        except Exception: return False


class CyberArkBackend(PAMBackend):
    def __init__(self):
        self.base_url = os.environ.get("CYBERARK_CCP_URL")
        self.app_id = os.environ.get("CYBERARK_APP_ID")
        if not self.base_url or not self.app_id:
            raise ValueError("CYBERARK_CCP_URL and CYBERARK_APP_ID required")

    def get_password(self, cyberark_safe: str = None, cyberark_object: str = None, **kwargs) -> str:
        if not cyberark_safe or not cyberark_object:
            raise ValueError("cyberark_safe and cyberark_object required")
        r = requests.get(f"{self.base_url}/AIMWebService/api/Accounts",
            params={"AppID": self.app_id, "Safe": cyberark_safe, "Object": cyberark_object},
            verify=True, timeout=30)
        r.raise_for_status()
        return r.json()["Content"]

    def test_connection(self) -> bool:
        try:
            r = requests.get(f"{self.base_url}/AIMWebService/api/", timeout=10)
            return r.status_code < 500
        except Exception: return False


class PAMClient:
    def __init__(self, backend: str = None):
        self.backend_name = backend or os.environ.get("PAM_BACKEND", "secretserver")
        self._ss: Optional[SecretServerBackend] = None
        self._ca: Optional[CyberArkBackend] = None

    @property
    def secretserver(self):
        if not self._ss: self._ss = SecretServerBackend()
        return self._ss

    @property
    def cyberark(self):
        if not self._ca: self._ca = CyberArkBackend()
        return self._ca

    def get_password(self, secret_id: int = None, cyberark_safe: str = None, cyberark_object: str = None) -> str:
        if self.backend_name == "secretserver":
            return self.secretserver.get_password(secret_id=secret_id)
        elif self.backend_name == "cyberark":
            return self.cyberark.get_password(cyberark_safe=cyberark_safe, cyberark_object=cyberark_object)
        elif self.backend_name == "both":
            try: return self.secretserver.get_password(secret_id=secret_id)
            except Exception as e:
                logger.warning("SS failed, falling back to CyberArk: %s", e)
                return self.cyberark.get_password(cyberark_safe=cyberark_safe, cyberark_object=cyberark_object)
        else:
            raise ValueError(f"Unknown PAM_BACKEND: {self.backend_name!r}")

    def test_backends(self) -> dict:
        results = {}
        try: results["secretserver"] = self.secretserver.test_connection()
        except Exception: results["secretserver"] = False
        try: results["cyberark"] = self.cyberark.test_connection()
        except Exception: results["cyberark"] = False
        return results


_default_client: Optional[PAMClient] = None

def get_password(secret_id: int = None, cyberark_safe: str = None, cyberark_object: str = None) -> str:
    global _default_client
    if _default_client is None:
        _default_client = PAMClient()
    return _default_client.get_password(secret_id, cyberark_safe, cyberark_object)


if __name__ == "__main__":
    import sys
    client = PAMClient()
    print(f"Backend: {client.backend_name}")
    results = client.test_backends()
    for b, ok in results.items():
        print(f"  {b}: {'Connected' if ok else 'FAILED'}")
    sys.exit(0 if any(results.values()) else 1)
'''

SECRETSERVER_POWERSHELL = open(
    os.path.join(os.path.dirname(__file__), "..", "assets", "templates", "powershell_secret_retrieval.ps1")
).read() if os.path.exists(
    os.path.join(os.path.dirname(__file__), "..", "assets", "templates", "powershell_secret_retrieval.ps1")
) else "# See assets/templates/powershell_secret_retrieval.ps1\n"

# ── Template registry ─────────────────────────────────────────────────────────

WRAPPER_TEMPLATES = {
    "keeper": {
        "python":     KEEPER_PYTHON,
        "powershell": KEEPER_POWERSHELL,
    },
    "secretserver": {
        "python":     SECRETSERVER_PYTHON,
        "powershell": SECRETSERVER_POWERSHELL,
    },
}

DEFAULT_FILENAMES = {
    ("keeper",       "python"):     "keeper_wrapper.py",
    ("keeper",       "powershell"): "KeeperPAMWrapper.psm1",
    ("secretserver", "python"):     "ss_wrapper.py",
    ("secretserver", "powershell"): "SSWrapper.psm1",
}

# ── Generator ─────────────────────────────────────────────────────────────────

def generate_wrapper(platform: str, language: str, output_path: str) -> bool:
    """Generate PAM wrapper for the given platform and language."""
    if platform not in WRAPPER_TEMPLATES:
        print(f"Error: Unknown platform '{platform}'. Supported: {', '.join(WRAPPER_TEMPLATES)}")
        return False

    if language not in WRAPPER_TEMPLATES[platform]:
        supported = ', '.join(WRAPPER_TEMPLATES[platform])
        print(f"Error: Unsupported language '{language}' for platform '{platform}'. Supported: {supported}")
        return False

    output_dir = os.path.dirname(output_path)
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)

    with open(output_path, "w") as f:
        f.write(WRAPPER_TEMPLATES[platform][language])

    print(f"Generated: {output_path}")
    print(f"Platform:  {platform}")
    print(f"Language:  {language}")
    print()

    if platform == "keeper":
        _print_keeper_usage(language, output_path)
    else:
        _print_ss_usage(language, output_path)

    return True


def _print_keeper_usage(language: str, output_path: str):
    print("Next steps:")
    print()
    if language == "python":
        print("  1. Install KSM SDK:")
        print("       pip install keeper-secrets-manager-core")
        print()
        print("  2. First-run initialization (one time per service account):")
        print("       export KSM_ONE_TIME_TOKEN='ot:...'   # from Keeper Vault → Secrets Manager app")
        print("       python keeper_wrapper.py             # creates ksm_config.json")
        print("       unset KSM_ONE_TIME_TOKEN             # never needed again")
        print()
        print("  3. Runtime usage:")
        print("       export PAM_BACKEND=keeper")
        print("       export KSM_CONFIG_FILE=ksm_config.json")
        print()
        print("  4. In your application:")
        print("       from keeper_wrapper import get_password")
        print("       password = get_password(uid='XXXX-YYYY-ZZZZ')")
        print()
        print("  5. Migration mode (Keeper first, CyberArk fallback):")
        print("       export PAM_BACKEND=both")
        print("       export CYBERARK_CCP_URL=https://ccp.company.com")
        print("       export CYBERARK_APP_ID=MyApp")
        print("       password = get_password(uid='XXXX-YYYY-ZZZZ', cyberark_safe='MySafe', cyberark_object='MyAccount')")
    elif language == "powershell":
        print("  1. Install KSM PowerShell module (recommended):")
        print("       Install-Module SecretManagement.Keeper")
        print()
        print("  2. Import and use:")
        print("       Import-Module ./KeeperPAMWrapper.psm1")
        print("       $env:PAM_BACKEND = 'keeper'")
        print("       $env:KSM_ONE_TIME_TOKEN = 'ot:...'   # first run only")
        print("       Initialize-KSMConfig")
        print("       $password = Get-PAMPassword -UID 'XXXX-YYYY-ZZZZ'")
    print()
    print("  Find record UIDs: Keeper Vault → select record → Details → Record UID")


def _print_ss_usage(language: str, output_path: str):
    print("Next steps:")
    print()
    print("  1. Set environment variables:")
    print("       export PAM_BACKEND=secretserver")
    print("       export SECRET_SERVER_URL=https://secretserver.company.com")
    print("       export SECRET_SERVER_CLIENT_ID=your-client-id")
    print("       export SECRET_SERVER_CLIENT_SECRET=your-client-secret")
    print()
    print("  2. Use in application:")
    if language == "python":
        print("       from ss_wrapper import get_password")
        print("       password = get_password(secret_id=1234)")


# ── CLI ───────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Generate PAM abstraction wrapper for CyberArk → KeeperPAM / Secret Server migration",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # KeeperPAM (live target)
  python generate_wrapper.py --platform keeper --language python --output keeper_wrapper.py
  python generate_wrapper.py --platform keeper --language powershell --output KeeperPAMWrapper.psm1

  # Secret Server (comparison path)
  python generate_wrapper.py --platform secretserver --language python --output ss_wrapper.py
        """,
    )
    parser.add_argument(
        "--platform", "-p",
        choices=list(WRAPPER_TEMPLATES.keys()),
        default="keeper",
        help="Target PAM platform (default: keeper — the live migration target)",
    )
    parser.add_argument(
        "--language", "-l",
        choices=["python", "powershell"],
        default="python",
        help="Target language (default: python)",
    )
    parser.add_argument(
        "--output", "-o",
        help="Output file path (default: auto-named by platform + language)",
    )

    args = parser.parse_args()

    if not args.output:
        args.output = DEFAULT_FILENAMES.get((args.platform, args.language), "pam_wrapper.py")

    success = generate_wrapper(args.platform, args.language, args.output)
    return 0 if success else 1


if __name__ == "__main__":
    exit(main())

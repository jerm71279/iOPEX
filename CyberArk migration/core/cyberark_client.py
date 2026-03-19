"""CyberArk PVWA REST API client.

Adapted from PAM_Consulting_Agent/scripts/autodiscovery/connectors/cyberark.py.
Provides authenticated access to the on-prem CyberArk vault for discovery,
account enumeration, safe management, and audit log retrieval.
"""

import os
import re
import time
import logging
from typing import Any, Dict, List, Optional
from urllib.parse import quote

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

logger = logging.getLogger(__name__)

# System safes that should never be migrated
SYSTEM_SAFES = {
    "System", "VaultInternal", "VaultInternal_Node1", "VaultInternal_Node2",
    "Notification Engine", "PVWAConfig", "PVWAReports", "PVWATaskDefinitions",
    "PVWATicketingSystem", "PVWAPrivateUserPrefs", "PVWAPublicData",
    "PasswordManager", "PasswordManager_ADInternal", "PasswordManager_Info",
    "PasswordManagerShared", "AccountsFeedADAccounts", "AccountsFeedDiscovery",
    "PSM", "PSMRecordings", "PSMUniversalConnectors", "PSMLiveSessions",
    "SharedAuth_Internal", "PasswordManager_Pending",
}

# NHI platform IDs that definitionally indicate non-human accounts
NHI_PLATFORMS = {
    "UnixSSHKeys", "WinServiceAccount", "WinScheduledTask",
    "AzureServicePrincipal", "AWSAccessKeys", "HashiCorpVault",
}


def _safe_error(resp: requests.Response, max_len: int = 200) -> str:
    """Sanitize HTTP error response — never leak credentials."""
    text = (resp.text or "")[:max_len]
    text = re.sub(r'"password"\s*:\s*"[^"]*"', '"password":"***"', text)
    text = re.sub(r'"secret"\s*:\s*"[^"]*"', '"secret":"***"', text)
    text = re.sub(r'"Authorization"\s*:\s*"[^"]*"', '"Authorization":"***"', text)
    return f"HTTP {resp.status_code}: {text}"


class CyberArkError(Exception):
    """Base CyberArk API error."""


class AuthenticationError(CyberArkError):
    """Authentication failed."""


class PermissionDeniedError(CyberArkError):
    """Insufficient permissions."""


class CyberArkClient:
    """CyberArk PVWA REST API client with retry, pagination, and rate limiting.

    Usage as context manager (recommended):
        with CyberArkClient(config) as client:
            accounts = client.get_accounts()
    """

    API_BASE = "/PasswordVault/api"

    AUTH_ENDPOINTS = {
        "CyberArk": "/Auth/CyberArk/Logon",
        "LDAP": "/Auth/LDAP/Logon",
        "RADIUS": "/Auth/RADIUS/Logon",
        "Windows": "/Auth/Windows/Logon",
    }

    def __init__(self, config: dict):
        self.base_url = config["base_url"].rstrip("/")
        # Support env var overrides for credentials
        self.username = (
            os.environ.get("CYBERARK_USERNAME")
            or config.get("username", "")
        )
        self._password = (
            os.environ.get("CYBERARK_PASSWORD")
            or config.get("password", "")
        )
        self.auth_type = config.get("auth_type", "LDAP")
        self.verify_ssl = config.get("verify_ssl", True)
        self.timeout = config.get("timeout", 30)
        self.max_retries = config.get("max_retries", 3)
        self.retry_delay = config.get("retry_delay", 1.0)
        self.rate_limit = config.get("rate_limit", 0.1)
        self.batch_size = min(config.get("batch_size", 1000), 1000)  # API max is 1000

        self._session: Optional[requests.Session] = None
        self._token: Optional[str] = None
        self._authenticated = False

    def _create_session(self) -> requests.Session:
        session = requests.Session()
        retry = Retry(
            total=self.max_retries,
            backoff_factor=self.retry_delay,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
        )
        adapter = HTTPAdapter(max_retries=retry)
        session.mount("https://", adapter)
        session.verify = self.verify_ssl
        return session

    def connect(self) -> bool:
        if self.auth_type == "SAML":
            raise CyberArkError(
                "SAML auth requires browser-based redirect flow. "
                "Use CyberArk, LDAP, or RADIUS auth_type instead."
            )

        self._session = self._create_session()
        endpoint = self.AUTH_ENDPOINTS.get(self.auth_type, self.AUTH_ENDPOINTS["LDAP"])
        url = f"{self.base_url}{self.API_BASE}{endpoint}"

        try:
            resp = self._session.post(
                url,
                json={"username": self.username, "password": self._password},
                timeout=self.timeout,
            )
            # Zero out password from memory after auth attempt
            self._password = None

            if resp.status_code == 200:
                self._token = resp.text.strip('"')
                self._session.headers.update({
                    "Authorization": self._token,
                    "Content-Type": "application/json",
                })
                self._authenticated = True
                logger.info("Authenticated to CyberArk PVWA")
                return True
            elif resp.status_code == 401:
                raise AuthenticationError("Invalid credentials")
            elif resp.status_code == 403:
                raise PermissionDeniedError("Account lacks login permissions")
            else:
                raise CyberArkError(f"Auth failed: {_safe_error(resp)}")
        except requests.exceptions.SSLError:
            raise CyberArkError("SSL certificate validation failed")
        except requests.exceptions.ConnectionError:
            raise CyberArkError(f"Cannot connect to {self.base_url}")
        except requests.exceptions.Timeout:
            raise CyberArkError("Connection timeout")

    def disconnect(self):
        if self._session and self._authenticated:
            try:
                url = f"{self.base_url}{self.API_BASE}/Auth/Logoff"
                self._session.post(url)
            except Exception:
                pass
            finally:
                self._session.close()
                self._session = None
                self._token = None
                self._authenticated = False

    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, *exc):
        self.disconnect()
        return False

    @property
    def is_authenticated(self) -> bool:
        return self._authenticated

    def _reauth(self):
        """Re-authenticate on 401 (session expiry)."""
        logger.info("Session expired, re-authenticating...")
        self._authenticated = False
        if self._password is None:
            # Password was zeroed — read from env
            self._password = os.environ.get("CYBERARK_PASSWORD", "")
        self.connect()

    # ── low-level API ────────────────────────────────────────────

    def _get(self, endpoint: str, params: dict = None) -> dict:
        if not self._authenticated:
            raise CyberArkError("Not authenticated")
        url = f"{self.base_url}{self.API_BASE}{endpoint}"
        time.sleep(self.rate_limit)
        resp = self._session.get(url, params=params, timeout=self.timeout)
        if resp.status_code == 200:
            return resp.json()
        if resp.status_code == 401:
            self._reauth()
            resp = self._session.get(url, params=params, timeout=self.timeout)
            if resp.status_code == 200:
                return resp.json()
            raise AuthenticationError("Session re-auth failed")
        if resp.status_code == 403:
            raise PermissionDeniedError(f"Insufficient permissions: {endpoint}")
        if resp.status_code == 404:
            return {}
        raise CyberArkError(_safe_error(resp))

    def _post(self, endpoint: str, payload: dict = None) -> dict:
        if not self._authenticated:
            raise CyberArkError("Not authenticated")
        url = f"{self.base_url}{self.API_BASE}{endpoint}"
        time.sleep(self.rate_limit)
        resp = self._session.post(url, json=payload or {}, timeout=self.timeout)
        if resp.status_code in (200, 201):
            return resp.json() if resp.text else {}
        if resp.status_code == 401:
            self._reauth()
            resp = self._session.post(url, json=payload or {}, timeout=self.timeout)
            if resp.status_code in (200, 201):
                return resp.json() if resp.text else {}
            raise AuthenticationError("Session re-auth failed")
        if resp.status_code == 403:
            raise PermissionDeniedError(f"Insufficient permissions: {endpoint}")
        raise CyberArkError(_safe_error(resp))

    def _put(self, endpoint: str, payload: dict = None) -> dict:
        if not self._authenticated:
            raise CyberArkError("Not authenticated")
        url = f"{self.base_url}{self.API_BASE}{endpoint}"
        time.sleep(self.rate_limit)
        resp = self._session.put(url, json=payload or {}, timeout=self.timeout)
        if resp.status_code == 200:
            return resp.json() if resp.text else {}
        if resp.status_code == 401:
            self._reauth()
            resp = self._session.put(url, json=payload or {}, timeout=self.timeout)
            if resp.status_code == 200:
                return resp.json() if resp.text else {}
        raise CyberArkError(_safe_error(resp))

    def _patch(self, endpoint: str, payload: dict = None) -> dict:
        if not self._authenticated:
            raise CyberArkError("Not authenticated")
        url = f"{self.base_url}{self.API_BASE}{endpoint}"
        time.sleep(self.rate_limit)
        resp = self._session.patch(url, json=payload or {}, timeout=self.timeout)
        if resp.status_code == 200:
            return resp.json() if resp.text else {}
        if resp.status_code == 401:
            self._reauth()
            resp = self._session.patch(url, json=payload or {}, timeout=self.timeout)
            if resp.status_code == 200:
                return resp.json() if resp.text else {}
        raise CyberArkError(_safe_error(resp))

    def _delete(self, endpoint: str) -> bool:
        if not self._authenticated:
            raise CyberArkError("Not authenticated")
        url = f"{self.base_url}{self.API_BASE}{endpoint}"
        time.sleep(self.rate_limit)
        resp = self._session.delete(url, timeout=self.timeout)
        return resp.status_code in (200, 204)

    # ── account operations ────────────────────────────────────────

    def get_accounts(self, **filters) -> List[Dict[str, Any]]:
        """Retrieve all accounts with pagination using count-based loop."""
        all_accounts = []
        offset = 0
        total = None
        while True:
            params = {"limit": self.batch_size, "offset": offset, **filters}
            resp = self._get("/Accounts", params)
            accounts = resp.get("value", [])
            if total is None:
                total = resp.get("count", 0)
            if not accounts:
                break
            all_accounts.extend(accounts)
            if total and len(all_accounts) >= total:
                break
            offset += len(accounts)
            time.sleep(self.rate_limit)
        logger.info(f"Retrieved {len(all_accounts)} accounts")
        return all_accounts

    def get_account_details(self, account_id: str) -> dict:
        """Get full account details including linked accounts."""
        return self._get(f"/Accounts/{account_id}")

    def retrieve_password(self, account_id: str, reason: str = "Migration") -> str:
        """Retrieve the actual password/secret value for an account.

        Calls POST /Accounts/{id}/Password/Retrieve which requires
        UseAccounts + RetrieveAccounts permissions.
        """
        resp = self._post(
            f"/Accounts/{account_id}/Password/Retrieve",
            {"reason": reason},
        )
        # Response is the password as a plain string (quoted)
        if isinstance(resp, str):
            return resp.strip('"')
        # Some versions return JSON
        return resp.get("Content", resp.get("Password", ""))

    def update_account(self, account_id: str, operations: list) -> dict:
        """Update account properties via PATCH /Accounts/{id}.

        Args:
            operations: List of JSON Patch operations, e.g.
                [{"op": "replace", "path": "/secretManagement/automaticManagementEnabled", "value": False}]
        """
        return self._patch(f"/Accounts/{account_id}", operations)

    def disable_account_management(self, account_id: str) -> dict:
        """Disable CPM automatic management for a single account (freeze)."""
        return self._patch(f"/Accounts/{account_id}", [
            {
                "op": "replace",
                "path": "/secretManagement/automaticManagementEnabled",
                "value": False,
            },
            {
                "op": "replace",
                "path": "/secretManagement/manualManagementReason",
                "value": "Migration in progress",
            },
        ])

    def enable_account_management(self, account_id: str) -> dict:
        """Re-enable CPM automatic management for a single account (unfreeze)."""
        return self._patch(f"/Accounts/{account_id}", [
            {
                "op": "replace",
                "path": "/secretManagement/automaticManagementEnabled",
                "value": True,
            },
            {
                "op": "remove",
                "path": "/secretManagement/manualManagementReason",
            },
        ])

    # ── safe operations ───────────────────────────────────────────

    def get_safes(self, include_system: bool = False) -> List[Dict[str, Any]]:
        """Get all safes, filtering out system safes by default."""
        resp = self._get("/Safes")
        safes = resp.get("value", resp.get("Safes", []))
        if not include_system:
            safes = [
                s for s in safes
                if s.get("SafeName", s.get("safeName", "")) not in SYSTEM_SAFES
            ]
        return safes

    def get_safe_members(self, safe_name: str) -> List[Dict[str, Any]]:
        """Get members of a safe with proper URL encoding."""
        encoded = quote(safe_name, safe="")
        resp = self._get(f"/Safes/{encoded}/Members")
        return resp.get("value", resp.get("members", []))

    def update_safe_member(self, safe_name: str, member_name: str, permissions: dict) -> dict:
        """Update a safe member's permissions."""
        encoded_safe = quote(safe_name, safe="")
        encoded_member = quote(member_name, safe="")
        return self._put(f"/Safes/{encoded_safe}/Members/{encoded_member}", permissions)

    # ── platform operations ───────────────────────────────────────

    def get_platforms(self) -> List[Dict[str, Any]]:
        """Get platforms. Tries v12+ endpoint first, falls back to legacy."""
        try:
            resp = self._get("/Platforms/Targets")
            return resp.get("Platforms", resp.get("value", []))
        except CyberArkError:
            resp = self._get("/Platforms")
            return resp.get("Platforms", [])

    def export_platform(self, platform_id: str) -> bytes:
        """Export a platform as a ZIP package."""
        url = f"{self.base_url}{self.API_BASE}/Platforms/{quote(platform_id, safe='')}/Export"
        resp = self._session.post(url, timeout=self.timeout)
        if resp.status_code == 200:
            return resp.content
        raise CyberArkError(f"Platform export failed: {_safe_error(resp)}")

    # ── application (CCP/AAM) operations ──────────────────────────

    def get_applications(self) -> List[Dict[str, Any]]:
        """List all registered CCP/AAM applications."""
        try:
            resp = self._get("/Applications")
            return resp.get("application", resp.get("value", []))
        except PermissionDeniedError:
            logger.warning("Cannot list applications (permission denied)")
            return []

    def get_application_auth(self, app_id: str) -> List[Dict[str, Any]]:
        """Get authentication methods for a CCP application."""
        encoded = quote(app_id, safe="")
        try:
            resp = self._get(f"/Applications/{encoded}/Authentications")
            return resp.get("authentication", resp.get("value", []))
        except CyberArkError:
            return []

    # ── audit & monitoring ────────────────────────────────────────

    def get_audit_logs(self, days: int = 90, **filters) -> List[Dict[str, Any]]:
        """Get activity logs with proper pagination and date filtering."""
        all_logs = []
        offset = 0
        while True:
            params = {"Limit": min(1000, self.batch_size), "Offset": offset, **filters}
            try:
                resp = self._get("/Activities", params)
                logs = resp.get("Activities", resp.get("value", []))
                if not logs:
                    break
                all_logs.extend(logs)
                offset += len(logs)
                if len(logs) < 1000:
                    break
                time.sleep(self.rate_limit)
            except PermissionDeniedError:
                logger.warning("Cannot access audit logs")
                break
        return all_logs

    def get_account_activity(self, account_id: str) -> List[Dict[str, Any]]:
        """Get activity logs for a specific account."""
        try:
            resp = self._get(f"/Accounts/{account_id}/Activities")
            return resp.get("Activities", resp.get("value", []))
        except Exception:
            return []

    def get_system_health(self) -> Dict[str, Any]:
        health = {}
        try:
            info = self._get("/Server/Verify")
            health["version"] = info.get("PVWAVersion", info.get("ServerID", ""))
            health["server_name"] = info.get("ServerName", "")
        except Exception:
            try:
                info = self._get("/Server")
                health["version"] = info.get("ServerID", "")
            except Exception:
                pass
        try:
            health["components"] = self._get("/ComponentsMonitoringDetails")
        except Exception:
            pass
        return health

    # ── health check ──────────────────────────────────────────────

    def preflight_check(self) -> Dict[str, Any]:
        """Run pre-flight validation."""
        results = {
            "connectivity": False,
            "ssl_valid": False,
            "authenticated": False,
            "can_list_safes": False,
            "can_list_accounts": False,
            "can_retrieve_passwords": False,
            "can_list_applications": False,
            "version": None,
            "errors": [],
        }
        try:
            requests.get(self.base_url, verify=self.verify_ssl, timeout=self.timeout)
            results["connectivity"] = True
            results["ssl_valid"] = True
        except requests.exceptions.SSLError:
            results["errors"].append("SSL validation failed")
            return results
        except Exception:
            results["errors"].append(f"Cannot connect to {self.base_url}")
            return results

        try:
            self.connect()
            results["authenticated"] = True
        except Exception as e:
            results["errors"].append(str(e))
            return results

        try:
            safes = self.get_safes()
            results["can_list_safes"] = len(safes) > 0
        except Exception as e:
            results["errors"].append(f"Safe listing failed: {e}")

        try:
            self._get("/Accounts", {"limit": 1})
            results["can_list_accounts"] = True
        except Exception as e:
            results["errors"].append(f"Account listing failed: {e}")

        try:
            apps = self.get_applications()
            results["can_list_applications"] = True
        except Exception:
            pass

        health = self.get_system_health()
        results["version"] = health.get("version")

        return results

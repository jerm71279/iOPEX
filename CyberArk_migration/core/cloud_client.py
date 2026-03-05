"""CyberArk Privilege Cloud REST API client.

Supports two authentication methods:
  1. OAuth2 via CyberArk Identity Security Platform (modern tenants)
  2. Legacy PVWA /Auth/CyberArk/Logon (Privilege Cloud Standard)

Provides safe creation, account import, permission management, platform
operations, and post-migration validation.
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


def _safe_error(resp: requests.Response, max_len: int = 200) -> str:
    """Sanitize HTTP error response — never leak credentials."""
    text = (resp.text or "")[:max_len]
    text = re.sub(r'"password"\s*:\s*"[^"]*"', '"password":"***"', text)
    text = re.sub(r'"client_secret"\s*:\s*"[^"]*"', '"client_secret":"***"', text)
    text = re.sub(r'"secret"\s*:\s*"[^"]*"', '"secret":"***"', text)
    return f"HTTP {resp.status_code}: {text}"


class CloudError(Exception):
    """Base Privilege Cloud API error."""


class CloudAuthError(CloudError):
    """Authentication failed."""


class CloudClient:
    """CyberArk Privilege Cloud REST API client.

    Supports OAuth2 (Identity) and legacy auth methods.

    Usage:
        with CloudClient(config) as client:
            client.create_safe("MigratedSafe01", {...})
            client.import_account({...})
    """

    API_BASE = "/PasswordVault/api"

    def __init__(self, config: dict):
        self.base_url = config["base_url"].rstrip("/")
        self.verify_ssl = config.get("verify_ssl", True)
        self.timeout = config.get("timeout", 30)
        self.max_retries = config.get("max_retries", 3)
        self.retry_delay = config.get("retry_delay", 1.0)
        self.rate_limit = config.get("rate_limit", 0.1)
        self.batch_size = min(config.get("batch_size", 500), 1000)

        # Auth method: "oauth2" (modern) or "legacy" (PVWA logon)
        self.auth_method = config.get("auth_method", "oauth2")

        # OAuth2 credentials (modern Privilege Cloud)
        self.identity_url = config.get(
            "identity_url",
            os.environ.get("PCLOUD_IDENTITY_URL", ""),
        )
        self.client_id = (
            os.environ.get("PCLOUD_CLIENT_ID")
            or config.get("client_id", "")
        )
        self._client_secret = (
            os.environ.get("PCLOUD_CLIENT_SECRET")
            or config.get("client_secret", "")
        )

        # Legacy credentials
        self.username = (
            os.environ.get("PCLOUD_USERNAME")
            or config.get("username", "")
        )
        self._password = (
            os.environ.get("PCLOUD_PASSWORD")
            or config.get("password", "")
        )

        self._session: Optional[requests.Session] = None
        self._token: Optional[str] = None
        self._token_type: str = "Bearer"
        self._authenticated = False

    def _create_session(self) -> requests.Session:
        if not self.base_url.startswith("https://"):
            raise CloudError("Privilege Cloud must use HTTPS")
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
        self._session = self._create_session()

        if self.auth_method == "oauth2":
            return self._connect_oauth2()
        return self._connect_legacy()

    def _connect_oauth2(self) -> bool:
        """Authenticate via CyberArk Identity Security Platform (OAuth2)."""
        if not self.identity_url:
            raise CloudAuthError(
                "identity_url required for OAuth2 auth. "
                "Set privilege_cloud.identity_url or PCLOUD_IDENTITY_URL env var. "
                "Format: https://<tenant>.id.cyberark.cloud"
            )

        token_url = f"{self.identity_url.rstrip('/')}/oauth2/platformtoken"
        try:
            resp = self._session.post(
                token_url,
                data={
                    "grant_type": "client_credentials",
                    "client_id": self.client_id,
                    "client_secret": self._client_secret,
                },
                timeout=self.timeout,
            )
            # Zero out secret after use
            self._client_secret = None

            if resp.status_code == 200:
                data = resp.json()
                self._token = data["access_token"]
                self._token_type = data.get("token_type", "Bearer")
                self._session.headers.update({
                    "Authorization": f"{self._token_type} {self._token}",
                    "Content-Type": "application/json",
                })
                self._authenticated = True
                logger.info("Authenticated to Privilege Cloud via OAuth2")
                return True
            raise CloudAuthError(f"OAuth2 auth failed: {_safe_error(resp)}")
        except requests.exceptions.ConnectionError:
            raise CloudError(f"Cannot connect to {self.identity_url}")
        except requests.exceptions.Timeout:
            raise CloudError("Identity platform connection timeout")

    def _connect_legacy(self) -> bool:
        """Authenticate via legacy PVWA /Auth/CyberArk/Logon."""
        url = f"{self.base_url}{self.API_BASE}/Auth/CyberArk/Logon"
        try:
            resp = self._session.post(
                url,
                json={"username": self.username, "password": self._password},
                timeout=self.timeout,
            )
            self._password = None

            if resp.status_code == 200:
                self._token = resp.text.strip('"')
                self._token_type = ""
                self._session.headers.update({
                    "Authorization": self._token,
                    "Content-Type": "application/json",
                })
                self._authenticated = True
                logger.info("Authenticated to Privilege Cloud (legacy)")
                return True
            raise CloudAuthError(f"Legacy auth failed: {_safe_error(resp)}")
        except requests.exceptions.ConnectionError:
            raise CloudError(f"Cannot connect to {self.base_url}")
        except requests.exceptions.Timeout:
            raise CloudError("Connection timeout")

    def _reauth(self):
        """Re-authenticate on 401 (session/token expiry)."""
        logger.info("Token expired, re-authenticating...")
        self._authenticated = False
        if self.auth_method == "oauth2":
            self._client_secret = os.environ.get("PCLOUD_CLIENT_SECRET", "")
        else:
            self._password = os.environ.get("PCLOUD_PASSWORD", "")
        self.connect()

    def disconnect(self):
        if self._session and self._authenticated:
            try:
                if self.auth_method == "legacy":
                    self._session.post(f"{self.base_url}{self.API_BASE}/Auth/Logoff")
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

    # ── low-level API ─────────────────────────────────────────────

    def _request(self, method: str, endpoint: str, **kwargs) -> requests.Response:
        if not self._authenticated:
            raise CloudError("Not authenticated")
        url = f"{self.base_url}{self.API_BASE}{endpoint}"
        time.sleep(self.rate_limit)
        resp = self._session.request(method, url, timeout=self.timeout, **kwargs)

        if resp.status_code == 401:
            self._reauth()
            resp = self._session.request(method, url, timeout=self.timeout, **kwargs)
            if resp.status_code == 401:
                raise CloudAuthError("Re-authentication failed")

        return resp

    def _get(self, endpoint: str, params: dict = None) -> dict:
        resp = self._request("GET", endpoint, params=params)
        if resp.status_code == 200:
            return resp.json()
        if resp.status_code == 404:
            return {}
        raise CloudError(_safe_error(resp))

    def _post(self, endpoint: str, payload: dict = None) -> dict:
        resp = self._request("POST", endpoint, json=payload or {})
        if resp.status_code in (200, 201):
            # Password retrieval returns plain text
            try:
                return resp.json() if resp.text else {}
            except ValueError:
                return {"Content": resp.text.strip('"')}
        if resp.status_code == 409:
            raise CloudError(f"Conflict (already exists)")
        raise CloudError(_safe_error(resp))

    def _put(self, endpoint: str, payload: dict = None) -> dict:
        resp = self._request("PUT", endpoint, json=payload or {})
        if resp.status_code == 200:
            return resp.json() if resp.text else {}
        raise CloudError(_safe_error(resp))

    def _patch(self, endpoint: str, payload: dict = None) -> dict:
        resp = self._request("PATCH", endpoint, json=payload or {})
        if resp.status_code == 200:
            return resp.json() if resp.text else {}
        raise CloudError(_safe_error(resp))

    def _delete(self, endpoint: str) -> bool:
        resp = self._request("DELETE", endpoint)
        return resp.status_code in (200, 204)

    # ── safe operations ──────────────────────────────────────────

    def create_safe(self, safe_name: str, properties: dict = None) -> dict:
        """Create a safe with all required properties.

        Args:
            safe_name: Name of the safe to create
            properties: Dict with optional keys:
                ManagingCPM, NumberOfDaysRetention, NumberOfVersionsRetention,
                OLACEnabled, Description, Location
        """
        payload = {"SafeName": safe_name}
        if properties:
            payload.update(properties)
        # Ensure critical defaults
        payload.setdefault("ManagingCPM", "PasswordManager")
        payload.setdefault("NumberOfVersionsRetention", 5)
        payload.setdefault("NumberOfDaysRetention", 7)
        return self._post("/Safes", payload)

    def get_safe(self, safe_name: str) -> dict:
        encoded = quote(safe_name, safe="")
        return self._get(f"/Safes/{encoded}")

    def safe_exists(self, safe_name: str) -> bool:
        try:
            result = self.get_safe(safe_name)
            return bool(result.get("SafeName") or result.get("safeName"))
        except CloudError:
            return False

    def get_safes(self) -> List[Dict[str, Any]]:
        resp = self._get("/Safes")
        return resp.get("value", resp.get("Safes", []))

    def add_safe_member(self, safe_name: str, member: dict) -> dict:
        """Add a member to a safe with individual permissions."""
        encoded = quote(safe_name, safe="")
        return self._post(f"/Safes/{encoded}/Members", member)

    def update_safe_member(self, safe_name: str, member_name: str, permissions: dict) -> dict:
        """Update an existing safe member's permissions."""
        encoded_safe = quote(safe_name, safe="")
        encoded_member = quote(member_name, safe="")
        return self._put(f"/Safes/{encoded_safe}/Members/{encoded_member}", permissions)

    # ── account operations ───────────────────────────────────────

    def import_account(self, account_data: dict) -> dict:
        """Import a single account into Privilege Cloud."""
        return self._post("/Accounts", account_data)

    def get_accounts(self, **filters) -> List[Dict[str, Any]]:
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
        return all_accounts

    def verify_account(self, account_id: str) -> dict:
        """Trigger password verification (heartbeat) for an account."""
        return self._post(f"/Accounts/{account_id}/Verify")

    def get_account_details(self, account_id: str) -> dict:
        return self._get(f"/Accounts/{account_id}")

    def retrieve_password(self, account_id: str, reason: str = "Validation") -> str:
        """Retrieve a password from Privilege Cloud (requires reason)."""
        resp = self._post(
            f"/Accounts/{account_id}/Password/Retrieve",
            {"reason": reason},
        )
        if isinstance(resp, dict):
            return resp.get("Content", resp.get("Password", ""))
        return str(resp).strip('"')

    def delete_account(self, account_id: str) -> bool:
        """Delete an account (for rollback)."""
        return self._delete(f"/Accounts/{account_id}")

    # ── linked accounts ──────────────────────────────────────────

    def link_account(self, account_id: str, linked_account: dict) -> dict:
        """Link a logon/reconcile/index account."""
        return self._post(f"/Accounts/{account_id}/LinkAccount", linked_account)

    # ── platform operations ──────────────────────────────────────

    def get_platforms(self) -> List[Dict[str, Any]]:
        try:
            resp = self._get("/Platforms/Targets")
            return resp.get("Platforms", resp.get("value", []))
        except CloudError:
            resp = self._get("/Platforms")
            return resp.get("Platforms", [])

    def import_platform(self, platform_zip: bytes) -> dict:
        """Import a platform package (ZIP) into Privilege Cloud."""
        url = f"{self.base_url}{self.API_BASE}/Platforms/Import"
        resp = self._session.post(
            url,
            files={"ImportFile": ("platform.zip", platform_zip, "application/zip")},
            timeout=self.timeout,
        )
        if resp.status_code in (200, 201):
            return resp.json() if resp.text else {}
        raise CloudError(_safe_error(resp))

    # ── health check ─────────────────────────────────────────────

    def preflight_check(self) -> Dict[str, Any]:
        results = {
            "connectivity": False,
            "authenticated": False,
            "can_list_safes": False,
            "can_list_accounts": False,
            "can_create_safes": False,
            "errors": [],
        }
        try:
            requests.get(self.base_url, verify=self.verify_ssl, timeout=self.timeout)
            results["connectivity"] = True
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
            self.get_safes()
            results["can_list_safes"] = True
        except Exception as e:
            results["errors"].append(f"Safe listing failed: {e}")

        try:
            self._get("/Accounts", {"limit": 1})
            results["can_list_accounts"] = True
        except Exception as e:
            results["errors"].append(f"Account listing failed: {e}")

        return results

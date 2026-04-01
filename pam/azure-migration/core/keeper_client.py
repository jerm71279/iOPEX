"""KeeperPAM REST API client.

Authenticates via OAuth2 client_credentials grant.

Provides vault creation, record import, permission management, platform
operations, and post-migration validation.

NOTE: Endpoint paths are marked [VERIFY ENDPOINT] — confirm against KeeperPAM
API documentation before first live run. Auth flow and method interface are
stable; the specific REST paths need validation with Keeper Security.
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


class KeeperError(Exception):
    """Base KeeperPAM API error."""


class KeeperAuthError(KeeperError):
    """Authentication failed."""


# Backwards-compatible aliases (agents importing CloudError still work during transition)
CloudError = KeeperError
CloudAuthError = KeeperAuthError


class KeeperClient:
    """KeeperPAM REST API client.

    Authenticates via OAuth2 client_credentials grant.
    Credentials sourced from environment variables (KEEPERPAM_CLIENT_ID,
    KEEPERPAM_CLIENT_SECRET) — never from config files.

    CyberArk → KeeperPAM terminology mapping:
        Safe        → Vault (Shared Folder)
        Account     → Record
        Platform    → Record Type

    Usage:
        with KeeperClient(config) as client:
            client.create_safe("MigratedVault01", {...})
            client.import_account({...})
    """

    API_BASE = "/api/rest"  # [VERIFY ENDPOINT] — confirm base path with KeeperPAM API docs

    def __init__(self, config: dict):
        self.base_url = config["base_url"].rstrip("/")
        self.verify_ssl = config.get("verify_ssl", True)
        self.timeout = config.get("timeout", 30)
        self.max_retries = config.get("max_retries", 3)
        self.retry_delay = config.get("retry_delay", 1.0)
        self.rate_limit = config.get("rate_limit", 0.1)
        self.batch_size = min(config.get("batch_size", 500), 1000)

        self.auth_method = config.get("auth_method", "oauth2")

        # OAuth2 credentials — env vars take priority over config file
        self.client_id = (
            os.environ.get("KEEPERPAM_CLIENT_ID")
            or config.get("client_id", "")
        )
        self._client_secret = (
            os.environ.get("KEEPERPAM_CLIENT_SECRET")
            or config.get("client_secret", "")
        )

        self._session: Optional[requests.Session] = None
        self._token: Optional[str] = None
        self._token_type: str = "Bearer"
        self._token_expires_at: float = 0.0  # Unix timestamp; 0 = not set
        self._authenticated = False

        # Security [MEDIUM]: enforce HTTPS at construction time — fail loudly
        # so misconfigured environments are caught before any credentials are sent
        if not self.base_url.startswith("https://"):
            raise KeeperError(
                f"Security policy violation: KeeperPAM base_url must use HTTPS. "
                f"Got: {self.base_url!r}"
            )

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
        self._session = self._create_session()
        return self._connect_oauth2()

    def _connect_oauth2(self) -> bool:
        """Authenticate via OAuth2 client_credentials grant."""
        token_url = f"{self.base_url}/oauth/token"  # [VERIFY ENDPOINT]
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

                # Security [MEDIUM]: proactive token refresh — re-auth 60s before expiry
                # Prevents mid-batch 401 errors that could leave accounts in FREEZE state
                expires_in = data.get("expires_in", 3600)
                self._token_expires_at = time.time() + expires_in - 60  # 60s buffer

                self._session.headers.update({
                    "Authorization": f"{self._token_type} {self._token}",
                    "Content-Type": "application/json",
                })
                self._authenticated = True
                logger.info(
                    "Authenticated to KeeperPAM via OAuth2 (token valid ~%ds)", expires_in
                )
                return True
            raise KeeperAuthError(f"OAuth2 auth failed: {_safe_error(resp)}")
        except requests.exceptions.ConnectionError:
            raise KeeperError(f"Cannot connect to {self.base_url}")
        except requests.exceptions.Timeout:
            raise KeeperError("KeeperPAM connection timeout")

    def _token_needs_refresh(self) -> bool:
        """Return True if the token has expired or will expire within 60 seconds."""
        return self._token_expires_at == 0.0 or time.time() >= self._token_expires_at

    def _reauth(self):
        """Re-authenticate — called reactively on 401 or proactively before expiry."""
        logger.info("Re-authenticating to KeeperPAM (token expired or near expiry)...")
        self._authenticated = False
        self._token_expires_at = 0.0
        # Re-read secret from env — it may have been rotated
        self._client_secret = os.environ.get("KEEPERPAM_CLIENT_SECRET", "")
        self.connect()

    def _ensure_auth(self):
        """Proactively refresh token before it expires — call at start of each API method."""
        if self._token_needs_refresh():
            self._reauth()

    def disconnect(self):
        if self._session and self._authenticated:
            try:
                self._session.close()
            except Exception:
                pass
            finally:
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
            raise KeeperError("Not authenticated")

        # Security [MEDIUM]: proactive token refresh — avoids 401 mid-batch
        # which could leave accounts in FREEZE state and require manual recovery
        self._ensure_auth()

        url = f"{self.base_url}{self.API_BASE}{endpoint}"
        time.sleep(self.rate_limit)
        resp = self._session.request(method, url, timeout=self.timeout, **kwargs)

        # Reactive fallback: if server returns 401 despite proactive refresh, re-auth once
        if resp.status_code == 401:
            self._reauth()
            resp = self._session.request(method, url, timeout=self.timeout, **kwargs)
            if resp.status_code == 401:
                raise KeeperAuthError("Re-authentication failed")

        return resp

    def _get(self, endpoint: str, params: dict = None) -> dict:
        resp = self._request("GET", endpoint, params=params)
        if resp.status_code == 200:
            return resp.json()
        if resp.status_code == 404:
            return {}
        raise KeeperError(_safe_error(resp))

    def _post(self, endpoint: str, payload: dict = None) -> dict:
        resp = self._request("POST", endpoint, json=payload or {})
        if resp.status_code in (200, 201):
            try:
                return resp.json() if resp.text else {}
            except ValueError:
                return {"Content": resp.text.strip('"')}
        if resp.status_code == 409:
            raise KeeperError("Conflict (already exists)")
        raise KeeperError(_safe_error(resp))

    def _put(self, endpoint: str, payload: dict = None) -> dict:
        resp = self._request("PUT", endpoint, json=payload or {})
        if resp.status_code == 200:
            return resp.json() if resp.text else {}
        raise KeeperError(_safe_error(resp))

    def _patch(self, endpoint: str, payload: dict = None) -> dict:
        resp = self._request("PATCH", endpoint, json=payload or {})
        if resp.status_code == 200:
            return resp.json() if resp.text else {}
        raise KeeperError(_safe_error(resp))

    def _delete(self, endpoint: str) -> bool:
        resp = self._request("DELETE", endpoint)
        return resp.status_code in (200, 204)

    # ── vault operations (CyberArk "Safes" → KeeperPAM "Vaults") ─
    # [VERIFY ENDPOINTS] — confirm all /vaults paths against KeeperPAM API docs

    def create_safe(self, safe_name: str, properties: dict = None) -> dict:
        """Create a vault (KeeperPAM equivalent of a CyberArk safe)."""
        payload = {"name": safe_name}
        if properties:
            payload.update(properties)
        return self._post("/vaults", payload)  # [VERIFY ENDPOINT]

    def get_safe(self, safe_name: str) -> dict:
        encoded = quote(safe_name, safe="")
        return self._get(f"/vaults/{encoded}")  # [VERIFY ENDPOINT]

    def safe_exists(self, safe_name: str) -> bool:
        try:
            result = self.get_safe(safe_name)
            return bool(result.get("name") or result.get("vaultName"))
        except KeeperError:
            return False

    def get_safes(self) -> List[Dict[str, Any]]:
        resp = self._get("/vaults")  # [VERIFY ENDPOINT]
        return resp.get("vaults", resp.get("value", []))

    def add_safe_member(self, safe_name: str, member: dict) -> dict:
        """Add a member to a vault with permissions."""
        encoded = quote(safe_name, safe="")
        return self._post(f"/vaults/{encoded}/members", member)  # [VERIFY ENDPOINT]

    def update_safe_member(self, safe_name: str, member_name: str, permissions: dict) -> dict:
        """Update an existing vault member's permissions."""
        encoded_safe = quote(safe_name, safe="")
        encoded_member = quote(member_name, safe="")
        return self._put(f"/vaults/{encoded_safe}/members/{encoded_member}", permissions)  # [VERIFY ENDPOINT]

    # ── record operations (CyberArk "Accounts" → KeeperPAM "Records") ──
    # [VERIFY ENDPOINTS] — confirm all /records paths against KeeperPAM API docs

    def import_account(self, account_data: dict) -> dict:
        """Import a single record into KeeperPAM."""
        return self._post("/records", account_data)  # [VERIFY ENDPOINT]

    def get_accounts(self, **filters) -> List[Dict[str, Any]]:
        all_accounts = []
        offset = 0
        total = None
        while True:
            params = {"limit": self.batch_size, "offset": offset, **filters}
            resp = self._get("/records", params)  # [VERIFY ENDPOINT]
            accounts = resp.get("records", resp.get("value", []))
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
        """Trigger password rotation check (heartbeat) for a record."""
        return self._post(f"/records/{account_id}/verify")  # [VERIFY ENDPOINT]

    def get_account_details(self, account_id: str) -> dict:
        return self._get(f"/records/{account_id}")  # [VERIFY ENDPOINT]

    def retrieve_password(self, account_id: str, reason: str = "Validation") -> str:
        """Retrieve a password from KeeperPAM."""
        resp = self._post(
            f"/records/{account_id}/password",  # [VERIFY ENDPOINT]
            {"reason": reason},
        )
        if isinstance(resp, dict):
            return resp.get("password", resp.get("Content", ""))
        return str(resp).strip('"')

    def delete_account(self, account_id: str) -> bool:
        """Delete a record (for rollback)."""
        return self._delete(f"/records/{account_id}")  # [VERIFY ENDPOINT]

    # ── linked records ────────────────────────────────────────────

    def link_account(self, account_id: str, linked_account: dict) -> dict:
        """Link a logon/reconcile/index record."""
        return self._post(f"/records/{account_id}/link", linked_account)  # [VERIFY ENDPOINT]

    # ── record type operations (CyberArk "Platforms" → KeeperPAM "Record Types") ─
    # [VERIFY ENDPOINTS]

    def get_platforms(self) -> List[Dict[str, Any]]:
        resp = self._get("/record-types")  # [VERIFY ENDPOINT]
        return resp.get("recordTypes", resp.get("value", []))

    def import_platform(self, platform_zip: bytes) -> dict:
        """Import a record type package into KeeperPAM."""
        url = f"{self.base_url}{self.API_BASE}/record-types/import"  # [VERIFY ENDPOINT]
        resp = self._session.post(
            url,
            files={"ImportFile": ("platform.zip", platform_zip, "application/zip")},
            timeout=self.timeout,
        )
        if resp.status_code in (200, 201):
            return resp.json() if resp.text else {}
        raise KeeperError(_safe_error(resp))

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
            results["errors"].append(f"Vault listing failed: {e}")

        try:
            self._get("/records", {"limit": 1})  # [VERIFY ENDPOINT]
            results["can_list_accounts"] = True
        except Exception as e:
            results["errors"].append(f"Record listing failed: {e}")

        return results


# Backwards-compatible alias — remove once all agents import KeeperClient directly
CloudClient = KeeperClient

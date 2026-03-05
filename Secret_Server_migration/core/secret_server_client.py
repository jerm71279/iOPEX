"""Delinea Secret Server REST API client.

Supports two authentication methods:
  1. OAuth2 client credentials (modern, recommended)
  2. Username/password token auth (legacy)

Provides folder management, secret operations, template management,
folder permissions, user/group queries, and post-migration validation.

API base: /api/v1/
Docs: https://docs.delinea.com/online-help/secret-server/api-scripting/rest/index.htm
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


class SSError(Exception):
    """Base Secret Server API error."""


class SSAuthError(SSError):
    """Authentication failed."""


class SecretServerClient:
    """Delinea Secret Server REST API client.

    Supports OAuth2 and username/password authentication.

    Usage:
        with SecretServerClient(config) as client:
            client.create_folder("MigratedAccounts", parent_id=1)
            client.create_secret({...})
    """

    API_BASE = "/api/v1"

    def __init__(self, config: dict):
        self.base_url = config["base_url"].rstrip("/")
        self.verify_ssl = config.get("verify_ssl", True)
        self.timeout = config.get("timeout", 30)
        self.max_retries = config.get("max_retries", 3)
        self.retry_delay = config.get("retry_delay", 1.0)
        self.rate_limit = config.get("rate_limit", 0.1)
        self.batch_size = min(config.get("batch_size", 500), 1000)
        self.default_folder_id = config.get("default_folder_id", -1)
        self.inherit_permissions = config.get("inherit_permissions", True)

        # Auth method: "oauth2" (recommended) or "legacy" (username/password)
        self.auth_method = config.get("auth_method", "oauth2")

        # OAuth2 credentials
        self.client_id = (
            os.environ.get("SS_CLIENT_ID")
            or config.get("client_id", "")
        )
        self._client_secret = (
            os.environ.get("SS_CLIENT_SECRET")
            or config.get("client_secret", "")
        )

        # Legacy credentials (username/password)
        self.username = (
            os.environ.get("SS_USERNAME")
            or config.get("username", "")
        )
        self._password = (
            os.environ.get("SS_PASSWORD")
            or config.get("password", "")
        )

        self._session: Optional[requests.Session] = None
        self._token: Optional[str] = None
        self._token_expiry: float = 0
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
        session.mount("http://", adapter)
        session.verify = self.verify_ssl
        return session

    def connect(self) -> bool:
        self._session = self._create_session()

        if self.auth_method == "oauth2":
            return self._connect_oauth2()
        return self._connect_legacy()

    def _connect_oauth2(self) -> bool:
        """Authenticate via OAuth2 client credentials."""
        token_url = f"{self.base_url}/oauth2/token"
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
                self._token_expiry = time.time() + data.get("expires_in", 3600)
                self._session.headers.update({
                    "Authorization": f"Bearer {self._token}",
                    "Content-Type": "application/json",
                })
                self._authenticated = True
                logger.info("Authenticated to Secret Server via OAuth2")
                return True
            raise SSAuthError(f"OAuth2 auth failed: {_safe_error(resp)}")
        except requests.exceptions.ConnectionError:
            raise SSError(f"Cannot connect to {self.base_url}")
        except requests.exceptions.Timeout:
            raise SSError("Secret Server connection timeout")

    def _connect_legacy(self) -> bool:
        """Authenticate via username/password token endpoint."""
        token_url = f"{self.base_url}/oauth2/token"
        try:
            resp = self._session.post(
                token_url,
                data={
                    "grant_type": "password",
                    "username": self.username,
                    "password": self._password,
                },
                timeout=self.timeout,
            )
            self._password = None

            if resp.status_code == 200:
                data = resp.json()
                self._token = data["access_token"]
                self._token_expiry = time.time() + data.get("expires_in", 3600)
                self._session.headers.update({
                    "Authorization": f"Bearer {self._token}",
                    "Content-Type": "application/json",
                })
                self._authenticated = True
                logger.info("Authenticated to Secret Server (legacy)")
                return True
            raise SSAuthError(f"Legacy auth failed: {_safe_error(resp)}")
        except requests.exceptions.ConnectionError:
            raise SSError(f"Cannot connect to {self.base_url}")
        except requests.exceptions.Timeout:
            raise SSError("Connection timeout")

    def _reauth(self):
        """Re-authenticate on 401 (token expiry)."""
        logger.info("Token expired, re-authenticating...")
        self._authenticated = False
        if self.auth_method == "oauth2":
            self._client_secret = os.environ.get("SS_CLIENT_SECRET", "")
        else:
            self._password = os.environ.get("SS_PASSWORD", "")
        self.connect()

    def disconnect(self):
        if self._session:
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
            raise SSError("Not authenticated")

        # Re-auth proactively if token is about to expire
        if self._token_expiry and time.time() > self._token_expiry - 60:
            self._reauth()

        url = f"{self.base_url}{self.API_BASE}{endpoint}"
        time.sleep(self.rate_limit)
        resp = self._session.request(method, url, timeout=self.timeout, **kwargs)

        if resp.status_code == 401:
            self._reauth()
            resp = self._session.request(method, url, timeout=self.timeout, **kwargs)
            if resp.status_code == 401:
                raise SSAuthError("Re-authentication failed")

        return resp

    def _get(self, endpoint: str, params: dict = None) -> dict:
        resp = self._request("GET", endpoint, params=params)
        if resp.status_code == 200:
            return resp.json()
        if resp.status_code == 404:
            return {}
        raise SSError(_safe_error(resp))

    def _post(self, endpoint: str, payload: dict = None) -> dict:
        resp = self._request("POST", endpoint, json=payload or {})
        if resp.status_code in (200, 201):
            try:
                return resp.json() if resp.text else {}
            except ValueError:
                return {"value": resp.text.strip('"')}
        if resp.status_code == 409:
            raise SSError("Conflict (already exists)")
        raise SSError(_safe_error(resp))

    def _put(self, endpoint: str, payload: dict = None) -> dict:
        resp = self._request("PUT", endpoint, json=payload or {})
        if resp.status_code == 200:
            return resp.json() if resp.text else {}
        raise SSError(_safe_error(resp))

    def _patch(self, endpoint: str, payload: dict = None) -> dict:
        resp = self._request("PATCH", endpoint, json=payload or {})
        if resp.status_code == 200:
            return resp.json() if resp.text else {}
        raise SSError(_safe_error(resp))

    def _delete(self, endpoint: str) -> bool:
        resp = self._request("DELETE", endpoint)
        return resp.status_code in (200, 204)

    # ── folder operations (replaces CyberArk Safes) ──────────────

    def get_folders(self) -> List[Dict[str, Any]]:
        """Get all folders."""
        resp = self._get("/folders", {"filter.parentFolderId": -1, "getAllChildren": True})
        return resp.get("records", [])

    def create_folder(self, name: str, parent_id: int = -1,
                      inherit_permissions: bool = None,
                      inherit_secret_policy: bool = True) -> dict:
        """Create a folder (equivalent to CyberArk Safe creation).

        Args:
            name: Folder name
            parent_id: Parent folder ID (-1 for root)
            inherit_permissions: Inherit parent permissions (default from config)
            inherit_secret_policy: Inherit parent secret policy
        """
        if inherit_permissions is None:
            inherit_permissions = self.inherit_permissions
        return self._post("/folders", {
            "folderName": name,
            "parentFolderId": parent_id,
            "inheritPermissions": inherit_permissions,
            "inheritSecretPolicy": inherit_secret_policy,
        })

    def folder_exists(self, name: str) -> bool:
        """Check if a folder exists by name."""
        try:
            resp = self._get("/folders", {"filter.searchText": name})
            records = resp.get("records", [])
            return any(f.get("folderName") == name for f in records)
        except SSError:
            return False

    def get_folder(self, folder_id: int) -> dict:
        """Get a folder by ID."""
        return self._get(f"/folders/{folder_id}")

    def get_folder_permissions(self, folder_id: int) -> List[Dict[str, Any]]:
        """Get permissions for a folder."""
        resp = self._get(f"/folder-permissions", {"filter.folderId": folder_id})
        return resp.get("records", [])

    def set_folder_permission(self, folder_id: int, permission: dict) -> dict:
        """Add a permission entry to a folder.

        Args:
            folder_id: Target folder ID
            permission: Dict with keys:
                folderId, groupId or userId, folderAccessRoleName,
                secretAccessRoleName
        """
        payload = {"folderId": folder_id}
        payload.update(permission)
        return self._post("/folder-permissions", payload)

    def update_folder_permission(self, permission_id: int, permission: dict) -> dict:
        """Update an existing folder permission."""
        return self._put(f"/folder-permissions/{permission_id}", permission)

    # ── secret operations (replaces CyberArk Accounts) ────────────

    def create_secret(self, secret_data: dict) -> dict:
        """Create a secret (equivalent to CyberArk Account import).

        Args:
            secret_data: Dict with keys:
                name, secretTemplateId, folderId, siteId,
                items (list of {fieldId, itemValue, slug, ...})
        """
        return self._post("/secrets", secret_data)

    def get_secrets(self, **filters) -> List[Dict[str, Any]]:
        """Get secrets with pagination.

        Common filters: filter.searchText, filter.folderId,
        filter.secretTemplateId, filter.includeSubFolders
        """
        all_secrets = []
        skip = 0
        total = None
        while True:
            params = {"take": self.batch_size, "skip": skip, **filters}
            resp = self._get("/secrets", params)
            records = resp.get("records", [])
            if total is None:
                total = resp.get("total", 0)
            if not records:
                break
            all_secrets.extend(records)
            if total and len(all_secrets) >= total:
                break
            skip += len(records)
        return all_secrets

    def get_secret(self, secret_id: int) -> dict:
        """Get full secret details by ID."""
        return self._get(f"/secrets/{secret_id}")

    def get_password(self, secret_id: int) -> str:
        """Retrieve the password field from a secret."""
        resp = self._get(f"/secrets/{secret_id}/fields/password")
        if isinstance(resp, dict):
            return resp.get("value", resp.get("itemValue", ""))
        return str(resp).strip('"')

    def set_password(self, secret_id: int, password: str) -> dict:
        """Set the password field on a secret."""
        return self._put(f"/secrets/{secret_id}/fields/password", {
            "value": password,
        })

    def get_field(self, secret_id: int, field_slug: str) -> str:
        """Retrieve a specific field from a secret."""
        resp = self._get(f"/secrets/{secret_id}/fields/{field_slug}")
        if isinstance(resp, dict):
            return resp.get("value", resp.get("itemValue", ""))
        return str(resp).strip('"')

    def delete_secret(self, secret_id: int) -> bool:
        """Delete a secret (for rollback)."""
        return self._delete(f"/secrets/{secret_id}")

    def heartbeat_secret(self, secret_id: int) -> dict:
        """Trigger a heartbeat (password verification) on a secret."""
        return self._post(f"/secrets/{secret_id}/heartbeat")

    def get_secret_state(self, secret_id: int) -> dict:
        """Get heartbeat/RPC status of a secret."""
        return self._get(f"/secrets/{secret_id}/state")

    # ── template operations (replaces CyberArk Platforms) ─────────

    def get_templates(self) -> List[Dict[str, Any]]:
        """Get all secret templates."""
        resp = self._get("/secret-templates")
        return resp.get("records", [])

    def get_template(self, template_id: int) -> dict:
        """Get a template by ID."""
        return self._get(f"/secret-templates/{template_id}")

    def create_template(self, template_data: dict) -> dict:
        """Create a secret template."""
        return self._post("/secret-templates", template_data)

    # ── user & group operations ───────────────────────────────────

    def get_users(self) -> List[Dict[str, Any]]:
        """Get all users."""
        resp = self._get("/users")
        return resp.get("records", [])

    def get_groups(self) -> List[Dict[str, Any]]:
        """Get all groups."""
        resp = self._get("/groups")
        return resp.get("records", [])

    def get_roles(self) -> List[Dict[str, Any]]:
        """Get all roles."""
        resp = self._get("/roles")
        return resp.get("records", [])

    # ── site/distributed engine ───────────────────────────────────

    def get_sites(self) -> List[Dict[str, Any]]:
        """Get all distributed engine sites."""
        resp = self._get("/distributed-engine/sites")
        return resp.get("records", resp.get("model", []))

    # ── health check ──────────────────────────────────────────────

    def preflight_check(self) -> Dict[str, Any]:
        """Run connectivity and permission checks."""
        results = {
            "connectivity": False,
            "authenticated": False,
            "can_list_folders": False,
            "can_list_secrets": False,
            "can_list_templates": False,
            "server_version": "",
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
            self.get_folders()
            results["can_list_folders"] = True
        except Exception as e:
            results["errors"].append(f"Folder listing failed: {e}")

        try:
            self._get("/secrets", {"take": 1})
            results["can_list_secrets"] = True
        except Exception as e:
            results["errors"].append(f"Secret listing failed: {e}")

        try:
            self.get_templates()
            results["can_list_templates"] = True
        except Exception as e:
            results["errors"].append(f"Template listing failed: {e}")

        try:
            ver = self._get("/version")
            results["server_version"] = ver.get("version", ver.get("model", ""))
        except Exception:
            pass

        return results

"""Multi-Vendor Source Adapters — Canonical PAM Data Model (G-01 Gap Closure).

Provides a unified interface for reading accounts, containers, and platforms
from any PAM vendor. Each adapter normalizes vendor-specific schemas to a
canonical format that downstream agents consume.

Supported sources:
    - CyberArk PAS (PVWA REST API)
    - BeyondTrust Password Safe (REST API v3)
    - Delinea Secret Server (REST API v1)
    - HashiCorp Vault (HTTP API, KV v2)
    - AWS Secrets Manager (boto3)
    - Azure Key Vault (azure-keyvault-secrets)
    - GCP Secret Manager (google-cloud-secret-manager)
"""

import json
import logging
import os
import re
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


# ── Canonical Data Model ────────────────────────────────────────

@dataclass
class NormalizedAccount:
    """Common account representation across all PAM vendors."""
    source_id: str
    source_vendor: str         # cyberark | beyondtrust | secretserver | hashicorp | aws | azure | gcp
    name: str
    username: str
    address: str
    container_name: str        # Safe (CyberArk), Container (BT), Folder (SS), Path (Vault)
    platform_type: str         # Platform ID or equivalent
    secret_type: str = "password"  # password | key | certificate | api_key
    account_type: str = "human"    # human | service | api_key | machine | unknown
    managed: bool = True
    last_accessed: str = ""
    last_modified: str = ""
    properties: Dict[str, Any] = field(default_factory=dict)
    tags: Dict[str, str] = field(default_factory=dict)
    raw: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return asdict(self)

    def to_cyberark_format(self) -> dict:
        """Convert back to CyberArk-style dict for downstream agent compatibility."""
        return {
            "id": self.source_id,
            "name": self.name,
            "userName": self.username,
            "address": self.address,
            "safeName": self.container_name,
            "platformId": self.platform_type,
            "secretType": self.secret_type,
            "secretManagement": {"automaticManagementEnabled": self.managed},
            "platformAccountProperties": self.properties,
            "_source_vendor": self.source_vendor,
            "_normalized": True,
        }


@dataclass
class NormalizedContainer:
    """Common container (Safe/Folder/Container/Path) representation."""
    source_id: str
    source_vendor: str
    name: str
    description: str = ""
    parent: str = ""
    members: List[Dict[str, Any]] = field(default_factory=list)
    properties: Dict[str, Any] = field(default_factory=dict)
    raw: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class NormalizedPlatform:
    """Common platform/policy/template representation."""
    source_id: str
    source_vendor: str
    name: str
    platform_type: str = ""    # windows_domain | unix_ssh | database | etc.
    rotation_enabled: bool = False
    rotation_interval_days: int = 0
    properties: Dict[str, Any] = field(default_factory=dict)
    raw: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return asdict(self)


# ── Source Adapter ABC ──────────────────────────────────────────

class SourceAdapter(ABC):
    """Abstract base class for reading from any PAM vendor."""

    VENDOR: str = "base"

    def __init__(self, config: dict):
        self._config = config
        self._connected = False

    @abstractmethod
    def connect(self) -> bool:
        """Establish connection to the source. Returns True on success."""

    @abstractmethod
    def disconnect(self):
        """Close connection and clean up resources."""

    @abstractmethod
    def get_accounts(self, **filters) -> List[NormalizedAccount]:
        """Enumerate all accounts, normalized to canonical format."""

    @abstractmethod
    def get_containers(self) -> List[NormalizedContainer]:
        """Enumerate all containers (safes/folders/paths)."""

    @abstractmethod
    def get_platforms(self) -> List[NormalizedPlatform]:
        """Enumerate all platforms/templates/policies."""

    @abstractmethod
    def retrieve_secret(self, account_id: str, reason: str = "") -> str:
        """Retrieve the actual secret value for an account."""

    @abstractmethod
    def get_audit_logs(self, days: int = 90) -> List[dict]:
        """Retrieve audit/activity logs."""

    @abstractmethod
    def get_applications(self) -> List[dict]:
        """Retrieve application identities (CCP/AAM or equivalent)."""

    @abstractmethod
    def preflight_check(self) -> dict:
        """Validate connectivity, permissions, and readiness."""

    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, *exc):
        self.disconnect()
        return False


# ── CyberArk Source Adapter ─────────────────────────────────────

class CyberArkSourceAdapter(SourceAdapter):
    """Wraps existing CyberArkClient to produce normalized output.

    This is the default adapter when source.type is 'cyberark'.
    """

    VENDOR = "cyberark"

    def __init__(self, config: dict):
        super().__init__(config)
        self._client = None

    def connect(self) -> bool:
        from core.cyberark_client import CyberArkClient
        on_prem_cfg = self._config.get("cyberark_on_prem", self._config)
        self._client = CyberArkClient(on_prem_cfg)
        self._client.__enter__()
        self._connected = True
        return True

    def disconnect(self):
        if self._client:
            self._client.__exit__(None, None, None)
            self._client = None
        self._connected = False

    def get_accounts(self, **filters) -> List[NormalizedAccount]:
        raw_accounts = self._client.get_accounts()
        return [self._normalize_account(a) for a in raw_accounts]

    def get_containers(self) -> List[NormalizedContainer]:
        safes = self._client.get_safes(include_system=False)
        containers = []
        for safe in safes:
            name = safe.get("SafeName", safe.get("safeName", ""))
            members = []
            try:
                members = self._client.get_safe_members(name)
            except Exception:
                pass
            containers.append(NormalizedContainer(
                source_id=name,
                source_vendor=self.VENDOR,
                name=name,
                description=safe.get("Description", ""),
                members=members,
                raw=safe,
            ))
        return containers

    def get_platforms(self) -> List[NormalizedPlatform]:
        platforms = self._client.get_platforms()
        return [NormalizedPlatform(
            source_id=p.get("PlatformID", p.get("id", "")),
            source_vendor=self.VENDOR,
            name=p.get("PlatformID", p.get("Name", "")),
            platform_type=p.get("SystemType", ""),
            rotation_enabled=p.get("AllowedSafes", "") != "",
            raw=p,
        ) for p in platforms]

    def retrieve_secret(self, account_id: str, reason: str = "") -> str:
        return self._client.retrieve_password(account_id, reason or "Migration")

    def get_audit_logs(self, days: int = 90) -> List[dict]:
        return self._client.get_audit_logs(days=days)

    def get_applications(self) -> List[dict]:
        return self._client.get_applications()

    def preflight_check(self) -> dict:
        return self._client.preflight_check()

    def _normalize_account(self, acct: dict) -> NormalizedAccount:
        return NormalizedAccount(
            source_id=acct.get("id", ""),
            source_vendor=self.VENDOR,
            name=acct.get("name", acct.get("userName", "")),
            username=acct.get("userName", ""),
            address=acct.get("address", ""),
            container_name=acct.get("safeName", ""),
            platform_type=acct.get("platformId", ""),
            secret_type=acct.get("secretType", "password"),
            managed=acct.get("secretManagement", {}).get(
                "automaticManagementEnabled", True),
            properties=acct.get("platformAccountProperties", {}),
            raw=acct,
        )


# ── BeyondTrust Password Safe Adapter ──────────────────────────

class BeyondTrustAdapter(SourceAdapter):
    """BeyondTrust Password Safe REST API v3 source adapter.

    API flow:
        POST /Auth/SignAppin → session token
        GET /ManagedAccounts → account enumeration
        GET /ManagedSystems → container enumeration
        POST /Requests → credential request
        GET /Credentials/{requestId} → retrieve password
        POST /Requests/{requestId}/Checkin → release credential
    """

    VENDOR = "beyondtrust"

    def __init__(self, config: dict):
        super().__init__(config)
        self._session = None
        self._base_url = ""
        self._headers = {}

    def connect(self) -> bool:
        import requests
        bt_cfg = self._config.get("beyondtrust", self._config)
        self._base_url = bt_cfg.get("base_url", "").rstrip("/")
        api_key = os.environ.get(
            bt_cfg.get("api_key_env", "BT_API_KEY"), "")
        runas_user = bt_cfg.get("runas_user", "")

        self._session = requests.Session()
        self._session.verify = bt_cfg.get("verify_ssl", True)

        # Authenticate
        resp = self._session.post(
            f"{self._base_url}/Auth/SignAppin",
            headers={"Authorization": f"PS-Auth key={api_key}; runas={runas_user};"},
        )
        resp.raise_for_status()
        self._headers = {"Authorization": f"PS-Auth key={api_key}; runas={runas_user};"}
        self._connected = True
        return True

    def disconnect(self):
        if self._session:
            try:
                self._session.post(
                    f"{self._base_url}/Auth/Signout",
                    headers=self._headers,
                )
            except Exception:
                pass
            self._session.close()
            self._session = None
        self._connected = False

    def get_accounts(self, **filters) -> List[NormalizedAccount]:
        accounts = []
        offset = 0
        limit = 100

        while True:
            resp = self._session.get(
                f"{self._base_url}/ManagedAccounts",
                headers=self._headers,
                params={"offset": offset, "limit": limit},
            )
            resp.raise_for_status()
            batch = resp.json()

            if not batch:
                break

            for acct in batch:
                accounts.append(self._normalize_account(acct))

            if len(batch) < limit:
                break
            offset += limit

        return accounts

    def get_containers(self) -> List[NormalizedContainer]:
        resp = self._session.get(
            f"{self._base_url}/ManagedSystems",
            headers=self._headers,
        )
        resp.raise_for_status()
        systems = resp.json()

        return [NormalizedContainer(
            source_id=str(s.get("ManagedSystemID", "")),
            source_vendor=self.VENDOR,
            name=s.get("ManagedSystemName", s.get("SystemName", "")),
            description=s.get("Description", ""),
            properties={
                "platform": s.get("PlatformID", ""),
                "contact_email": s.get("ContactEmail", ""),
            },
            raw=s,
        ) for s in systems]

    def get_platforms(self) -> List[NormalizedPlatform]:
        resp = self._session.get(
            f"{self._base_url}/Platforms",
            headers=self._headers,
        )
        resp.raise_for_status()
        platforms = resp.json()

        return [NormalizedPlatform(
            source_id=str(p.get("PlatformID", "")),
            source_vendor=self.VENDOR,
            name=p.get("Name", ""),
            platform_type=p.get("PlatformType", ""),
            raw=p,
        ) for p in platforms]

    def retrieve_secret(self, account_id: str, reason: str = "") -> str:
        # BT requires a request/approval flow
        resp = self._session.post(
            f"{self._base_url}/Requests",
            headers=self._headers,
            json={
                "AccountId": int(account_id),
                "Reason": reason or "PAM Migration",
                "DurationMinutes": 5,
            },
        )
        resp.raise_for_status()
        request_id = resp.json()

        # Retrieve the credential
        resp = self._session.get(
            f"{self._base_url}/Credentials/{request_id}",
            headers=self._headers,
        )
        resp.raise_for_status()
        password = resp.text.strip('"')

        # Check in the request
        try:
            self._session.put(
                f"{self._base_url}/Requests/{request_id}/Checkin",
                headers=self._headers,
                json={"Reason": "Migration complete"},
            )
        except Exception:
            pass

        return password

    def get_audit_logs(self, days: int = 90) -> List[dict]:
        # BT activity logs
        try:
            resp = self._session.get(
                f"{self._base_url}/ActivityLogs",
                headers=self._headers,
                params={"days": days},
            )
            resp.raise_for_status()
            return resp.json()
        except Exception:
            return []

    def get_applications(self) -> List[dict]:
        # BT doesn't have CCP/AAM equivalent — return empty
        return []

    def preflight_check(self) -> dict:
        checks = {"connected": self._connected, "errors": []}
        try:
            resp = self._session.get(
                f"{self._base_url}/ManagedAccounts",
                headers=self._headers,
                params={"limit": 1},
            )
            checks["can_list_accounts"] = resp.status_code == 200
        except Exception as e:
            checks["errors"].append(f"Account listing failed: {e}")
            checks["can_list_accounts"] = False
        return checks

    def _normalize_account(self, acct: dict) -> NormalizedAccount:
        return NormalizedAccount(
            source_id=str(acct.get("ManagedAccountID", acct.get("AccountId", ""))),
            source_vendor=self.VENDOR,
            name=acct.get("AccountName", ""),
            username=acct.get("AccountName", ""),
            address=acct.get("SystemName", acct.get("DomainName", "")),
            container_name=acct.get("SystemName", ""),
            platform_type=acct.get("PlatformID", ""),
            secret_type="password",
            account_type=self._classify_bt_account(acct),
            managed=acct.get("IsAutoManaged", True),
            properties={
                "domain": acct.get("DomainName", ""),
                "instance": acct.get("InstanceName", ""),
            },
            raw=acct,
        )

    def _classify_bt_account(self, acct: dict) -> str:
        name = (acct.get("AccountName") or "").lower()
        if any(p in name for p in ("svc", "service", "app", "api", "bot")):
            return "service"
        return "human"


# ── Secret Server Source Adapter ────────────────────────────────

class SecretServerSourceAdapter(SourceAdapter):
    """Delinea Secret Server REST API v1 source adapter.

    Used when migrating FROM Secret Server (SS as source, not target).
    """

    VENDOR = "secretserver"

    def __init__(self, config: dict):
        super().__init__(config)
        self._session = None
        self._base_url = ""
        self._token = ""

    def connect(self) -> bool:
        import requests
        ss_cfg = self._config.get("secretserver_source", self._config)
        self._base_url = ss_cfg.get("base_url", "").rstrip("/")
        self._session = requests.Session()
        self._session.verify = ss_cfg.get("verify_ssl", True)

        # OAuth2 authentication
        resp = self._session.post(
            f"{self._base_url}/oauth2/token",
            data={
                "grant_type": "password",
                "username": os.environ.get(
                    ss_cfg.get("username_env", "SS_SOURCE_USERNAME"), ""),
                "password": os.environ.get(
                    ss_cfg.get("password_env", "SS_SOURCE_PASSWORD"), ""),
            },
        )
        resp.raise_for_status()
        self._token = resp.json().get("access_token", "")
        self._session.headers.update({
            "Authorization": f"Bearer {self._token}",
            "Content-Type": "application/json",
        })
        self._connected = True
        return True

    def disconnect(self):
        if self._session:
            self._session.close()
            self._session = None
        self._token = ""
        self._connected = False

    def get_accounts(self, **filters) -> List[NormalizedAccount]:
        accounts = []
        skip = 0
        take = 100

        while True:
            resp = self._session.get(
                f"{self._base_url}/api/v1/secrets",
                params={"skip": skip, "take": take,
                        "filter.includeRestricted": True},
            )
            resp.raise_for_status()
            data = resp.json()
            records = data.get("records", [])

            if not records:
                break

            for secret in records:
                accounts.append(self._normalize_secret(secret))

            if len(records) < take:
                break
            skip += take

        return accounts

    def get_containers(self) -> List[NormalizedContainer]:
        resp = self._session.get(
            f"{self._base_url}/api/v1/folders",
            params={"filter.folderPath": "\\", "take": 1000},
        )
        resp.raise_for_status()
        folders = resp.json().get("records", [])

        return [NormalizedContainer(
            source_id=str(f.get("id", "")),
            source_vendor=self.VENDOR,
            name=f.get("folderName", ""),
            description="",
            parent=str(f.get("parentFolderId", "")),
            properties={"path": f.get("folderPath", "")},
            raw=f,
        ) for f in folders]

    def get_platforms(self) -> List[NormalizedPlatform]:
        resp = self._session.get(
            f"{self._base_url}/api/v1/secret-templates",
        )
        resp.raise_for_status()
        templates = resp.json().get("records", [])

        return [NormalizedPlatform(
            source_id=str(t.get("id", "")),
            source_vendor=self.VENDOR,
            name=t.get("name", ""),
            raw=t,
        ) for t in templates]

    def retrieve_secret(self, account_id: str, reason: str = "") -> str:
        resp = self._session.get(
            f"{self._base_url}/api/v1/secrets/{account_id}/fields/password",
        )
        resp.raise_for_status()
        return resp.text.strip('"')

    def get_audit_logs(self, days: int = 90) -> List[dict]:
        try:
            resp = self._session.get(
                f"{self._base_url}/api/v1/secret-audit",
                params={"take": 1000},
            )
            resp.raise_for_status()
            return resp.json().get("records", [])
        except Exception:
            return []

    def get_applications(self) -> List[dict]:
        return []  # SS doesn't have CCP/AAM equivalent

    def preflight_check(self) -> dict:
        checks = {"connected": self._connected, "errors": []}
        try:
            resp = self._session.get(
                f"{self._base_url}/api/v1/secrets",
                params={"take": 1},
            )
            checks["can_list_accounts"] = resp.status_code == 200
            checks["can_list_safes"] = True
        except Exception as e:
            checks["errors"].append(str(e))
            checks["can_list_accounts"] = False
        return checks

    def _normalize_secret(self, secret: dict) -> NormalizedAccount:
        # Extract username/password fields from Items array
        items = secret.get("items", [])
        username = ""
        for item in items:
            if item.get("slug") == "username" or item.get("fieldName", "").lower() == "username":
                username = item.get("itemValue", "")
                break

        return NormalizedAccount(
            source_id=str(secret.get("id", "")),
            source_vendor=self.VENDOR,
            name=secret.get("name", ""),
            username=username,
            address=secret.get("machineName", ""),
            container_name=secret.get("folderPath", str(secret.get("folderId", ""))),
            platform_type=str(secret.get("secretTemplateName", "")),
            secret_type="password",
            managed=secret.get("autoChangeEnabled", False),
            properties={"template_id": secret.get("secretTemplateId", "")},
            raw=secret,
        )


# ── HashiCorp Vault Adapter ────────────────────────────────────

class HashiCorpVaultAdapter(SourceAdapter):
    """HashiCorp Vault KV v2 source adapter.

    API flow:
        POST /v1/auth/approle/login → client token
        LIST /v1/{mount}/metadata/ → enumerate secrets (recursive)
        GET /v1/{mount}/data/{path} → read secret data
    """

    VENDOR = "hashicorp"

    def __init__(self, config: dict):
        super().__init__(config)
        self._session = None
        self._vault_addr = ""
        self._mount = "secret"

    def connect(self) -> bool:
        import requests
        vault_cfg = self._config.get("hashicorp", self._config)
        self._vault_addr = os.environ.get(
            vault_cfg.get("vault_addr_env", "VAULT_ADDR"), "").rstrip("/")
        self._mount = vault_cfg.get("mount", "secret")

        self._session = requests.Session()
        self._session.verify = vault_cfg.get("verify_ssl", True)

        # Auth: token or approle
        token = os.environ.get("VAULT_TOKEN", "")
        if token:
            self._session.headers["X-Vault-Token"] = token
        else:
            role_id = os.environ.get(
                vault_cfg.get("role_id_env", "VAULT_ROLE_ID"), "")
            secret_id = os.environ.get(
                vault_cfg.get("secret_id_env", "VAULT_SECRET_ID"), "")
            resp = self._session.post(
                f"{self._vault_addr}/v1/auth/approle/login",
                json={"role_id": role_id, "secret_id": secret_id},
            )
            resp.raise_for_status()
            token = resp.json().get("auth", {}).get("client_token", "")
            self._session.headers["X-Vault-Token"] = token

        self._connected = True
        return True

    def disconnect(self):
        if self._session:
            self._session.close()
            self._session = None
        self._connected = False

    def get_accounts(self, **filters) -> List[NormalizedAccount]:
        accounts = []
        paths = self._list_secrets_recursive("")

        for path in paths:
            try:
                resp = self._session.get(
                    f"{self._vault_addr}/v1/{self._mount}/data/{path}",
                )
                if resp.status_code != 200:
                    continue
                data = resp.json().get("data", {})
                secret_data = data.get("data", {})
                metadata = data.get("metadata", {})

                # Vault KV secrets can have any structure — normalize common patterns
                username = (secret_data.get("username") or
                            secret_data.get("user") or
                            secret_data.get("login") or "")
                address = (secret_data.get("host") or
                           secret_data.get("address") or
                           secret_data.get("server") or
                           secret_data.get("url") or "")

                # Determine secret type
                secret_type = "password"
                if "key" in secret_data or "private_key" in secret_data:
                    secret_type = "key"
                elif "certificate" in secret_data or "cert" in secret_data:
                    secret_type = "certificate"
                elif "api_key" in secret_data or "token" in secret_data:
                    secret_type = "api_key"

                # Container = directory portion of path
                parts = path.rsplit("/", 1)
                container = parts[0] if len(parts) > 1 else "/"
                name = parts[-1]

                accounts.append(NormalizedAccount(
                    source_id=path,
                    source_vendor=self.VENDOR,
                    name=name,
                    username=username,
                    address=address,
                    container_name=container,
                    platform_type="vault_kv",
                    secret_type=secret_type,
                    managed=False,  # Vault doesn't auto-rotate by default
                    last_modified=metadata.get("created_time", ""),
                    properties={k: v for k, v in secret_data.items()
                                if k not in ("password", "secret", "key", "private_key",
                                             "token", "api_key", "certificate", "cert")},
                    raw={"path": path, "metadata": metadata},
                ))
            except Exception as e:
                logger.debug(f"Error reading vault secret {path}: {e}")

        return accounts

    def get_containers(self) -> List[NormalizedContainer]:
        # Vault paths are virtual — derive from secret paths
        paths = self._list_secrets_recursive("")
        dirs = set()
        for path in paths:
            parts = path.split("/")
            for i in range(1, len(parts)):
                dirs.add("/".join(parts[:i]))

        return [NormalizedContainer(
            source_id=d,
            source_vendor=self.VENDOR,
            name=d.rsplit("/", 1)[-1] if "/" in d else d,
            parent=d.rsplit("/", 1)[0] if "/" in d else "",
            properties={"path": d},
        ) for d in sorted(dirs)]

    def get_platforms(self) -> List[NormalizedPlatform]:
        return [NormalizedPlatform(
            source_id="vault_kv",
            source_vendor=self.VENDOR,
            name="Vault KV v2",
            platform_type="kv_v2",
        )]

    def retrieve_secret(self, account_id: str, reason: str = "") -> str:
        resp = self._session.get(
            f"{self._vault_addr}/v1/{self._mount}/data/{account_id}",
        )
        resp.raise_for_status()
        data = resp.json().get("data", {}).get("data", {})
        return (data.get("password") or data.get("secret") or
                data.get("key") or data.get("value") or "")

    def get_audit_logs(self, days: int = 90) -> List[dict]:
        return []  # Vault audit logs are file/syslog based, not API

    def get_applications(self) -> List[dict]:
        return []

    def preflight_check(self) -> dict:
        checks = {"connected": self._connected, "errors": []}
        try:
            resp = self._session.get(f"{self._vault_addr}/v1/sys/health")
            health = resp.json()
            checks["vault_initialized"] = health.get("initialized", False)
            checks["vault_sealed"] = health.get("sealed", True)
            checks["can_list_accounts"] = not health.get("sealed", True)
            checks["can_list_safes"] = checks["can_list_accounts"]
        except Exception as e:
            checks["errors"].append(str(e))
        return checks

    def _list_secrets_recursive(self, prefix: str) -> List[str]:
        """Recursively list all secret paths under prefix."""
        paths = []
        try:
            resp = self._session.request(
                "LIST",
                f"{self._vault_addr}/v1/{self._mount}/metadata/{prefix}",
            )
            if resp.status_code != 200:
                return paths

            keys = resp.json().get("data", {}).get("keys", [])
            for key in keys:
                full_path = f"{prefix}{key}" if prefix else key
                if key.endswith("/"):
                    # Directory — recurse
                    paths.extend(self._list_secrets_recursive(full_path))
                else:
                    paths.append(full_path)
        except Exception:
            pass
        return paths


# ── Cloud Secrets Adapters (G-06) ──────────────────────────────

class AWSSecretsManagerAdapter(SourceAdapter):
    """AWS Secrets Manager discovery adapter."""

    VENDOR = "aws"

    def __init__(self, config: dict):
        super().__init__(config)
        self._client = None

    def connect(self) -> bool:
        import boto3
        aws_cfg = self._config.get("aws", self._config)
        region = aws_cfg.get("region", os.environ.get("AWS_REGION", "us-east-1"))
        self._client = boto3.client("secretsmanager", region_name=region)
        self._connected = True
        return True

    def disconnect(self):
        self._client = None
        self._connected = False

    def get_accounts(self, **filters) -> List[NormalizedAccount]:
        accounts = []
        paginator = self._client.get_paginator("list_secrets")

        for page in paginator.paginate():
            for secret in page.get("SecretList", []):
                accounts.append(NormalizedAccount(
                    source_id=secret["ARN"],
                    source_vendor=self.VENDOR,
                    name=secret.get("Name", ""),
                    username="",
                    address="aws",
                    container_name=secret.get("Name", "").rsplit("/", 1)[0] or "/",
                    platform_type="aws_secretsmanager",
                    secret_type="password",
                    managed=secret.get("RotationEnabled", False),
                    last_modified=str(secret.get("LastChangedDate", "")),
                    last_accessed=str(secret.get("LastAccessedDate", "")),
                    tags={t["Key"]: t["Value"] for t in secret.get("Tags", [])},
                    properties={"rotation_enabled": secret.get("RotationEnabled", False)},
                    raw=secret,
                ))

        return accounts

    def get_containers(self) -> List[NormalizedContainer]:
        return []  # AWS SM doesn't have containers

    def get_platforms(self) -> List[NormalizedPlatform]:
        return [NormalizedPlatform(
            source_id="aws_secretsmanager",
            source_vendor=self.VENDOR,
            name="AWS Secrets Manager",
        )]

    def retrieve_secret(self, account_id: str, reason: str = "") -> str:
        resp = self._client.get_secret_value(SecretId=account_id)
        return resp.get("SecretString", "")

    def get_audit_logs(self, days: int = 90) -> List[dict]:
        return []  # Use CloudTrail instead

    def get_applications(self) -> List[dict]:
        return []

    def preflight_check(self) -> dict:
        try:
            self._client.list_secrets(MaxResults=1)
            return {"connected": True, "can_list_accounts": True,
                    "can_list_safes": True, "errors": []}
        except Exception as e:
            return {"connected": False, "errors": [str(e)]}


class AzureKeyVaultAdapter(SourceAdapter):
    """Azure Key Vault discovery adapter."""

    VENDOR = "azure"

    def __init__(self, config: dict):
        super().__init__(config)
        self._clients = []  # Multiple vaults possible
        self._vault_urls = []

    def connect(self) -> bool:
        from azure.identity import DefaultAzureCredential
        from azure.keyvault.secrets import SecretClient

        azure_cfg = self._config.get("azure_keyvault", self._config)
        self._vault_urls = azure_cfg.get("vault_urls", [])
        credential = DefaultAzureCredential()

        self._clients = []
        for url in self._vault_urls:
            self._clients.append(SecretClient(vault_url=url, credential=credential))

        self._connected = True
        return True

    def disconnect(self):
        self._clients = []
        self._connected = False

    def get_accounts(self, **filters) -> List[NormalizedAccount]:
        accounts = []
        for i, client in enumerate(self._clients):
            vault_url = self._vault_urls[i]
            for prop in client.list_properties_of_secrets():
                accounts.append(NormalizedAccount(
                    source_id=prop.id,
                    source_vendor=self.VENDOR,
                    name=prop.name,
                    username="",
                    address=vault_url,
                    container_name=vault_url.split("//")[1].split(".")[0],
                    platform_type="azure_keyvault",
                    secret_type="password",
                    managed=False,
                    last_modified=str(prop.updated_on or ""),
                    tags=dict(prop.tags) if prop.tags else {},
                    properties={"enabled": prop.enabled, "vault": vault_url},
                    raw={"id": prop.id, "name": prop.name, "enabled": prop.enabled},
                ))
        return accounts

    def get_containers(self) -> List[NormalizedContainer]:
        return [NormalizedContainer(
            source_id=url,
            source_vendor=self.VENDOR,
            name=url.split("//")[1].split(".")[0],
            properties={"vault_url": url},
        ) for url in self._vault_urls]

    def get_platforms(self) -> List[NormalizedPlatform]:
        return [NormalizedPlatform(
            source_id="azure_keyvault",
            source_vendor=self.VENDOR,
            name="Azure Key Vault",
        )]

    def retrieve_secret(self, account_id: str, reason: str = "") -> str:
        # account_id is the secret name; try each vault
        for client in self._clients:
            try:
                secret = client.get_secret(account_id)
                return secret.value or ""
            except Exception:
                continue
        return ""

    def get_audit_logs(self, days: int = 90) -> List[dict]:
        return []  # Use Azure Monitor / Log Analytics

    def get_applications(self) -> List[dict]:
        return []

    def preflight_check(self) -> dict:
        checks = {"connected": True, "errors": [], "vaults": len(self._vault_urls)}
        for i, client in enumerate(self._clients):
            try:
                next(iter(client.list_properties_of_secrets()), None)
                checks[f"vault_{i}_accessible"] = True
            except Exception as e:
                checks[f"vault_{i}_accessible"] = False
                checks["errors"].append(str(e))
        checks["can_list_accounts"] = not checks["errors"]
        checks["can_list_safes"] = checks["can_list_accounts"]
        return checks


class GCPSecretManagerAdapter(SourceAdapter):
    """Google Cloud Secret Manager discovery adapter."""

    VENDOR = "gcp"

    def __init__(self, config: dict):
        super().__init__(config)
        self._client = None
        self._project_id = ""

    def connect(self) -> bool:
        from google.cloud import secretmanager
        gcp_cfg = self._config.get("gcp", self._config)
        self._project_id = gcp_cfg.get(
            "project_id", os.environ.get("GCP_PROJECT_ID", ""))
        self._client = secretmanager.SecretManagerServiceClient()
        self._connected = True
        return True

    def disconnect(self):
        self._client = None
        self._connected = False

    def get_accounts(self, **filters) -> List[NormalizedAccount]:
        accounts = []
        parent = f"projects/{self._project_id}"

        for secret in self._client.list_secrets(request={"parent": parent}):
            labels = dict(secret.labels) if secret.labels else {}
            accounts.append(NormalizedAccount(
                source_id=secret.name,
                source_vendor=self.VENDOR,
                name=secret.name.split("/")[-1],
                username="",
                address="gcp",
                container_name=self._project_id,
                platform_type="gcp_secretmanager",
                secret_type="password",
                managed=bool(secret.rotation),
                tags=labels,
                properties={
                    "replication": str(secret.replication),
                    "create_time": str(secret.create_time),
                },
                raw={"name": secret.name, "labels": labels},
            ))
        return accounts

    def get_containers(self) -> List[NormalizedContainer]:
        return [NormalizedContainer(
            source_id=self._project_id,
            source_vendor=self.VENDOR,
            name=self._project_id,
        )]

    def get_platforms(self) -> List[NormalizedPlatform]:
        return [NormalizedPlatform(
            source_id="gcp_secretmanager",
            source_vendor=self.VENDOR,
            name="GCP Secret Manager",
        )]

    def retrieve_secret(self, account_id: str, reason: str = "") -> str:
        name = f"{account_id}/versions/latest"
        response = self._client.access_secret_version(request={"name": name})
        return response.payload.data.decode("UTF-8")

    def get_audit_logs(self, days: int = 90) -> List[dict]:
        return []  # Use Cloud Audit Logs

    def get_applications(self) -> List[dict]:
        return []

    def preflight_check(self) -> dict:
        try:
            parent = f"projects/{self._project_id}"
            next(iter(self._client.list_secrets(request={"parent": parent})), None)
            return {"connected": True, "can_list_accounts": True,
                    "can_list_safes": True, "errors": []}
        except Exception as e:
            return {"connected": False, "errors": [str(e)]}


# ── Adapter Factory ─────────────────────────────────────────────

ADAPTER_REGISTRY = {
    "cyberark": CyberArkSourceAdapter,
    "beyondtrust": BeyondTrustAdapter,
    "secretserver": SecretServerSourceAdapter,
    "hashicorp": HashiCorpVaultAdapter,
    "aws": AWSSecretsManagerAdapter,
    "azure": AzureKeyVaultAdapter,
    "gcp": GCPSecretManagerAdapter,
}


def get_source_adapter(config: dict) -> SourceAdapter:
    """Factory function to create the appropriate source adapter."""
    source_cfg = config.get("source", {})
    source_type = source_cfg.get("type", "cyberark").lower()

    adapter_class = ADAPTER_REGISTRY.get(source_type)
    if adapter_class is None:
        raise ValueError(
            f"Unknown source type '{source_type}'. "
            f"Supported: {', '.join(ADAPTER_REGISTRY.keys())}"
        )

    return adapter_class(config)

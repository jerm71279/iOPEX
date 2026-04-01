#!/usr/bin/env python3
"""
KeeperPAM / Keeper Secrets Manager — Credential Retrieval Template

Replaces CyberArk CCP calls with Keeper Secrets Manager (KSM) SDK.

Install:
    pip install keeper-secrets-manager-core

First-run initialization:
    export KSM_ONE_TIME_TOKEN='ot:...'   # from Keeper Vault → Secrets Manager app
    python this_script.py                # creates ksm_config.json
    unset KSM_ONE_TIME_TOKEN             # not needed again

Runtime:
    export KSM_CONFIG_FILE=ksm_config.json   # path to initialized config

Record UIDs:
    Keeper Vault → select record → Details → Record UID
    UIDs are stable and do not change when a record is renamed.

CyberArk equivalent:
    # Old (CCP):
    GET /AIMWebService/api/Accounts?AppID=MyApp&Safe=MySafe&Object=MyAccount
    → response["Content"]

    # New (KSM):
    sm.get_secrets(["RECORD-UID"])
    → record.field("password", single=True)
"""

import os
import logging
from keeper_secrets_manager_core import SecretsManager
from keeper_secrets_manager_core.storage import FileKeyValueStorage

logger = logging.getLogger(__name__)


def get_ksm_client() -> SecretsManager:
    """
    Initialize and return a KSM client.

    On first run: set KSM_ONE_TIME_TOKEN env var → config file is created.
    On subsequent runs: uses existing config file.
    """
    config_file = os.environ.get("KSM_CONFIG_FILE", "ksm_config.json")
    one_time_token = os.environ.get("KSM_ONE_TIME_TOKEN")

    storage = FileKeyValueStorage(config_file)

    if one_time_token:
        logger.info("KSM: First-run init from one-time token → %s", config_file)
        client = SecretsManager(token=one_time_token, config=storage)
        logger.info("KSM: Config created. Unset KSM_ONE_TIME_TOKEN.")
    else:
        client = SecretsManager(config=storage)

    return client


def get_password(uid: str, client: SecretsManager = None) -> str:
    """
    Retrieve the password field from a Keeper record by UID.

    Args:
        uid:    Keeper record UID (e.g., "XXXX-YYYY-ZZZZ")
        client: Optional pre-initialized SecretsManager (reuse for performance)

    Returns:
        Password string.
    """
    if client is None:
        client = get_ksm_client()

    records = client.get_secrets([uid])
    if not records:
        raise ValueError(f"Record not found: uid={uid}")

    return records[0].field("password", single=True)


def get_field(uid: str, field: str, client: SecretsManager = None) -> str:
    """
    Retrieve any field from a Keeper record by UID and field type.

    Standard field types: "password", "login", "url", "host", "port"
    Custom fields: use exact label as defined in Keeper Vault.

    Args:
        uid:    Keeper record UID
        field:  Field type or custom field label
        client: Optional pre-initialized SecretsManager

    Returns:
        Field value as string.
    """
    if client is None:
        client = get_ksm_client()

    records = client.get_secrets([uid])
    if not records:
        raise ValueError(f"Record not found: uid={uid}")

    record = records[0]

    # Try standard field first
    try:
        value = record.field(field, single=True)
        if value is not None:
            return value
    except Exception:
        pass

    # Try custom field
    try:
        value = record.custom_field(field, single=True)
        if value is not None:
            return value
    except Exception:
        pass

    raise ValueError(f"Field '{field}' not found in record uid={uid}")


# ── Example usage ──────────────────────────────────────────────────────────────

if __name__ == "__main__":
    # Replace these UIDs with real Keeper record UIDs from your vault
    RECORD_UID = os.environ.get("KEEPER_RECORD_UID", "XXXX-YYYY-ZZZZ")

    client = get_ksm_client()

    # Retrieve password
    password = get_password(uid=RECORD_UID, client=client)
    print(f"Password retrieved: {'*' * len(password)}")

    # Retrieve login
    try:
        login = get_field(uid=RECORD_UID, field="login", client=client)
        print(f"Login: {login}")
    except ValueError as e:
        print(f"No login field: {e}")

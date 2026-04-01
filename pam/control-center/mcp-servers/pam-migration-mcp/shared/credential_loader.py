"""Credential loader — Azure Key Vault → environment variables at startup.

Loads PAM credentials from Azure Key Vault and sets them as environment
variables so the orchestrator's existing CyberArkClient and
SecretServerClient can pick them up transparently.

Falls back to existing environment variables if Key Vault is unavailable
(local development without Azure).
"""

import logging
import os
from typing import Dict, Optional

logger = logging.getLogger(__name__)

# Key Vault secret name → environment variable mapping
SECRET_MAP = {
    # CyberArk on-prem PVWA
    "cyberark-username": "CYBERARK_USERNAME",
    "cyberark-password": "CYBERARK_PASSWORD",
    # Privilege Cloud (Option A)
    "pcloud-client-id": "PCLOUD_CLIENT_ID",
    "pcloud-client-secret": "PCLOUD_CLIENT_SECRET",
    # Secret Server (Option B)
    "ss-client-id": "SS_CLIENT_ID",
    "ss-client-secret": "SS_CLIENT_SECRET",
    # StrongDM (Option A)
    "strongdm-access-key": "SDM_ACCESS_KEY",
    "strongdm-secret-key": "SDM_SECRET_KEY",
}


def load_credentials(key_vault_uri: Optional[str] = None) -> Dict[str, bool]:
    """Load credentials from Azure Key Vault into environment variables.

    Args:
        key_vault_uri: Azure Key Vault URI (e.g., https://kv-pam.vault.azure.net/).
                       If None, skips Key Vault and uses existing env vars.

    Returns:
        Dict mapping env var names to whether they're set (True/False).
    """
    status = {}

    if key_vault_uri:
        loaded = _load_from_key_vault(key_vault_uri)
        status.update(loaded)
    else:
        logger.info("No Key Vault URI configured — using environment variables")

    # Report which credentials are available
    for secret_name, env_var in SECRET_MAP.items():
        is_set = bool(os.environ.get(env_var))
        status[env_var] = is_set
        if is_set:
            logger.info("Credential available: %s", env_var)
        else:
            logger.debug("Credential not set: %s", env_var)

    return status


def _load_from_key_vault(key_vault_uri: str) -> Dict[str, bool]:
    """Load secrets from Azure Key Vault using managed identity."""
    results = {}
    try:
        from azure.identity import DefaultAzureCredential
        from azure.keyvault.secrets import SecretClient

        credential = DefaultAzureCredential()
        client = SecretClient(vault_url=key_vault_uri, credential=credential)

        for secret_name, env_var in SECRET_MAP.items():
            try:
                secret = client.get_secret(secret_name)
                if secret.value:
                    os.environ[env_var] = secret.value
                    results[env_var] = True
                    logger.info("Loaded from Key Vault: %s → %s", secret_name, env_var)
            except Exception:
                # Secret may not exist for this migration option — that's OK
                results[env_var] = False
                logger.debug("Key Vault secret '%s' not found or inaccessible", secret_name)

    except ImportError:
        logger.warning(
            "azure-identity / azure-keyvault-secrets not installed. "
            "Install with: pip install azure-identity azure-keyvault-secrets"
        )
    except Exception as exc:
        logger.warning("Key Vault connection failed: %s", exc)

    return results

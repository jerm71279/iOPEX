"""Deprecated shim — target client is now KeeperPAM.

All imports should use keeper_client.py. This shim re-exports the KeeperPAM
client under the old names so any code not yet updated still works.
"""

from core.keeper_client import (  # noqa: F401
    KeeperClient as CloudClient,
    KeeperError as CloudError,
    KeeperAuthError as CloudAuthError,
    _safe_error,
)

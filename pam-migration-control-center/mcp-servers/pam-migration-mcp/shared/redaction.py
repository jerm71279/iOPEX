"""Response redaction — strips secrets from all MCP tool responses.

Recursively scans dicts/lists for keys that may contain credentials
and replaces their values with a redaction marker. This ensures
passwords, tokens, and secrets are NEVER returned to the MCP client.
"""

import copy
import re
from typing import Any

# Keys whose values must always be redacted (case-insensitive match)
_SECRET_KEYS = frozenset({
    "password", "passwd", "secret", "token", "access_token",
    "refresh_token", "client_secret", "api_key", "apikey",
    "private_key", "privatekey", "credential", "credentials",
    "secret_value", "connection_string", "connectionstring",
    "sas_token", "shared_access_key", "master_key",
})

# Patterns in key names that suggest a secret
_SECRET_PATTERNS = re.compile(
    r"(password|passwd|secret|token|key|credential|apikey)",
    re.IGNORECASE,
)

REDACTED = "[REDACTED]"


def sanitize_response(data: Any, *, deep_copy: bool = True) -> Any:
    """Recursively strip secret values from a data structure.

    Args:
        data: The response data (dict, list, or scalar).
        deep_copy: If True, operates on a copy (default). Set False
                   if the caller guarantees the data won't be reused.

    Returns:
        Sanitized copy (or in-place if deep_copy=False).
    """
    if deep_copy:
        data = copy.deepcopy(data)
    return _sanitize(data)


def _sanitize(obj: Any) -> Any:
    if isinstance(obj, dict):
        for key in list(obj.keys()):
            if _is_secret_key(key):
                obj[key] = REDACTED
            else:
                obj[key] = _sanitize(obj[key])
    elif isinstance(obj, list):
        for i, item in enumerate(obj):
            obj[i] = _sanitize(item)
    elif isinstance(obj, str):
        # Don't redact string values at the top level —
        # only redact when the KEY indicates it's a secret
        pass
    return obj


def _is_secret_key(key: str) -> bool:
    """Check if a key name indicates a secret value."""
    lower = key.lower().strip("_")
    if lower in _SECRET_KEYS:
        return True
    return bool(_SECRET_PATTERNS.search(lower))

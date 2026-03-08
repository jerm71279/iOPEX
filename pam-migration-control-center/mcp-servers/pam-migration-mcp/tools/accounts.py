"""PVWA account tools — read-only CyberArk on-prem access (Condition 4).

Exposes list_pvwa_accounts and get_pvwa_account_details using the
existing cyberark_client.py.  All responses are sanitized to strip
passwords, secrets, and tokens.

CRITICAL: retrieve_password() is NEVER exposed as an MCP tool.
Passwords flow internally through Agent 04 to Key Vault only.
"""

import logging
import sys
from pathlib import Path

from ..server import mcp, _get_enforcer
from ..shared.config import PamMcpSettings
from ..shared.redaction import sanitize_response
from ..shared.phase_enforcer import PhaseEnforcementError

logger = logging.getLogger(__name__)
settings = PamMcpSettings()


def _get_pvwa_client():
    """Create a CyberArkClient from orchestrator code."""
    orch_path = str(Path(settings.orchestrator_path).resolve())
    if orch_path not in sys.path:
        sys.path.insert(0, orch_path)

    from core.cyberark_client import CyberArkClient

    config = {
        "base_url": settings.cyberark_base_url,
        "auth_type": settings.cyberark_auth_type,
        "verify_ssl": settings.cyberark_verify_ssl,
        "timeout": settings.cyberark_timeout,
    }
    return CyberArkClient(config)


@mcp.tool()
async def list_pvwa_accounts(
    safe: str | None = None,
    search: str | None = None,
    limit: int = 100,
) -> dict:
    """List accounts from CyberArk on-prem PVWA (read-only).

    Returns account summaries WITHOUT passwords or secrets.

    Args:
        safe: Filter by safe name.
        search: Search term for account names.
        limit: Maximum accounts to return (default 100).
    """
    enforcer = _get_enforcer()
    try:
        enforcer.validate("list_pvwa_accounts")
    except PhaseEnforcementError as exc:
        return {"error": str(exc)}

    if not settings.cyberark_base_url:
        return {
            "error": "PVWA not configured. Set PAM_MCP_CYBERARK_BASE_URL.",
            "hint": "This tool requires connectivity to the on-prem CyberArk PVWA.",
        }

    try:
        with _get_pvwa_client() as client:
            accounts = client.get_accounts(
                safe=safe,
                search=search,
                limit=limit,
            )
        return sanitize_response({
            "count": len(accounts),
            "accounts": accounts,
        })
    except Exception as exc:
        logger.error("PVWA list_accounts failed: %s", exc)
        return {"error": f"PVWA query failed: {type(exc).__name__}"}


@mcp.tool()
async def get_pvwa_account_details(account_id: str) -> dict:
    """Get detailed account info from CyberArk PVWA (read-only).

    Returns account properties, safe membership, platform info — NO passwords.

    Args:
        account_id: The CyberArk account ID.
    """
    enforcer = _get_enforcer()
    try:
        enforcer.validate("get_pvwa_account_details")
    except PhaseEnforcementError as exc:
        return {"error": str(exc)}

    if not settings.cyberark_base_url:
        return {"error": "PVWA not configured. Set PAM_MCP_CYBERARK_BASE_URL."}

    try:
        with _get_pvwa_client() as client:
            details = client.get_account_details(account_id)
        return sanitize_response(details)
    except Exception as exc:
        logger.error("PVWA get_account_details failed: %s", exc)
        return {"error": f"PVWA query failed: {type(exc).__name__}"}

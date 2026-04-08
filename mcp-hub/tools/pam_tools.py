"""
MCP tools — PAM status (KeeperPAM + legacy connectors)
Exposed on the hub at /mcp/pam-status
Calls shift-api for live gate/agent state; checks env for connector config.
"""
import os
import httpx
from fastmcp import FastMCP

mcp = FastMCP("pam-status")

SHIFT_URL = os.environ.get("SHIFT_API_URL", "http://localhost:8000")
KEEPERPAM_URL = os.environ.get("KEEPERPAM_URL", "")
TIMEOUT = 15.0


@mcp.tool()
async def pam_status() -> dict:
    """
    Aggregate PAM migration status across all connectors.
    Returns KeeperPAM reachability, SHIFT wave state, and gate summary.
    """
    result: dict = {}

    # KeeperPAM reachability
    if KEEPERPAM_URL:
        try:
            async with httpx.AsyncClient(timeout=TIMEOUT) as c:
                r = await c.get(f"{KEEPERPAM_URL.rstrip('/')}/health", timeout=5.0)
                result["keeperpam"] = {"reachable": r.status_code < 400, "status_code": r.status_code}
        except Exception as e:
            result["keeperpam"] = {"reachable": False, "error": str(e)}
    else:
        result["keeperpam"] = {"configured": False, "hint": "Set KEEPERPAM_URL in .env"}

    # SHIFT wave state via shift-api
    try:
        async with httpx.AsyncClient(timeout=TIMEOUT) as c:
            r = await c.get(f"{SHIFT_URL}/health")
            result["shift_api"] = {"reachable": r.status_code < 400}
            if r.status_code < 400:
                wr = await c.get(f"{SHIFT_URL}/wave/status")
                if wr.status_code < 400:
                    result["wave"] = wr.json()
    except Exception as e:
        result["shift_api"] = {"reachable": False, "error": str(e)}

    return result


@mcp.tool()
async def pam_connector_config() -> dict:
    """
    Return current PAM connector configuration (URLs only, no secrets).
    Shows which connectors are configured in the environment.
    """
    return {
        "keeperpam_url":   KEEPERPAM_URL or None,
        "shift_api_url":   SHIFT_URL,
        "cyberark_pvwa":   bool(os.environ.get("CYBERARK_PVWA_URL")),
        "active_target":   "KeeperPAM (production)",
    }

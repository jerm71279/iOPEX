"""
MCP tools — SHIFT PAM Control Center
Exposed on the hub at /mcp/shift
"""
from fastmcp import FastMCP
from clients import shift

mcp = FastMCP("shift")


@mcp.tool()
async def shift_health() -> dict:
    """Check SHIFT Agent API health and readiness."""
    try:
        return await shift.health()
    except Exception as e:
        return {"status": "unreachable", "error": str(e)}


@mcp.tool()
async def shift_wave_status() -> dict:
    """
    Get current SHIFT wave execution status.
    Returns active wave, gate states, and agent assignments.
    """
    try:
        return await shift.wave_status()
    except Exception as e:
        return {"error": str(e), "hint": "shift-api may not have /wave/status yet"}


@mcp.tool()
async def shift_agent_status() -> dict:
    """
    Get status of all SHIFT agents (gate trackers, PAM connectors, etc.).
    """
    try:
        return await shift.agent_status()
    except Exception as e:
        return {"error": str(e), "hint": "shift-api may not have /agents/status yet"}


@mcp.tool()
async def shift_ask(question: str, context: str = "") -> dict:
    """
    Ask the SHIFT system a free-form question about PAM migration state,
    wave progress, agent decisions, or gate outcomes.

    Args:
        question: Natural language question about SHIFT/PAM state
        context:  Optional additional context (e.g. current wave name)
    """
    try:
        return await shift.ask(question, context)
    except Exception as e:
        return {"error": str(e)}

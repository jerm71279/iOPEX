"""
MCP tools — iOPEX Digital Expert
Exposed on the hub at /mcp/iopex
"""
from fastmcp import FastMCP
from clients import iopex

mcp = FastMCP("iopex")

DOMAINS = ["pam", "zero_trust", "network", "secops", "cloud", "ai"]


@mcp.tool()
async def iopex_health() -> dict:
    """Check iOPEX Digital Expert API health."""
    try:
        return await iopex.health()
    except Exception as e:
        return {"status": "unreachable", "error": str(e)}


@mcp.tool()
async def iopex_query(
    question: str,
    domain: str = "",
    client_id: str = "mcp-hub",
) -> dict:
    """
    Query the iOPEX Digital Expert knowledge base.
    Returns a structured reply with confidence score and routing decision.

    Args:
        question:  Natural language question about iOPEX technology domains
        domain:    Optional domain hint — one of: pam, zero_trust, network,
                   secops, cloud, ai. Leave blank for auto-routing.
        client_id: Caller identity for session isolation (default: mcp-hub)
    """
    try:
        return await iopex.query(question, client_id=client_id, domain=domain or None)
    except Exception as e:
        return {"error": str(e)}

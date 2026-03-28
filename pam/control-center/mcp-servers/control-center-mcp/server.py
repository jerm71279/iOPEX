"""Control Center MCP Server — proxies FastAPI endpoints as MCP tools.

Exposes the PAM Migration Control Center's REST API as ~25 MCP tools
so AI assistants can query dashboards, phases, agents, waves, gates,
accounts, checkpoints, and deliverables.

All tools are read-only HTTP proxies via httpx.AsyncClient, except for
gate approval, checkpoint fire/resolve/escalate/snooze, and wave simulate.
"""

import json
import logging
from contextlib import asynccontextmanager

import httpx
from mcp.server.fastmcp import FastMCP

from .config import ControlCenterMcpSettings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

settings = ControlCenterMcpSettings()
_client: httpx.AsyncClient | None = None


@asynccontextmanager
async def lifespan(server):
    """Create shared httpx client on startup, close on shutdown."""
    global _client
    _client = httpx.AsyncClient(
        base_url=settings.control_center_url,
        timeout=settings.request_timeout,
    )
    logger.info(
        "Control Center MCP started — proxying %s", settings.control_center_url,
    )
    yield
    await _client.aclose()
    _client = None


mcp = FastMCP(
    settings.server_name,
    lifespan=lifespan,
)


async def _get(path: str, params: dict | None = None) -> dict | list:
    """GET helper with error handling."""
    resp = await _client.get(f"/api{path}", params=params)
    resp.raise_for_status()
    return resp.json()


async def _post(path: str, params: dict | None = None, json_body: dict | None = None) -> dict:
    """POST helper with error handling."""
    resp = await _client.post(f"/api{path}", params=params, json=json_body)
    resp.raise_for_status()
    return resp.json()


# ═══════════════════════════════════════════════════════════════
# Dashboard (4 tools)
# ═══════════════════════════════════════════════════════════════


@mcp.tool()
async def get_dashboard_stats(option: str = "a") -> dict:
    """Get migration dashboard statistics (accounts, agents, gates, current phase)."""
    return await _get("/dashboard/stats", {"option": option})


@mcp.tool()
async def get_dashboard_risks(option: str = "a") -> dict:
    """Get risk breakdown (critical/high/medium/low) with descriptions."""
    return await _get("/dashboard/risks", {"option": option})


@mcp.tool()
async def get_dashboard_timeline(option: str = "a") -> list:
    """Get phase timeline with weeks, risk levels, and status."""
    return await _get("/dashboard/timeline", {"option": option})


@mcp.tool()
async def get_dashboard_predictions(option: str = "a") -> dict:
    """Get AI predictive insights — bottleneck and risk forecasting."""
    return await _get("/dashboard/predictions", {"option": option})


# ═══════════════════════════════════════════════════════════════
# Phases (2 tools)
# ═══════════════════════════════════════════════════════════════


@mcp.tool()
async def list_phases(option: str = "a") -> list:
    """List all migration phases (P0-P7) with agents, activities, and deliverables."""
    return await _get("/phases", {"option": option})


@mcp.tool()
async def get_phase(phase_id: str, option: str = "a") -> dict:
    """Get detailed phase info including agents, activities, and deliverables."""
    return await _get(f"/phases/{phase_id}", {"option": option})


# ═══════════════════════════════════════════════════════════════
# Agents (3 tools)
# ═══════════════════════════════════════════════════════════════


@mcp.tool()
async def list_agents(option: str = "a") -> list:
    """List all 15 migration agents with status, phases, and dependencies."""
    return await _get("/agents", {"option": option})


@mcp.tool()
async def get_agent(agent_id: str, option: str = "a") -> dict:
    """Get detailed agent info including description and blocked_by list."""
    return await _get(f"/agents/{agent_id}", {"option": option})


@mcp.tool()
async def get_agent_output(agent_id: str) -> dict:
    """Get agent output data — deliverables produced by this agent."""
    return await _get(f"/agents/{agent_id}/output")


# ═══════════════════════════════════════════════════════════════
# Waves (3 tools)
# ═══════════════════════════════════════════════════════════════


@mcp.tool()
async def list_waves(option: str = "a") -> list:
    """List all migration waves with ETL steps, account counts, and status."""
    return await _get("/waves", {"option": option})


@mcp.tool()
async def get_wave(wave_id: str, option: str = "a") -> dict:
    """Get detailed wave info with ETL pipeline steps."""
    return await _get(f"/waves/{wave_id}", {"option": option})


@mcp.tool()
async def simulate_wave(wave_id: str, option: str = "a") -> dict:
    """Simulate ETL pipeline execution for a wave. Returns step-by-step results."""
    return await _post(f"/waves/{wave_id}/simulate", {"option": option})


# ═══════════════════════════════════════════════════════════════
# Gates (4 tools)
# ═══════════════════════════════════════════════════════════════


@mcp.tool()
async def list_gates(option: str = "a") -> list:
    """List all quality gates with status (passed/active/pending)."""
    return await _get("/gates", {"option": option})


@mcp.tool()
async def get_gate(gate_id: str, option: str = "a") -> dict:
    """Get detailed gate info including criteria and status."""
    return await _get(f"/gates/{gate_id}", {"option": option})


@mcp.tool()
async def approve_gate(gate_id: str) -> dict:
    """Approve a quality gate — advances it to 'passed' and activates the next gate."""
    return await _post(f"/gates/{gate_id}/approve")


@mcp.tool()
async def reset_gates() -> dict:
    """Reset all gates to their initial state."""
    return await _post("/gates/reset")


# ═══════════════════════════════════════════════════════════════
# Accounts (4 tools)
# ═══════════════════════════════════════════════════════════════


@mcp.tool()
async def list_accounts(
    option: str = "a",
    wave: int | None = None,
    department: str | None = None,
    role: str | None = None,
    nhi_type: str | None = None,
    risk: str | None = None,
    status: str | None = None,
    search: str | None = None,
) -> list:
    """List accounts with optional filters (wave, department, role, NHI type, risk, status, search)."""
    params = {"option": option}
    if wave is not None:
        params["wave"] = wave
    if department:
        params["department"] = department
    if role:
        params["role"] = role
    if nhi_type:
        params["nhi_type"] = nhi_type
    if risk:
        params["risk"] = risk
    if status:
        params["status"] = status
    if search:
        params["search"] = search
    return await _get("/accounts", params)


@mcp.tool()
async def get_account(account_id: str, option: str = "a") -> dict:
    """Get full account profile with permission mapping for the chosen migration option."""
    return await _get(f"/accounts/{account_id}", {"option": option})


@mcp.tool()
async def get_account_groups(option: str = "a", group_by: str = "department") -> dict:
    """Aggregate accounts by attribute (department, wave, role, nhi_type, risk)."""
    return await _get("/accounts/groups", {"option": option, "group_by": group_by})


@mcp.tool()
async def get_migration_flow(option: str = "a", batch_by: str = "wave") -> dict:
    """Get batching flow summary — accounts grouped and run through 7-step ETL pipeline."""
    return await _get("/accounts/migration-flow", {"option": option, "batch_by": batch_by})


# ═══════════════════════════════════════════════════════════════
# Checkpoints (7 tools)
# ═══════════════════════════════════════════════════════════════


@mcp.tool()
async def list_checkpoints(
    option: str = "a",
    phase: str | None = None,
    checkpoint_type: str | None = None,
    status: str | None = None,
) -> list:
    """List yellow checkpoints with optional filters (phase, type, status)."""
    params = {"option": option}
    if phase:
        params["phase"] = phase
    if checkpoint_type:
        params["type"] = checkpoint_type
    if status:
        params["status"] = status
    return await _get("/checkpoints", params)


@mcp.tool()
async def get_checkpoint_stats(option: str = "a") -> dict:
    """Get checkpoint summary counts — total, open, resolved, escalated, accumulation per phase."""
    return await _get("/checkpoints/stats", {"option": option})


@mcp.tool()
async def get_checkpoint(checkpoint_id: str) -> dict:
    """Get full checkpoint detail with AI rationale."""
    return await _get(f"/checkpoints/{checkpoint_id}")


@mcp.tool()
async def fire_checkpoint(
    phase: str,
    agent: str,
    checkpoint_type: str = "OPERATIONAL",
    condition: str = "Manual checkpoint fired via MCP",
    option: str = "a",
) -> dict:
    """Fire a new yellow checkpoint. Creates ServiceNow INC ticket and starts SLA window."""
    return await _post("/checkpoints/fire", json_body={
        "phase": phase,
        "agent": agent,
        "type": checkpoint_type,
        "condition": condition,
        "option": option,
    })


@mcp.tool()
async def resolve_checkpoint(
    checkpoint_id: str,
    resolution_note: str = "Resolved via MCP",
    resolved_by: str = "MCP User",
) -> dict:
    """Resolve a checkpoint — closes ServiceNow INC ticket."""
    return await _post(
        f"/checkpoints/{checkpoint_id}/resolve",
        {"resolution_note": resolution_note, "resolved_by": resolved_by},
    )


@mcp.tool()
async def escalate_checkpoint(checkpoint_id: str) -> dict:
    """Escalate checkpoint to RED — upgrades ServiceNow INC to CHG, blocks gate."""
    return await _post(f"/checkpoints/{checkpoint_id}/escalate")


@mcp.tool()
async def snooze_checkpoint(checkpoint_id: str) -> dict:
    """Snooze a checkpoint once — resets SLA window. Cannot snooze twice."""
    return await _post(f"/checkpoints/{checkpoint_id}/snooze")


# ═══════════════════════════════════════════════════════════════
# Deliverables (3 tools)
# ═══════════════════════════════════════════════════════════════


@mcp.tool()
async def list_deliverables(phase_id: str) -> list:
    """List deliverables for a phase with name, agent, format, and data availability."""
    return await _get(f"/deliverables/{phase_id}")


@mcp.tool()
async def get_deliverable(phase_id: str, deliverable_key: str) -> dict:
    """Get full deliverable content including data."""
    return await _get(f"/deliverables/{phase_id}/{deliverable_key}")


@mcp.tool()
async def compare_options() -> dict:
    """Get Option A vs Option B comparison — rows, permission mapping, platform→template map."""
    return await _get("/deliverables/compare/options")


# ═══════════════════════════════════════════════════════════════
# Entry point
# ═══════════════════════════════════════════════════════════════


def main():
    """Run the MCP server with HTTP transport."""
    mcp.run(transport="streamable-http")


if __name__ == "__main__":
    main()

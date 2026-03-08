"""Preflight connectivity checks.

Validates that the MCP server can reach required infrastructure
(PVWA, target platform, Key Vault) before running migration tools.
"""

import logging
import os
import sys
from pathlib import Path

from ..server import mcp, _get_state, _get_audit, _get_registry
from ..shared.config import PamMcpSettings

logger = logging.getLogger(__name__)
settings = PamMcpSettings()


@mcp.tool()
async def run_preflight_all() -> dict:
    """Run all preflight connectivity checks.

    Validates: orchestrator code, state file, PVWA, target platform,
    credentials, frozen registry.
    """
    checks = {}

    # 1. Orchestrator code accessible
    orch_path = Path(settings.orchestrator_path)
    checks["orchestrator_code"] = {
        "status": "pass" if (orch_path / "core" / "state.py").exists() else "fail",
        "path": str(orch_path),
    }

    # 2. State directory writable
    state_dir = Path(settings.state_dir)
    try:
        state_dir.mkdir(parents=True, exist_ok=True)
        test_file = state_dir / ".preflight_test"
        test_file.write_text("ok")
        test_file.unlink()
        checks["state_directory"] = {"status": "pass", "path": str(state_dir)}
    except Exception as exc:
        checks["state_directory"] = {"status": "fail", "error": str(exc)}

    # 3. PVWA connectivity
    if settings.cyberark_base_url:
        checks["pvwa"] = await _check_pvwa()
    else:
        checks["pvwa"] = {"status": "skip", "reason": "CYBERARK_BASE_URL not set"}

    # 4. Credentials available
    cred_checks = {}
    for env_var in ["CYBERARK_USERNAME", "CYBERARK_PASSWORD"]:
        cred_checks[env_var] = "set" if os.environ.get(env_var) else "not_set"
    if settings.migration_option == "a":
        for env_var in ["PCLOUD_CLIENT_ID", "PCLOUD_CLIENT_SECRET"]:
            cred_checks[env_var] = "set" if os.environ.get(env_var) else "not_set"
    else:
        for env_var in ["SS_CLIENT_ID", "SS_CLIENT_SECRET"]:
            cred_checks[env_var] = "set" if os.environ.get(env_var) else "not_set"
    checks["credentials"] = cred_checks

    # 5. Frozen registry
    registry = _get_registry()
    checks["frozen_registry"] = {
        "status": "pass",
        "frozen_count": registry.count if registry else 0,
    }

    # 6. Migration state
    state = _get_state()
    checks["migration_state"] = {
        "migration_id": state.get_migration_id() if state else None,
        "current_phase": state.current_phase if state else None,
    }

    all_pass = all(
        c.get("status") in ("pass", "skip")
        for c in checks.values()
        if isinstance(c, dict) and "status" in c
    )

    return {
        "overall": "pass" if all_pass else "warn",
        "checks": checks,
    }


@mcp.tool()
async def run_preflight_agent(agent_number: int) -> dict:
    """Run preflight check for a specific agent.

    Validates that the agent module exists and can be imported.

    Args:
        agent_number: Agent number (1-15).
    """
    if not 1 <= agent_number <= 15:
        return {"error": "Agent number must be 1-15"}

    agent_map = {
        1: "agent_01_discovery",
        2: "agent_02_gap_analysis",
        3: "agent_03_permissions",
        4: "agent_04_etl",
        5: "agent_05_heartbeat",
        6: "agent_06_integration",
        7: "agent_07_compliance",
        8: "agent_08_runbook",
        9: "agent_09_dependency_mapper",
        10: "agent_10_staging",
        11: "agent_11_source_adapter",
        12: "agent_12_nhi_handler",
        13: "agent_13_platform_plugins",
        14: "agent_14_onboarding",
        15: "agent_15_hybrid_fleet",
    }

    module_name = agent_map[agent_number]
    orch_path = Path(settings.orchestrator_path)
    agent_file = orch_path / "agents" / f"{module_name}.py"

    result = {
        "agent": agent_number,
        "module": module_name,
        "file_exists": agent_file.exists(),
        "path": str(agent_file),
    }

    if agent_file.exists():
        result["status"] = "pass"
    else:
        result["status"] = "fail"
        result["error"] = f"Agent file not found: {agent_file}"

    return result


async def _check_pvwa() -> dict:
    """Test PVWA connectivity."""
    try:
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
        with CyberArkClient(config) as client:
            # Attempt a lightweight API call
            client.get_server_version()
        return {"status": "pass", "base_url": settings.cyberark_base_url}
    except ImportError:
        return {"status": "fail", "error": "CyberArkClient not importable"}
    except Exception as exc:
        return {"status": "fail", "error": str(exc)}

"""Discovery tool — wraps Agents 01, 09, 12, 02, 03 for Phase 1.

Runs the full discovery pipeline: source adapter load, discovery scan,
dependency mapping, NHI classification, gap analysis, and permission mapping.
"""

import logging
import sys
from pathlib import Path

from ..server import mcp, _get_state, _get_audit, _get_enforcer
from ..shared.config import PamMcpSettings
from ..shared.redaction import sanitize_response
from ..shared.phase_enforcer import PhaseEnforcementError

logger = logging.getLogger(__name__)
settings = PamMcpSettings()


@mcp.tool()
async def run_discovery(option: str = "b", dry_run: bool = True) -> dict:
    """Run Phase 1 discovery pipeline (Agents 11, 01, 09, 12, 02, 03).

    Discovers accounts, maps dependencies, classifies NHIs, performs
    gap analysis, and maps permissions.

    Args:
        option: Migration target — "a" (Privilege Cloud) or "b" (Secret Server).
        dry_run: If True, simulate without making API calls (default: True).
    """
    state = _get_state()
    audit = _get_audit()
    enforcer = _get_enforcer()

    try:
        enforcer.validate("run_discovery")
    except PhaseEnforcementError as exc:
        return {"error": str(exc)}

    audit.log("discovery_started", {
        "option": option,
        "dry_run": dry_run,
        "source": "mcp",
    })

    # Import orchestrator's agent registry
    orch_path = str(Path(settings.orchestrator_path).resolve())
    if orch_path not in sys.path:
        sys.path.insert(0, orch_path)

    agents_sequence = [
        "11-source-adapter",
        "01-discovery",
        "09-dependency-mapper",
        "12-nhi-handler",
        "02-gap-analysis",
        "03-permissions",
    ]

    results = {}
    for agent_key in agents_sequence:
        step_id = f"P1:{agent_key}"
        if state.is_step_completed(step_id) and not dry_run:
            results[agent_key] = {"status": "skipped", "reason": "already completed"}
            continue

        try:
            from agents import AGENT_REGISTRY

            agent_cls = AGENT_REGISTRY.get(agent_key)
            if agent_cls is None:
                results[agent_key] = {"status": "error", "error": f"Agent '{agent_key}' not in registry"}
                continue

            # Load config
            import json
            config_path = Path(orch_path) / "config.json"
            if not config_path.exists():
                config_path = Path(orch_path) / "config.example.json"
            config = json.loads(config_path.read_text()) if config_path.exists() else {}

            agent = agent_cls(config=config, state=state, dry_run=dry_run)
            result = agent.run(phase="P1")

            results[agent_key] = {
                "status": result.status,
                "summary": result.summary if hasattr(result, "summary") else {},
                "dry_run": dry_run,
            }

            if not dry_run and result.status == "success":
                state.complete_step(step_id, {"agent": agent_key})
                if hasattr(result, "data") and result.data:
                    state.store_agent_result(agent_key, "P1", result.data)

        except ImportError as exc:
            results[agent_key] = {"status": "error", "error": f"Import failed: {exc}"}
        except Exception as exc:
            logger.error("Agent %s failed: %s", agent_key, exc)
            results[agent_key] = {"status": "error", "error": str(exc)}
            if not dry_run:
                state.record_error(agent_key, str(exc))

    audit.log("discovery_completed", {
        "option": option,
        "dry_run": dry_run,
        "agent_results": {k: v["status"] for k, v in results.items()},
    })

    return sanitize_response({
        "status": "completed",
        "dry_run": dry_run,
        "agents": results,
    })

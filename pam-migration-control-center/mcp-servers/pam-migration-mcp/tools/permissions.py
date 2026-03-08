"""Permission mapping tool — wraps Agent 03.

Maps CyberArk safe permissions to the target platform:
  - Option A (Secret Server): 22 → 4 roles (LOSSY — escalation detection)
  - Option B (Privilege Cloud): 22 → 22 (1:1 mapping)
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
async def map_permissions(option: str = "b", dry_run: bool = True) -> dict:
    """Run permission mapping (Agent 03).

    Maps CyberArk 22-permission model to the target platform.
    For Secret Server: 22 → 4 roles with escalation detection and loss tracking.
    For Privilege Cloud: 22 → 22 direct mapping.

    Args:
        option: Migration target — "a" or "b".
        dry_run: If True, simulate without writing results (default: True).
    """
    state = _get_state()
    audit = _get_audit()
    enforcer = _get_enforcer()

    try:
        enforcer.validate("map_permissions")
    except PhaseEnforcementError as exc:
        return {"error": str(exc)}

    phase = state.current_phase or "P1"
    step_id = f"{phase}:03-permissions"

    if state.is_step_completed(step_id) and not dry_run:
        return {"status": "skipped", "reason": f"Permissions already mapped in {phase}"}

    audit.log("permission_mapping_started", {
        "option": option,
        "phase": phase,
        "dry_run": dry_run,
    })

    try:
        orch_path = str(Path(settings.orchestrator_path).resolve())
        if orch_path not in sys.path:
            sys.path.insert(0, orch_path)

        from agents import AGENT_REGISTRY
        import json

        agent_cls = AGENT_REGISTRY.get("03-permissions")
        if agent_cls is None:
            return {"error": "Agent 03 not found in registry"}

        config_path = Path(orch_path) / "config.json"
        if not config_path.exists():
            config_path = Path(orch_path) / "config.example.json"
        config = json.loads(config_path.read_text()) if config_path.exists() else {}

        agent = agent_cls(config=config, state=state, dry_run=dry_run)
        result = agent.run(phase=phase)

        if not dry_run and result.status == "success":
            state.complete_step(step_id, {"agent": "03-permissions"})
            if hasattr(result, "data") and result.data:
                state.store_agent_result("03-permissions", phase, result.data)

        audit.log("permission_mapping_completed", {
            "option": option,
            "phase": phase,
            "status": result.status,
            "dry_run": dry_run,
        })

        return sanitize_response({
            "status": result.status,
            "phase": phase,
            "dry_run": dry_run,
            "summary": result.summary if hasattr(result, "summary") else {},
            "model": "22→4 (LOSSY)" if option == "a" else "22→22 (1:1)",
        })

    except Exception as exc:
        logger.error("Permission mapping failed: %s", exc)
        if not dry_run:
            state.record_error("03-permissions", str(exc))
        return {"error": f"Permission mapping failed: {type(exc).__name__}"}

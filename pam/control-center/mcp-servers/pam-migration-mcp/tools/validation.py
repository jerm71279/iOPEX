"""Validation tools — wraps Agent 10 (staging) and Agent 05 (heartbeat).

Agent 10: 10-assertion staging validation that hard-blocks production.
Agent 05: Post-migration heartbeat checks (10 validations per account).
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
async def run_staging_validation(option: str = "b") -> dict:
    """Run staging validation (Agent 10) — 10 assertions that must pass before production.

    Tests: connectivity, auth, CRUD operations, permission model, template/platform
    mapping, heartbeat, rollback, performance baseline, audit logging, NHI handling.

    Args:
        option: Migration target — "a" or "b".
    """
    state = _get_state()
    audit = _get_audit()
    enforcer = _get_enforcer()

    try:
        enforcer.validate("run_staging_validation")
    except PhaseEnforcementError as exc:
        return {"error": str(exc)}

    audit.log("staging_validation_started", {"option": option})

    try:
        orch_path = str(Path(settings.orchestrator_path).resolve())
        if orch_path not in sys.path:
            sys.path.insert(0, orch_path)

        from agents import AGENT_REGISTRY
        import json

        agent_cls = AGENT_REGISTRY.get("10-staging")
        if agent_cls is None:
            return {"error": "Agent 10 not found in registry"}

        config_path = Path(orch_path) / "config.json"
        if not config_path.exists():
            config_path = Path(orch_path) / "config.example.json"
        config = json.loads(config_path.read_text()) if config_path.exists() else {}

        agent = agent_cls(config=config, state=state, dry_run=False)
        result = agent.run(phase="P2")

        if result.status == "success":
            state.complete_step("P2:10-staging", {"agent": "10-staging"})
            if hasattr(result, "data") and result.data:
                state.store_agent_result("10-staging", "P2", result.data)

        audit.log("staging_validation_completed", {
            "status": result.status,
            "option": option,
        })

        return sanitize_response({
            "status": result.status,
            "summary": result.summary if hasattr(result, "summary") else {},
            "production_blocked": result.status != "success",
        })

    except Exception as exc:
        logger.error("Staging validation failed: %s", exc)
        state.record_error("10-staging", str(exc))
        return {"error": f"Staging validation failed: {type(exc).__name__}"}


@mcp.tool()
async def run_heartbeat_validation(option: str = "b", wave: int | None = None) -> dict:
    """Run post-migration heartbeat validation (Agent 05).

    Performs 10 checks per migrated account: connectivity, auth rotation,
    CPM/RPC health, audit continuity, session recording, integration endpoints,
    permission verification, NHI rotation, reporting, and SLA compliance.

    Args:
        option: Migration target — "a" or "b".
        wave: Optional wave number to validate (None = all migrated accounts).
    """
    state = _get_state()
    audit = _get_audit()
    enforcer = _get_enforcer()

    try:
        enforcer.validate("run_heartbeat_validation")
    except PhaseEnforcementError as exc:
        return {"error": str(exc)}

    phase = state.current_phase or "P4"
    audit.log("heartbeat_validation_started", {
        "option": option,
        "phase": phase,
        "wave": wave,
    })

    try:
        orch_path = str(Path(settings.orchestrator_path).resolve())
        if orch_path not in sys.path:
            sys.path.insert(0, orch_path)

        from agents import AGENT_REGISTRY
        import json

        agent_cls = AGENT_REGISTRY.get("05-heartbeat")
        if agent_cls is None:
            return {"error": "Agent 05 not found in registry"}

        config_path = Path(orch_path) / "config.json"
        if not config_path.exists():
            config_path = Path(orch_path) / "config.example.json"
        config = json.loads(config_path.read_text()) if config_path.exists() else {}

        agent = agent_cls(config=config, state=state, dry_run=False)
        result = agent.run(phase=phase)

        step_id = f"{phase}:05-heartbeat"
        if result.status == "success":
            state.complete_step(step_id, {"agent": "05-heartbeat", "wave": wave})

        audit.log("heartbeat_validation_completed", {
            "status": result.status,
            "phase": phase,
            "wave": wave,
        })

        return sanitize_response({
            "status": result.status,
            "phase": phase,
            "wave": wave,
            "summary": result.summary if hasattr(result, "summary") else {},
        })

    except Exception as exc:
        logger.error("Heartbeat validation failed: %s", exc)
        state.record_error("05-heartbeat", str(exc))
        return {"error": f"Heartbeat validation failed: {type(exc).__name__}"}

"""Compliance reporting tool — wraps Agent 07.

Generates compliance reports against PCI-DSS, NIST 800-53, HIPAA, and SOX
frameworks. Reports include current compliance posture, migration impact,
and risk findings.
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
async def generate_compliance_report(
    frameworks: list[str] | None = None,
    option: str = "b",
) -> dict:
    """Generate compliance report (Agent 07).

    Produces reports against selected compliance frameworks, including
    current posture, migration-specific risks, and remediation guidance.

    Args:
        frameworks: List of frameworks (default: all). Options: "pci-dss", "nist-800-53", "hipaa", "sox".
        option: Migration target — "a" or "b".
    """
    state = _get_state()
    audit = _get_audit()
    enforcer = _get_enforcer()

    try:
        enforcer.validate("generate_compliance_report")
    except PhaseEnforcementError as exc:
        return {"error": str(exc)}

    if frameworks is None:
        frameworks = ["pci-dss", "nist-800-53", "hipaa", "sox"]

    phase = state.current_phase or "P5"
    audit.log("compliance_report_started", {
        "frameworks": frameworks,
        "option": option,
        "phase": phase,
    })

    try:
        orch_path = str(Path(settings.orchestrator_path).resolve())
        if orch_path not in sys.path:
            sys.path.insert(0, orch_path)

        from agents import AGENT_REGISTRY
        import json

        agent_cls = AGENT_REGISTRY.get("07-compliance")
        if agent_cls is None:
            return {"error": "Agent 07 not found in registry"}

        config_path = Path(orch_path) / "config.json"
        if not config_path.exists():
            config_path = Path(orch_path) / "config.example.json"
        config = json.loads(config_path.read_text()) if config_path.exists() else {}

        agent = agent_cls(config=config, state=state, dry_run=False)
        result = agent.run(phase=phase)

        if result.status == "success":
            state.complete_step(f"{phase}:07-compliance", {
                "frameworks": frameworks,
            })
            if hasattr(result, "data") and result.data:
                state.store_agent_result("07-compliance", phase, result.data)

        audit.log("compliance_report_completed", {
            "status": result.status,
            "frameworks": frameworks,
        })

        return sanitize_response({
            "status": result.status,
            "frameworks": frameworks,
            "phase": phase,
            "summary": result.summary if hasattr(result, "summary") else {},
        })

    except Exception as exc:
        logger.error("Compliance report failed: %s", exc)
        state.record_error("07-compliance", str(exc))
        return {"error": f"Compliance report failed: {type(exc).__name__}"}

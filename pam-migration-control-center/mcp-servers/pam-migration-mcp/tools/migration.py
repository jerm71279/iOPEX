"""Migration lifecycle tools — start, status, advance phase.

These tools manage the high-level migration state machine.
"""

from ..server import mcp, _get_state, _get_audit, _get_enforcer
from ..shared.redaction import sanitize_response
from ..shared.phase_enforcer import PhaseEnforcementError


@mcp.tool()
async def start_migration(migration_id: str, option: str = "b") -> dict:
    """Start a new PAM migration. Creates state file and logs start event.

    Args:
        migration_id: Unique identifier for this migration run.
        option: Migration target — "a" (Privilege Cloud) or "b" (Secret Server).
    """
    state = _get_state()
    audit = _get_audit()

    existing = state.get_migration_id()
    if existing:
        return {
            "error": f"Migration '{existing}' already active. "
            "Complete or reset it before starting a new one.",
            "current_phase": state.current_phase,
        }

    state.start_migration(migration_id)
    audit.log("migration_started", {
        "migration_id": migration_id,
        "option": option,
        "source": "mcp",
    })

    return sanitize_response({
        "status": "started",
        "migration_id": migration_id,
        "option": option,
        "current_phase": state.current_phase,
        "summary": state.summary(),
    })


@mcp.tool()
async def get_migration_status() -> dict:
    """Get current migration status — phase, progress, errors, approvals."""
    state = _get_state()
    summary = state.summary()
    if summary["migration_id"] is None:
        return {"status": "no_active_migration", "message": "Call start_migration() to begin."}
    return sanitize_response(summary)


@mcp.tool()
async def advance_phase() -> dict:
    """Advance to the next migration phase after validating the current phase is complete.

    Returns the new phase or indicates migration completion.
    """
    state = _get_state()
    audit = _get_audit()
    enforcer = _get_enforcer()

    try:
        enforcer.validate("advance_phase")
    except PhaseEnforcementError as exc:
        return {"error": str(exc)}

    current = state.current_phase
    if current is None:
        return {"error": "No active migration to advance."}

    next_phase = state.advance_phase()
    if next_phase is None:
        audit.log("migration_completed", {"last_phase": current})
        return {
            "status": "migration_complete",
            "message": f"Phase {current} was the final phase. Migration complete.",
        }

    audit.log("phase_advanced", {
        "from_phase": current,
        "to_phase": next_phase,
        "source": "mcp",
    })

    return {
        "status": "advanced",
        "from_phase": current,
        "to_phase": next_phase,
        "summary": state.summary(),
    }

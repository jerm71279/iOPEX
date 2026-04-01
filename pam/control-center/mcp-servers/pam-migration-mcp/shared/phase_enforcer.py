"""Phase enforcer — validates MCP tool calls against current migration phase.

Prevents out-of-order operations (e.g., running ETL before discovery).
Each tool declares which phases it's allowed in and what prerequisites
must be completed.
"""

import logging
from dataclasses import dataclass, field
from typing import Dict, FrozenSet, Optional, Set

logger = logging.getLogger(__name__)

PHASES = ("P0", "P1", "P2", "P3", "P4", "P5", "P6", "P7")


@dataclass(frozen=True)
class ToolPhaseRule:
    """Defines which phases a tool may execute in and what must be done first."""
    allowed_phases: FrozenSet[str]
    required_completed_phases: FrozenSet[str] = field(default_factory=frozenset)


# Tool → phase rules
# "any" tools can run regardless of current phase
TOOL_RULES: Dict[str, ToolPhaseRule] = {
    # Always-available tools
    "start_migration": ToolPhaseRule(
        allowed_phases=frozenset(PHASES),
    ),
    "get_migration_status": ToolPhaseRule(
        allowed_phases=frozenset(PHASES),
    ),
    "emergency_unfreeze": ToolPhaseRule(
        allowed_phases=frozenset(PHASES),
    ),

    # Phase-restricted tools
    "run_discovery": ToolPhaseRule(
        allowed_phases=frozenset({"P1"}),
    ),
    "map_permissions": ToolPhaseRule(
        allowed_phases=frozenset({"P1", "P3"}),
    ),
    "run_staging_validation": ToolPhaseRule(
        allowed_phases=frozenset({"P2"}),
        required_completed_phases=frozenset({"P1"}),
    ),
    "execute_etl_batch": ToolPhaseRule(
        allowed_phases=frozenset({"P4", "P5"}),
    ),
    "run_heartbeat_validation": ToolPhaseRule(
        allowed_phases=frozenset({"P4", "P5", "P6"}),
    ),
    "generate_compliance_report": ToolPhaseRule(
        allowed_phases=frozenset({"P5", "P6", "P7"}),
    ),
    "advance_phase": ToolPhaseRule(
        allowed_phases=frozenset(PHASES),
    ),

    # PVWA read-only tools (always available once migration exists)
    "list_pvwa_accounts": ToolPhaseRule(
        allowed_phases=frozenset(PHASES),
    ),
    "get_pvwa_account_details": ToolPhaseRule(
        allowed_phases=frozenset(PHASES),
    ),

    # Preflight tools (always available)
    "run_preflight_all": ToolPhaseRule(
        allowed_phases=frozenset(PHASES),
    ),
    "run_preflight_agent": ToolPhaseRule(
        allowed_phases=frozenset(PHASES),
    ),
}


class PhaseEnforcementError(Exception):
    """Raised when a tool call violates phase constraints."""
    pass


class PhaseEnforcer:
    """Validates tool calls against the current migration phase."""

    def __init__(self, state):
        """
        Args:
            state: MigrationState instance (shared via state_bridge).
        """
        self._state = state

    def validate(self, tool_name: str) -> None:
        """Check if tool_name is allowed in the current phase.

        Raises:
            PhaseEnforcementError: If the tool cannot run in this phase.
        """
        rule = TOOL_RULES.get(tool_name)
        if rule is None:
            # Unknown tool — allow by default (the MCP framework
            # already gates unknown tools)
            logger.warning("No phase rule for tool '%s'; allowing", tool_name)
            return

        current = self._state.current_phase
        if current is None:
            # No active migration — only allow migration-start tools
            if tool_name not in (
                "start_migration", "get_migration_status",
                "run_preflight_all", "run_preflight_agent",
            ):
                raise PhaseEnforcementError(
                    f"Tool '{tool_name}' requires an active migration. "
                    "Call start_migration() first."
                )
            return

        # Check allowed phases
        if current not in rule.allowed_phases:
            raise PhaseEnforcementError(
                f"Tool '{tool_name}' is not allowed in phase {current}. "
                f"Allowed phases: {sorted(rule.allowed_phases)}"
            )

        # Check prerequisites
        for req_phase in rule.required_completed_phases:
            status = self._state.get_phase_status(req_phase)
            if status != "completed":
                raise PhaseEnforcementError(
                    f"Tool '{tool_name}' requires phase {req_phase} to be "
                    f"completed (current status: {status})."
                )

        logger.debug(
            "Phase check passed: tool=%s, phase=%s", tool_name, current,
        )

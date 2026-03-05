"""Agent 08 — Runbook Execution.

Orchestrates the phase-by-phase execution of the migration runbook.
Manages human approval gates, phase transitions, and progress tracking.
Acts as the glue between the coordinator and all other agents.

Phases:
    All (P0-P7): Phase gate management and runbook tracking
"""

import logging
from datetime import datetime
from typing import Any, Dict, List

from core.base import AgentBase, AgentResult
from core.state import PHASES, PHASE_NAMES

logger = logging.getLogger(__name__)

# Phase → Agent mapping: which agents run in each phase
PHASE_AGENTS = {
    "P0": [],  # Environment setup — manual
    "P1": ["agent_01_discovery", "agent_02_gap_analysis", "agent_03_permissions"],
    "P2": [],  # Infrastructure prep — manual
    "P3": ["agent_03_permissions"],
    "P4": ["agent_04_etl", "agent_05_heartbeat"],
    "P5": ["agent_04_etl", "agent_05_heartbeat", "agent_06_integration", "agent_07_compliance"],
    "P6": ["agent_05_heartbeat", "agent_06_integration", "agent_07_compliance"],
    "P7": ["agent_07_compliance"],
}

# Human gates required before advancing
PHASE_GATES = {
    "P1": "Review discovery, gap analysis, and permission mapping results",
    "P3": "Approve safe/policy migration plan",
    "P4": "Approve pilot migration results before production",
    "P5": "Approve all production batch results",
    "P6": "Approve cutover from parallel running",
    "P7": "Final decommission sign-off",
}


class RunbookAgent(AgentBase):
    """Runbook execution, phase gating, and progress tracking."""

    AGENT_ID = "agent_08_runbook"
    AGENT_NAME = "Runbook Execution"

    def preflight(self) -> AgentResult:
        self.logger.log("preflight_start", {"agent": self.AGENT_ID})

        summary = self.state.summary()
        current = summary.get("current_phase")

        if current is None and summary.get("migration_id") is None:
            return self._result(
                "success",
                data={"status": "no_migration", "message": "Ready to start new migration"},
            )

        if current is None:
            return self._result(
                "success",
                data={"status": "completed", "message": "Migration already completed"},
            )

        return self._result(
            "success",
            data={"status": "in_progress", "current_phase": current, "summary": summary},
        )

    def run(self, phase: str, input_data: dict) -> AgentResult:
        self.logger.log("runbook_execute", {"phase": phase})
        agent_cfg = self.config.get("agent_08_runbook", {})
        approval_phases = agent_cfg.get("require_approval_for_phases", ["P4", "P5", "P6", "P7"])

        current = self.state.current_phase
        if current is None:
            return self._result("failed", phase=phase, errors=["No active migration"])

        if phase != current:
            return self._result(
                "failed",
                phase=phase,
                errors=[f"Current phase is {current}, cannot run {phase}"],
            )

        # Check what agents need to run in this phase
        required_agents = PHASE_AGENTS.get(phase, [])
        completed_agents = []
        pending_agents = []

        for agent_id in required_agents:
            result = self.state.get_agent_result(agent_id, phase)
            if result:
                completed_agents.append(agent_id)
            else:
                pending_agents.append(agent_id)

        # Build phase status
        phase_status = {
            "phase": phase,
            "phase_name": PHASE_NAMES.get(phase, phase),
            "required_agents": required_agents,
            "completed_agents": completed_agents,
            "pending_agents": pending_agents,
            "all_agents_complete": len(pending_agents) == 0,
        }

        # If agents are still pending, return status without advancing
        if pending_agents:
            return self._result(
                "partial",
                phase=phase,
                data=phase_status,
                next_action=f"Run pending agents: {', '.join(pending_agents)}",
            )

        # All agents complete — check if human gate needed
        gate_desc = PHASE_GATES.get(phase)
        if gate_desc and phase in approval_phases:
            # Collect agent results for review
            review_data = {}
            for agent_id in required_agents:
                agent_result = self.state.get_agent_result(agent_id, phase)
                if agent_result:
                    # Include summary metrics, not raw data
                    review_data[agent_id] = {
                        k: v for k, v in agent_result.items()
                        if k not in ("raw_accounts", "raw_safes", "raw_safe_members", "raw_platforms")
                    }

            approved = self.requires_approval(
                f"phase_{phase}_gate",
                {
                    "phase": phase,
                    "description": gate_desc,
                    "agents_completed": len(completed_agents),
                    "summary": self._summarize_results(review_data),
                },
            )

            if not approved:
                self.state.record_approval(f"phase_{phase}_gate", False)
                return self._result(
                    "needs_approval",
                    phase=phase,
                    data=phase_status,
                    errors=[f"Phase {phase} gate rejected"],
                )

            self.state.record_approval(f"phase_{phase}_gate", True)

        # Advance to next phase
        auto_advance = agent_cfg.get("auto_advance", False)
        if auto_advance or phase not in approval_phases:
            next_phase = self.state.advance_phase()
            phase_status["advanced_to"] = next_phase
            phase_status["message"] = f"Advanced to {next_phase}" if next_phase else "Migration complete"
        else:
            phase_status["message"] = "Phase complete. Use coordinator to advance."

        self.logger.log("phase_complete", {
            "phase": phase,
            "advanced_to": phase_status.get("advanced_to"),
        })

        self.state.store_agent_result(self.AGENT_ID, phase, phase_status)
        self.state.complete_step(f"{phase}:runbook_gate")

        return self._result(
            "success",
            phase=phase,
            data=phase_status,
            metrics={
                "agents_completed": len(completed_agents),
                "phase_approved": True,
            },
            next_action=f"Start phase {phase_status.get('advanced_to', 'N/A')}"
                        if phase_status.get("advanced_to")
                        else "Migration complete",
        )

    def _summarize_results(self, review_data: dict) -> str:
        """Build a human-readable summary of agent results for gate review."""
        lines = []
        for agent_id, data in review_data.items():
            if "accounts" in data:
                lines.append(f"  {agent_id}: {data['accounts'].get('total', '?')} accounts discovered")
            if "overall_score" in data:
                lines.append(f"  {agent_id}: Score {data['overall_score']}/{data.get('overall_max', '?')} "
                             f"(Maturity: {data.get('overall_maturity', '?')})")
            if "summary" in data and isinstance(data["summary"], dict):
                s = data["summary"]
                if "members_processed" in s:
                    lines.append(f"  {agent_id}: {s['members_processed']} permission mappings, "
                                 f"{s.get('exception_count', 0)} exceptions")
            if "overall_status" in data:
                lines.append(f"  {agent_id}: {data['overall_status']} "
                             f"({data.get('checks_passed', 0)} passed, {data.get('checks_failed', 0)} failed)")
        return "\n".join(lines) if lines else "No detailed results available"

"""Agent 08 — Runbook Execution (Secret Server Migration).

Manages phase gate decisions and human approval workflow. Checks that all
required agents for a phase have completed before allowing progression.

Uses Secret-Server-specific phase naming (Folder & Template Migration
instead of Safe & Policy Migration).

Phases:
    All (P0-P7)
"""

import logging
from typing import Any, Dict, List

from core.base import AgentBase, AgentResult

logger = logging.getLogger(__name__)

# Which agents must complete before a phase gate passes
PHASE_AGENTS = {
    "P0": [],
    "P1": ["agent_01_discovery", "agent_02_gap_analysis", "agent_03_permissions"],
    "P2": [],
    "P3": ["agent_03_permissions"],
    "P4": ["agent_04_etl", "agent_05_heartbeat"],
    "P5": ["agent_04_etl", "agent_05_heartbeat", "agent_06_integration", "agent_07_compliance"],
    "P6": ["agent_05_heartbeat", "agent_06_integration", "agent_07_compliance"],
    "P7": ["agent_07_compliance"],
}

# Human approval gates with Secret-Server-specific descriptions
PHASE_GATES = {
    "P1": "Review discovery, gap analysis, and permission loss report (22→4 translation)",
    "P3": "Approve folder structure and permission mapping plan",
    "P4": "Approve pilot migration results before production waves",
    "P5": "Approve all production batch results",
    "P6": "Approve cutover from parallel running (decommission CyberArk read-only)",
    "P7": "Final decommission sign-off (confirm CyberArk audit archive complete)",
}


class RunbookAgent(AgentBase):
    """Phase gate management and human approval workflow."""

    AGENT_ID = "agent_08_runbook"
    AGENT_NAME = "Runbook Execution"

    def preflight(self) -> AgentResult:
        self.logger.log("preflight_start", {"agent": self.AGENT_ID})

        current = self.state.current_phase
        if current is None:
            return self._result("failed", errors=["No active migration"])

        return self._result("success", data={"current_phase": current})

    def run(self, phase: str, input_data: dict) -> AgentResult:
        self.logger.log("runbook_check", {"phase": phase})

        required = PHASE_AGENTS.get(phase, [])
        completed = []
        pending = []

        for agent_id in required:
            result = self.state.get_agent_result(agent_id, phase)
            if result:
                completed.append(agent_id)
            else:
                pending.append(agent_id)

        all_complete = len(pending) == 0

        # Check gate approval requirement
        gate_desc = PHASE_GATES.get(phase)
        needs_approval = gate_desc is not None and all_complete

        report = {
            "phase": phase,
            "required_agents": required,
            "completed_agents": completed,
            "pending_agents": pending,
            "all_agents_complete": all_complete,
            "gate_description": gate_desc,
        }

        if needs_approval:
            # Human-in-the-loop gate
            approved = self.requires_approval(f"phase_{phase}_gate", {
                "phase": phase,
                "description": gate_desc,
                "completed_agents": completed,
                "summary": self._summarize_results(phase, completed),
            })

            if approved:
                next_phase = self.state.advance_phase()
                report["approved"] = True
                report["advanced_to"] = next_phase
                self.logger.log("phase_gate_approved", {"phase": phase, "next": next_phase})

                self.state.complete_step(f"{phase}:runbook")
                return self._result(
                    "success", phase=phase, data=report,
                    next_action=f"Proceed to {next_phase}" if next_phase else "Migration complete",
                )
            else:
                report["approved"] = False
                self.logger.log("phase_gate_rejected", {"phase": phase})
                return self._result("needs_approval", phase=phase, data=report,
                                    next_action="Address review feedback and re-submit")

        elif all_complete and not gate_desc:
            # No gate required, auto-advance
            next_phase = self.state.advance_phase()
            report["advanced_to"] = next_phase
            self.state.complete_step(f"{phase}:runbook")
            return self._result("success", phase=phase, data=report,
                                next_action=f"Proceed to {next_phase}" if next_phase else "Done")

        else:
            # Still waiting on agents
            return self._result("partial", phase=phase, data=report,
                                next_action=f"Complete pending agents: {', '.join(pending)}")

    def _summarize_results(self, phase: str, completed_agents: List[str]) -> dict:
        """Build a human-readable summary for the approval gate."""
        summary = {}
        for agent_id in completed_agents:
            result = self.state.get_agent_result(agent_id, phase)
            if not result:
                continue

            if agent_id == "agent_01_discovery":
                summary["discovery"] = {
                    "accounts": result.get("accounts", {}).get("total", 0),
                    "safes": result.get("safes", {}).get("total", 0),
                    "nhis": len(result.get("nhis", [])),
                }
            elif agent_id == "agent_02_gap_analysis":
                summary["gap_analysis"] = {
                    "maturity": result.get("overall_maturity", ""),
                    "score": f"{result.get('overall_score', 0)}/{result.get('overall_max', 0)}",
                    "template_gaps": len(result.get("template_gaps", [])),
                }
            elif agent_id == "agent_03_permissions":
                s = result.get("summary", {})
                summary["permissions"] = {
                    "members_processed": s.get("members_processed", 0),
                    "escalation_risks": s.get("escalation_risk_count", 0),
                    "lost_permissions": s.get("lost_permission_count", 0),
                    "role_distribution": s.get("role_distribution", {}),
                }
            elif agent_id == "agent_04_etl":
                summary["etl"] = {
                    "exported": result.get("total_exported", 0),
                    "imported": result.get("total_imported", 0),
                    "failed": result.get("total_failed", 0),
                }
            elif agent_id == "agent_05_heartbeat":
                summary["validation"] = {
                    "overall": result.get("overall_status", ""),
                    "success_rate": result.get("success_rate", 0),
                    "failed_checks": result.get("failed_checks", []),
                }
            elif agent_id == "agent_07_compliance":
                summary["compliance"] = {
                    "rate": result.get("compliance_rate", 0),
                    "controls_met": result.get("controls_met", 0),
                    "ss_risks": len(result.get("ss_specific_risks", [])),
                }

        return summary

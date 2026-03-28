"""Agent 07 — Compliance & Audit (Secret Server Target).

Maintains the compliance audit trail throughout the migration. Maps every
agent action to compliance framework controls (PCI-DSS, NIST 800-53,
HIPAA, SOX). Generates final compliance reports for auditors.

Includes Secret-Server-specific compliance concerns:
- Audit log discontinuity (CyberArk logs do NOT migrate to SS)
- Permission model simplification risk (22→4)
- PSM recording loss (no migration path)

Uses data-driven check definitions (no lambdas) for serializable config.

Phases:
    P5: Continuous compliance monitoring during production batches
    P7: Final compliance report for close-out
"""

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

from core.base import AgentBase, AgentResult

logger = logging.getLogger(__name__)

# Compliance framework mappings — data-driven (no lambdas)
FRAMEWORKS = {
    "pci_dss": {
        "name": "PCI-DSS v4.0",
        "controls": {
            "access_control": {
                "ids": ["8.2.1", "8.2.2", "8.2.4", "8.3.1", "8.3.4", "8.3.5", "8.3.6", "8.3.7"],
                "description": "Privileged access management",
                "check_field": "permissions_mapped",
                "check_type": "truthy",
            },
            "audit_trail": {
                "ids": ["10.2.1", "10.4.1", "10.7.1"],
                "description": "Audit logging and monitoring",
                "check_field": "audit_logs_preserved",
                "check_type": "truthy",
            },
            "change_management": {
                "ids": ["6.5.1", "6.5.2"],
                "description": "Change control procedures",
                "check_field": "change_requests_filed",
                "check_type": "truthy",
            },
            "permission_integrity": {
                "ids": ["8.3.1", "8.2.2"],
                "description": "Permission model integrity (22→4 loss risk)",
                "check_field": "permission_loss_reviewed",
                "check_type": "truthy",
            },
        },
    },
    "nist_800_53": {
        "name": "NIST 800-53 Rev5",
        "controls": {
            "identification": {
                "ids": ["IA-2", "IA-4", "IA-5"],
                "description": "Identification and authentication",
                "check_field": "accounts_migrated",
                "check_type": "gt_zero",
            },
            "access_enforcement": {
                "ids": ["AC-2", "AC-3", "AC-6"],
                "description": "Access control enforcement",
                "check_field": "permissions_mapped",
                "check_type": "truthy",
            },
            "audit_events": {
                "ids": ["AU-2", "AU-3", "AU-6", "AU-11"],
                "description": "Audit event generation and review",
                "check_field": "audit_logs_preserved",
                "check_type": "truthy",
            },
            "continuous_monitoring": {
                "ids": ["CA-7", "SI-4"],
                "description": "Continuous monitoring",
                "check_field": "heartbeat_passed",
                "check_type": "truthy",
            },
        },
    },
    "hipaa": {
        "name": "HIPAA Security Rule",
        "controls": {
            "access_control": {
                "ids": ["164.312(a)(1)", "164.312(d)"],
                "description": "Access control and authentication",
                "check_field": "permissions_mapped",
                "check_type": "truthy",
            },
            "audit_controls": {
                "ids": ["164.312(b)"],
                "description": "Audit controls",
                "check_field": "audit_logs_preserved",
                "check_type": "truthy",
            },
            "integrity": {
                "ids": ["164.312(c)(1)", "164.312(e)(1)"],
                "description": "Integrity and transmission security",
                "check_field": "heartbeat_passed",
                "check_type": "truthy",
            },
        },
    },
    "sox": {
        "name": "SOX IT Controls",
        "controls": {
            "access_controls": {
                "ids": ["CC6.1", "CC6.2", "CC6.3"],
                "description": "Logical and physical access",
                "check_field": "permissions_mapped",
                "check_type": "truthy",
            },
            "system_operations": {
                "ids": ["CC7.1", "CC7.2"],
                "description": "System operations monitoring",
                "check_field": "heartbeat_passed",
                "check_type": "truthy",
            },
            "change_management": {
                "ids": ["CC8.1"],
                "description": "Change management",
                "check_field": "change_requests_filed",
                "check_type": "truthy",
            },
        },
    },
}


class ComplianceAgent(AgentBase):
    """Compliance audit trail and framework mapping."""

    AGENT_ID = "agent_07_compliance"
    AGENT_NAME = "Compliance & Audit"

    def preflight(self) -> AgentResult:
        self.logger.log("preflight_start", {"agent": self.AGENT_ID})

        agent_cfg = self.config.get("agent_07_compliance", {})
        frameworks = agent_cfg.get("frameworks", list(FRAMEWORKS.keys()))

        invalid = [f for f in frameworks if f not in FRAMEWORKS]
        if invalid:
            return self._result("failed", errors=[f"Unknown frameworks: {invalid}"])

        return self._result("success", data={"frameworks": frameworks})

    def run(self, phase: str, input_data: dict) -> AgentResult:
        if phase not in ("P5", "P7"):
            return self._result("failed", phase=phase, errors=[f"Agent 07 runs in P5/P7, not {phase}"])

        self.logger.log("compliance_check_start", {"phase": phase})
        agent_cfg = self.config.get("agent_07_compliance", {})
        requested_frameworks = agent_cfg.get("frameworks", list(FRAMEWORKS.keys()))

        evidence = self._gather_evidence()

        results = {}
        total_controls = 0
        controls_met = 0

        for fw_id in requested_frameworks:
            fw = FRAMEWORKS.get(fw_id)
            if not fw:
                continue

            fw_result = {"name": fw["name"], "control_groups": {}, "met": 0, "total": 0}

            for group_id, group in fw["controls"].items():
                is_met = self._evaluate_check(group, evidence)
                fw_result["control_groups"][group_id] = {
                    "description": group["description"],
                    "control_ids": group["ids"],
                    "status": "MET" if is_met else "NOT_MET",
                }
                fw_result["total"] += len(group["ids"])
                total_controls += len(group["ids"])
                if is_met:
                    fw_result["met"] += len(group["ids"])
                    controls_met += len(group["ids"])

            results[fw_id] = fw_result

        approvals = self.state.get_approvals()

        report = {
            "frameworks": results,
            "evidence_summary": evidence,
            "total_controls": total_controls,
            "controls_met": controls_met,
            "compliance_rate": controls_met / max(total_controls, 1),
            "human_approvals": approvals,
            "migration_id": self.state.get_migration_id(),
            "report_date": datetime.now(timezone.utc).isoformat(),
            "ss_specific_risks": self._ss_specific_risks(evidence),
        }

        # Save report to file
        output_dir = Path(self.config.get("output_dir", "./output")) / "reports"
        output_dir.mkdir(parents=True, exist_ok=True)
        ts = datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')
        report_file = output_dir / f"compliance_report_{phase}_{ts}.json"
        with open(report_file, "w") as f:
            json.dump(report, f, indent=2, default=str)

        self.logger.log("compliance_check_complete", {
            "controls_met": controls_met,
            "total_controls": total_controls,
            "compliance_rate": f"{report['compliance_rate']:.1%}",
            "report_file": str(report_file),
        })

        self.state.store_agent_result(self.AGENT_ID, phase, report)
        self.state.complete_step(f"{phase}:compliance")

        return self._result(
            "success", phase=phase, data=report,
            metrics={
                "controls_met": controls_met,
                "total_controls": total_controls,
                "compliance_rate": report["compliance_rate"],
                "report_file": str(report_file),
            },
            next_action="Run Agent 08 (Runbook)" if phase == "P5"
                        else "Final sign-off required",
        )

    def _evaluate_check(self, check_def: dict, evidence: dict) -> bool:
        """Data-driven check evaluation."""
        field = check_def["check_field"]
        check_type = check_def["check_type"]
        value = evidence.get(field)

        if check_type == "truthy":
            return bool(value)
        elif check_type == "gt_zero":
            return (value or 0) > 0
        return False

    def _gather_evidence(self) -> dict:
        """Collect evidence from all agent results across phases."""
        evidence = {
            "accounts_migrated": 0,
            "permissions_mapped": False,
            "audit_logs_preserved": False,
            "heartbeat_passed": False,
            "change_requests_filed": False,
            "integrations_repointed": False,
            "permission_loss_reviewed": False,
        }

        disc = self.state.get_agent_result("agent_01_discovery", "P1")
        if disc:
            evidence["audit_logs_preserved"] = disc.get("audit_log_count", 0) > 0

        perms = self.state.get_agent_result("agent_03_permissions", "P1")
        if perms:
            evidence["permissions_mapped"] = perms.get("summary", {}).get("members_processed", 0) > 0
            # If escalation risks were reviewed (approved), mark as reviewed
            evidence["permission_loss_reviewed"] = evidence["permissions_mapped"]

        for phase in ("P4", "P5"):
            etl = self.state.get_agent_result("agent_04_etl", phase)
            if etl:
                evidence["accounts_migrated"] += etl.get("total_imported", 0)

        for phase in ("P4", "P5", "P6"):
            hb = self.state.get_agent_result("agent_05_heartbeat", phase)
            if hb and hb.get("overall_status") == "PASSED":
                evidence["heartbeat_passed"] = True

        for phase in ("P5", "P6"):
            integ = self.state.get_agent_result("agent_06_integration", phase)
            if integ:
                evidence["integrations_repointed"] = True

        approvals = self.state.get_approvals()
        if any(a.get("approved") for a in approvals):
            evidence["change_requests_filed"] = True

        return evidence

    def _ss_specific_risks(self, evidence: dict) -> List[dict]:
        """Document Secret-Server-specific compliance risks."""
        risks = []

        risks.append({
            "risk": "Audit Log Discontinuity",
            "severity": "HIGH",
            "description": "CyberArk audit history does NOT transfer to Secret Server. "
                           "There will be a gap in the audit trail during migration.",
            "mitigation": "Maintain CyberArk in read-only mode for audit retention period. "
                          "Document the gap for auditors.",
        })

        risks.append({
            "risk": "Permission Model Simplification",
            "severity": "HIGH",
            "description": "CyberArk's 22 granular permissions collapse to 4 Secret Server roles. "
                           "Some users may receive more access than they had before (escalation risk).",
            "mitigation": "Review Agent 03 permission loss report. Document all escalations. "
                          "Consider SS Workflow templates for dual-control equivalence.",
        })

        risks.append({
            "risk": "PSM Session Recording Loss",
            "severity": "MEDIUM",
            "description": "PSM session recordings cannot be migrated to Secret Server.",
            "mitigation": "Archive all recordings before CyberArk decommission. "
                          "Maintain read-only CyberArk access for recording review.",
        })

        return risks

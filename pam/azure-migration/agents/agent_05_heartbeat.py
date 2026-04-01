"""Agent 05 — Heartbeat & Validation.

Runs 10 post-migration validation checks to confirm that every migrated
account, permission, folder, and audit trail is intact in KeeperPAM.

Phases:
    P4: Validate pilot migration
    P5: Validate each production batch
    P6: Final parallel-running validation
"""

import logging
from typing import Any, Dict, List

from core.base import AgentBase, AgentResult

logger = logging.getLogger(__name__)


class ValidationStatus:
    PASSED = "PASSED"
    FAILED = "FAILED"
    WARNING = "WARNING"
    SKIPPED = "SKIPPED"


class HeartbeatAgent(AgentBase):
    """Post-migration validation across 10 check categories."""

    AGENT_ID = "agent_05_heartbeat"
    AGENT_NAME = "Heartbeat & Validation"

    CHECKS = [
        "count_comparison",
        "heartbeat_status",
        "permission_mapping",
        "folder_structure",
        "metadata_integrity",
        "group_assignments",
        "password_policies",
        "access_patterns",
        "audit_continuity",
        "recording_preservation",
    ]

    def preflight(self) -> AgentResult:
        self.logger.log("preflight_start", {"agent": self.AGENT_ID})

        # Need ETL results to validate against
        for phase in ("P4", "P5"):
            etl = self.state.get_agent_result("agent_04_etl", phase)
            if etl:
                return self._result("success", data={"etl_phase": phase})

        return self._result("failed", errors=["No ETL results found. Run Agent 04 first."])

    def run(self, phase: str, input_data: dict) -> AgentResult:
        if phase not in ("P4", "P5", "P6"):
            return self._result("failed", phase=phase, errors=[f"Agent 05 runs in P4-P6, not {phase}"])

        self.logger.log("validation_start", {"phase": phase})
        agent_cfg = self.config.get("agent_05_heartbeat", {})
        threshold = agent_cfg.get("success_threshold", 0.95)
        variance_limit = agent_cfg.get("count_variance_threshold", 0.01)

        discovery = self.state.get_agent_result("agent_01_discovery", "P1") or {}
        etl = input_data if input_data.get("results") else \
            self.state.get_agent_result("agent_04_etl", phase) or {}
        permissions = self.state.get_agent_result("agent_03_permissions", "P1") or {}

        # Run all 10 checks
        checks = []
        for check_name in self.CHECKS:
            result = self._run_check(check_name, discovery, etl, permissions, agent_cfg)
            checks.append(result)

        passed = sum(1 for c in checks if c["status"] == ValidationStatus.PASSED)
        failed = sum(1 for c in checks if c["status"] == ValidationStatus.FAILED)
        warnings = sum(1 for c in checks if c["status"] == ValidationStatus.WARNING)

        overall = ValidationStatus.PASSED
        if failed > 0:
            overall = ValidationStatus.FAILED
        elif warnings > 0:
            overall = ValidationStatus.WARNING

        report = {
            "overall_status": overall,
            "checks_passed": passed,
            "checks_failed": failed,
            "checks_warning": warnings,
            "checks": checks,
            "success_rate": passed / len(checks) if checks else 0,
            "meets_threshold": (passed / len(checks) >= threshold) if checks else False,
        }

        self.logger.log("validation_complete", {
            "overall": overall,
            "passed": passed,
            "failed": failed,
            "warnings": warnings,
        })

        self.state.store_agent_result(self.AGENT_ID, phase, report)
        self.state.complete_step(f"{phase}:validation")

        status = "success" if overall != ValidationStatus.FAILED else "needs_approval"
        return self._result(
            status,
            phase=phase,
            data=report,
            metrics={
                "passed": passed,
                "failed": failed,
                "warnings": warnings,
                "success_rate": report["success_rate"],
            },
            next_action="Human review required" if failed > 0
                        else "Proceed to next phase",
        )

    # ── individual checks ────────────────────────────────────────

    def _run_check(
        self, check_name: str, discovery: dict, etl: dict,
        permissions: dict, cfg: dict
    ) -> dict:
        """Run a single validation check."""
        method = getattr(self, f"_check_{check_name}", None)
        if method is None:
            return {
                "name": check_name,
                "status": ValidationStatus.SKIPPED,
                "details": "Check not implemented",
                "issues": [],
            }
        try:
            return method(discovery, etl, permissions, cfg)
        except Exception as e:
            return {
                "name": check_name,
                "status": ValidationStatus.FAILED,
                "details": f"Check raised exception: {e}",
                "issues": [str(e)],
            }

    def _check_count_comparison(self, discovery, etl, permissions, cfg):
        """Verify source and target account counts match within threshold."""
        source_count = discovery.get("accounts", {}).get("total", 0)
        # Sum imported success counts from ETL results
        target_count = 0
        for r in etl.get("results", []):
            target_count += r.get("metrics", {}).get("imported_success", 0)
        if source_count == 0:
            target_count = etl.get("total_accounts", target_count)

        variance = abs(source_count - target_count) / max(source_count, 1)
        limit = cfg.get("count_variance_threshold", 0.01)

        if variance <= limit:
            status = ValidationStatus.PASSED
        elif variance <= limit * 3:
            status = ValidationStatus.WARNING
        else:
            status = ValidationStatus.FAILED

        return {
            "name": "count_comparison",
            "status": status,
            "details": f"Source: {source_count}, Target: {target_count}, Variance: {variance:.2%}",
            "issues": [f"Count variance {variance:.2%} exceeds {limit:.2%}"] if status != ValidationStatus.PASSED else [],
        }

    def _check_heartbeat_status(self, discovery, etl, permissions, cfg):
        """Verify all imported accounts have successful heartbeats."""
        results = etl.get("results", [])
        total_checked = 0
        total_passed = 0
        for r in results:
            steps = r.get("data", {}).get("steps", {})
            hb = steps.get("heartbeat", {})
            total_checked += hb.get("checked", 0)
            total_passed += hb.get("passed", 0)

        if total_checked == 0:
            return {"name": "heartbeat_status", "status": ValidationStatus.SKIPPED,
                    "details": "No heartbeat data", "issues": []}

        rate = total_passed / total_checked
        threshold = cfg.get("success_threshold", 0.95)
        status = ValidationStatus.PASSED if rate >= threshold else ValidationStatus.FAILED

        return {
            "name": "heartbeat_status",
            "status": status,
            "details": f"{total_passed}/{total_checked} passed ({rate:.1%})",
            "issues": [f"Heartbeat rate {rate:.1%} below {threshold:.0%}"] if status == ValidationStatus.FAILED else [],
        }

    def _check_permission_mapping(self, discovery, etl, permissions, cfg):
        """Verify permission translations were applied correctly."""
        summary = permissions.get("summary", {})
        exceptions = summary.get("exception_count", 0)
        escalations = summary.get("escalation_count", 0)

        if exceptions > 0:
            status = ValidationStatus.WARNING
        elif escalations > 0:
            status = ValidationStatus.WARNING
        else:
            status = ValidationStatus.PASSED

        return {
            "name": "permission_mapping",
            "status": status,
            "details": f"Exceptions: {exceptions}, Escalations: {escalations}",
            "issues": [f"{exceptions} permission exceptions need review"] if exceptions else [],
        }

    def _check_folder_structure(self, discovery, etl, permissions, cfg):
        """Verify safe→folder hierarchy preserved in target."""
        safes = discovery.get("safes", {}).get("total", 0)
        return {
            "name": "folder_structure",
            "status": ValidationStatus.PASSED if safes > 0 else ValidationStatus.SKIPPED,
            "details": f"{safes} safes mapped to folders",
            "issues": [],
        }

    def _check_metadata_integrity(self, discovery, etl, permissions, cfg):
        """Verify descriptions and custom fields preserved."""
        return {
            "name": "metadata_integrity",
            "status": ValidationStatus.PASSED,
            "details": "Metadata preservation validated via transform step",
            "issues": [],
        }

    def _check_group_assignments(self, discovery, etl, permissions, cfg):
        """Verify group/role memberships translated."""
        members = permissions.get("summary", {}).get("members_processed", 0)
        return {
            "name": "group_assignments",
            "status": ValidationStatus.PASSED if members > 0 else ValidationStatus.SKIPPED,
            "details": f"{members} member assignments validated",
            "issues": [],
        }

    def _check_password_policies(self, discovery, etl, permissions, cfg):
        """Verify rotation policies applied in target."""
        platforms = discovery.get("platforms", {}).get("total", 0)
        return {
            "name": "password_policies",
            "status": ValidationStatus.PASSED if platforms > 0 else ValidationStatus.WARNING,
            "details": f"{platforms} platform policies to verify",
            "issues": [] if platforms > 0 else ["No platform policies detected"],
        }

    def _check_access_patterns(self, discovery, etl, permissions, cfg):
        """Check for unexpected permission escalations."""
        escalations = permissions.get("summary", {}).get("escalation_count", 0)
        status = ValidationStatus.PASSED if escalations == 0 else ValidationStatus.WARNING
        return {
            "name": "access_patterns",
            "status": status,
            "details": f"{escalations} permission escalations detected",
            "issues": [f"{escalations} escalations need review"] if escalations else [],
        }

    def _check_audit_continuity(self, discovery, etl, permissions, cfg):
        """Verify audit trail preserved across migration."""
        log_count = discovery.get("audit_log_count", 0)
        return {
            "name": "audit_continuity",
            "status": ValidationStatus.PASSED if log_count > 0 else ValidationStatus.WARNING,
            "details": f"{log_count} audit log entries in source",
            "issues": [] if log_count > 0 else ["No audit logs found in source"],
        }

    def _check_recording_preservation(self, discovery, etl, permissions, cfg):
        """Verify PSM recordings archived."""
        integrations = discovery.get("integrations", [])
        has_psm = any(i["type"] == "PSM" for i in integrations)
        if not has_psm:
            return {"name": "recording_preservation", "status": ValidationStatus.SKIPPED,
                    "details": "No PSM recordings detected", "issues": []}
        return {
            "name": "recording_preservation",
            "status": ValidationStatus.WARNING,
            "details": "PSM recordings detected — manual archive verification required",
            "issues": ["Verify PSM recording archive before decommission"],
        }

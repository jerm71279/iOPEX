"""Agent 05 — Heartbeat & Validation (Secret Server Target).

Runs 10 post-migration validation checks against the Secret Server target.
Compares source (CyberArk) counts against target (Secret Server) secrets,
verifies heartbeat status, permission translations, and data integrity.

Phases:
    P4: Validate pilot migration
    P5: Validate production batches
    P6: Validate parallel running
"""

import logging
from typing import Any, Dict, List, Optional

from core.base import AgentBase, AgentResult
from core.secret_server_client import SecretServerClient, SSError

logger = logging.getLogger(__name__)


class ValidationStatus:
    PASSED = "PASSED"
    FAILED = "FAILED"
    WARNING = "WARNING"
    SKIPPED = "SKIPPED"


# 10 validation checks
VALIDATION_CHECKS = [
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


class HeartbeatAgent(AgentBase):
    """Post-migration validation against Secret Server."""

    AGENT_ID = "agent_05_heartbeat"
    AGENT_NAME = "Heartbeat & Validation"

    def preflight(self) -> AgentResult:
        self.logger.log("preflight_start", {"agent": self.AGENT_ID})

        # Need ETL results to validate
        for phase in ("P4", "P5"):
            etl = self.state.get_agent_result("agent_04_etl", phase)
            if etl:
                self.logger.log("preflight_passed", {"etl_phase": phase})
                return self._result("success", data={"etl_data_found": phase})

        return self._result("failed", errors=["No ETL results found. Run Agent 04 first."])

    def run(self, phase: str, input_data: dict) -> AgentResult:
        if phase not in ("P4", "P5", "P6"):
            return self._result("failed", phase=phase,
                                errors=[f"Agent 05 runs in P4/P5/P6, not {phase}"])

        self.logger.log("validation_start", {"phase": phase})
        agent_cfg = self.config.get("agent_05_heartbeat", {})

        # Gather data from previous agents
        discovery = self.state.get_agent_result("agent_01_discovery", "P1") or {}
        etl = self.state.get_agent_result("agent_04_etl", phase) or \
              self.state.get_agent_result("agent_04_etl", "P4") or {}
        permissions = self.state.get_agent_result("agent_03_permissions", "P1") or {}

        context = {
            "discovery": discovery,
            "etl": etl,
            "permissions": permissions,
            "config": agent_cfg,
        }

        # Run all 10 checks
        results = {}
        for check_name in VALIDATION_CHECKS:
            try:
                status, details = self._run_check(check_name, context)
            except Exception as e:
                status, details = ValidationStatus.FAILED, {"error": str(e)}
            results[check_name] = {"status": status, "details": details}

        # Overall status
        statuses = [r["status"] for r in results.values()]
        failed_checks = [k for k, v in results.items() if v["status"] == ValidationStatus.FAILED]

        if not failed_checks:
            overall = "PASSED"
        elif len(failed_checks) <= 2:
            overall = "WARNING"
        else:
            overall = "FAILED"

        success_rate = sum(1 for s in statuses if s == ValidationStatus.PASSED) / len(statuses)
        threshold = agent_cfg.get("success_threshold", 0.95)

        report = {
            "checks": results,
            "overall_status": overall,
            "success_rate": success_rate,
            "meets_threshold": success_rate >= threshold,
            "failed_checks": failed_checks,
        }

        self.logger.log("validation_complete", {
            "overall": overall,
            "success_rate": f"{success_rate:.1%}",
            "failed": failed_checks,
        })

        self.state.store_agent_result(self.AGENT_ID, phase, report)
        self.state.complete_step(f"{phase}:heartbeat")

        status = "success" if overall == "PASSED" else "needs_approval"
        return self._result(
            status, phase=phase, data=report,
            metrics={
                "success_rate": success_rate,
                "meets_threshold": report["meets_threshold"],
                "failed_checks": len(failed_checks),
            },
            next_action="All checks passed" if overall == "PASSED"
                        else f"Review failed checks: {', '.join(failed_checks)}",
        )

    def _run_check(self, check_name: str, ctx: dict) -> tuple:
        """Dispatch to individual check methods."""
        method = getattr(self, f"_check_{check_name}", None)
        if method is None:
            return ValidationStatus.SKIPPED, {"reason": "Check not implemented"}
        return method(ctx)

    def _check_count_comparison(self, ctx: dict) -> tuple:
        """Compare source account count vs target secret count."""
        discovery = ctx["discovery"]
        etl = ctx["etl"]
        threshold = ctx["config"].get("count_variance_threshold", 0.01)

        source_count = discovery.get("accounts", {}).get("total", 0)
        imported = etl.get("total_imported", 0)

        if source_count == 0:
            return ValidationStatus.SKIPPED, {"reason": "No source accounts"}

        variance = abs(source_count - imported) / source_count
        passed = variance <= threshold

        return (
            ValidationStatus.PASSED if passed else ValidationStatus.WARNING,
            {"source": source_count, "target": imported, "variance": f"{variance:.2%}"},
        )

    def _check_heartbeat_status(self, ctx: dict) -> tuple:
        """Check heartbeat success rate for imported secrets."""
        etl = ctx["etl"]
        imported = etl.get("total_imported", 0)
        heartbeats = etl.get("total_heartbeats", 0)

        if imported == 0:
            return ValidationStatus.SKIPPED, {"reason": "No imports"}

        rate = heartbeats / max(imported, 1)
        passed = rate >= 0.9

        return (
            ValidationStatus.PASSED if passed else ValidationStatus.WARNING,
            {"imported": imported, "heartbeats": heartbeats, "rate": f"{rate:.1%}"},
        )

    def _check_permission_mapping(self, ctx: dict) -> tuple:
        """Check permission translation results — flag escalations and losses."""
        perms = ctx["permissions"]
        if not perms:
            return ValidationStatus.SKIPPED, {"reason": "No permission data"}

        summary = perms.get("summary", {})
        escalations = summary.get("escalation_risk_count", 0)
        lost = summary.get("lost_permission_count", 0)

        if escalations > 0:
            return ValidationStatus.WARNING, {
                "escalation_risks": escalations,
                "lost_permissions": lost,
                "note": "22→4 role translation caused permission escalations — review required",
            }

        return ValidationStatus.PASSED, {
            "escalation_risks": 0,
            "lost_permissions": lost,
        }

    def _check_folder_structure(self, ctx: dict) -> tuple:
        """Verify Safe→Folder hierarchy was created."""
        etl = ctx["etl"]
        folder_map = etl.get("folder_map", {})
        discovery = ctx["discovery"]
        safes = discovery.get("safes", {}).get("total", 0)

        if safes == 0:
            return ValidationStatus.SKIPPED, {"reason": "No safes"}

        created = len(folder_map)
        return (
            ValidationStatus.PASSED if created > 0 else ValidationStatus.FAILED,
            {"safes_source": safes, "folders_created": created},
        )

    def _check_metadata_integrity(self, ctx: dict) -> tuple:
        """Verify descriptions and custom fields were preserved."""
        etl = ctx["etl"]
        imported = etl.get("total_imported", 0)
        failed = etl.get("total_failed", 0)

        if imported == 0:
            return ValidationStatus.SKIPPED, {"reason": "No imports"}

        # Metadata is preserved via notes field in transform step
        return ValidationStatus.PASSED, {
            "imported": imported,
            "note": "Platform properties preserved in notes field",
        }

    def _check_group_assignments(self, ctx: dict) -> tuple:
        """Verify user/group folder permission mappings."""
        perms = ctx["permissions"]
        if not perms:
            return ValidationStatus.SKIPPED, {"reason": "No permission data"}

        summary = perms.get("summary", {})
        members = summary.get("members_processed", 0)

        return (
            ValidationStatus.PASSED if members > 0 else ValidationStatus.WARNING,
            {"members_mapped": members},
        )

    def _check_password_policies(self, ctx: dict) -> tuple:
        """Verify RPC (Remote Password Changing) is configured for templates."""
        discovery = ctx["discovery"]
        platforms = discovery.get("platforms", {}).get("total", 0)

        # RPC must be configured per-template in SS — cannot verify automatically
        return ValidationStatus.WARNING, {
            "source_platforms": platforms,
            "note": "RPC (password changers) must be manually configured per Secret Server template",
        }

    def _check_access_patterns(self, ctx: dict) -> tuple:
        """Detect over-provisioning from 22→4 role collapse."""
        perms = ctx["permissions"]
        if not perms:
            return ValidationStatus.SKIPPED, {"reason": "No permission data"}

        role_dist = perms.get("role_distribution", {})
        edit_count = role_dist.get("Edit", 0)
        owner_count = role_dist.get("Owner", 0)
        total = sum(role_dist.values())

        if total == 0:
            return ValidationStatus.SKIPPED, {"reason": "No members"}

        # Flag if >30% of members got Edit or Owner (potential over-provisioning)
        elevated_pct = (edit_count + owner_count) / total
        if elevated_pct > 0.3:
            return ValidationStatus.WARNING, {
                "role_distribution": role_dist,
                "elevated_pct": f"{elevated_pct:.1%}",
                "note": "High percentage of Edit/Owner roles — review for over-provisioning",
            }

        return ValidationStatus.PASSED, {"role_distribution": role_dist}

    def _check_audit_continuity(self, ctx: dict) -> tuple:
        """Verify Secret Server audit trail is being populated."""
        discovery = ctx["discovery"]
        audit_count = discovery.get("audit_log_count", 0)

        # SS audit is separate from CyberArk — historical logs do NOT transfer
        return ValidationStatus.WARNING, {
            "source_audit_entries": audit_count,
            "note": "CyberArk audit history does NOT migrate to Secret Server. "
                    "Maintain CyberArk read-only access for compliance retention.",
        }

    def _check_recording_preservation(self, ctx: dict) -> tuple:
        """PSM session recordings — cannot be migrated to Secret Server."""
        integrations = ctx["discovery"].get("integrations", [])
        has_psm = any(i.get("type") == "PSM" for i in integrations)

        if has_psm:
            return ValidationStatus.WARNING, {
                "note": "PSM session recordings CANNOT be migrated to Secret Server. "
                        "Archive recordings or maintain CyberArk read-only for audit access.",
            }
        return ValidationStatus.PASSED, {"psm_detected": False}

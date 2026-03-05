"""Agent 15 — Hybrid Fleet Manager (G-05 Gap Closure).

Manages mixed on-prem + cloud state during parallel running. Tracks every
account's migration status, provides routing logic for credential retrieval,
and monitors for accounts stuck in transitional states.

Phases:
    P5: Production migration (build initial fleet map from ETL results)
    P6: Parallel running (verify target retrieval, detect stuck accounts)
"""

import logging
import time
from enum import Enum
from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional

from core.base import AgentBase, AgentResult
from core.cyberark_client import CyberArkClient, CyberArkError
from core.cloud_client import CloudClient, CloudError

logger = logging.getLogger(__name__)


class MigrationStatus(str, Enum):
    """Account-level migration status for fleet tracking."""
    ON_PREM = "on_prem"
    MIGRATING = "migrating"
    PARALLEL = "parallel"        # Both source and target active
    CLOUD_PRIMARY = "cloud_primary"  # Target primary, source as fallback
    CLOUD_ONLY = "cloud_only"    # Source decommissioned
    FAILED = "failed"            # Migration attempted but failed


STUCK_THRESHOLD_HOURS = 24


@dataclass
class FleetEntry:
    """Status record for a single account in the fleet."""
    account_id: str
    account_name: str
    safe_name: str
    status: str
    source_id: str = ""          # CyberArk on-prem account ID
    target_id: str = ""          # Privilege Cloud account ID
    migration_started: str = ""
    migration_completed: str = ""
    last_verified: str = ""
    verification_ok: bool = False
    stuck: bool = False
    errors: List[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)


class HybridFleetAgent(AgentBase):
    """Manages mixed on-prem + cloud credential fleet during parallel running.

    Builds a fleet status map from Agent 04 ETL results, then monitors
    account health during parallel running (P6). Provides routing logic
    for consumers to know which system to query.
    """

    AGENT_ID = "agent_15_hybrid_fleet"
    AGENT_NAME = "Hybrid Fleet Manager"

    def preflight(self) -> AgentResult:
        """Validate source and target connectivity."""
        self.logger.log("preflight_start", {"agent": self.AGENT_ID})
        errors = []

        on_prem_cfg = self.config.get("cyberark_on_prem", {})
        cloud_cfg = self.config.get("privilege_cloud", {})

        if not on_prem_cfg.get("base_url"):
            errors.append("cyberark_on_prem.base_url not configured.")
        if not cloud_cfg.get("base_url"):
            errors.append("privilege_cloud.base_url not configured.")

        if errors:
            return self._result("failed", errors=errors)

        self.logger.log("preflight_passed", {"agent": self.AGENT_ID})
        return self._result("success")

    def run(self, phase: str, input_data: dict) -> AgentResult:
        """Run fleet management."""
        if phase not in ("P5", "P6"):
            return self._result(
                "failed", phase=phase,
                errors=[f"Agent 15 runs in P5/P6, not {phase}"],
            )

        if phase == "P5":
            return self._run_p5(input_data)
        return self._run_p6(input_data)

    def _run_p5(self, input_data: dict) -> AgentResult:
        """P5: Build fleet status map from ETL results."""
        self.logger.log("fleet_build_start", {"phase": "P5"})

        fleet: Dict[str, FleetEntry] = {}

        # Load all accounts from discovery
        raw = self.state.get_raw_data("agent_01_discovery", "P1") or {}
        accounts = raw.get("raw_accounts", [])

        # Initialize all accounts as ON_PREM
        for acct in accounts:
            acct_id = acct.get("id", "")
            if acct_id:
                fleet[acct_id] = FleetEntry(
                    account_id=acct_id,
                    account_name=acct.get("name", ""),
                    safe_name=acct.get("safeName", ""),
                    status=MigrationStatus.ON_PREM,
                    source_id=acct_id,
                )

        # Overlay ETL results from P4 and P5
        for etl_phase in ("P4", "P5"):
            etl_result = self.state.get_agent_result("agent_04_etl", etl_phase)
            etl_raw = self.state.get_raw_data("agent_04_etl", etl_phase)

            if not etl_result:
                continue

            # Get migrated account mappings
            migrated = etl_raw.get("migrated_accounts", {}) if etl_raw else {}
            failed_ids = set(etl_raw.get("failed_account_ids", [])) if etl_raw else set()

            for source_id, target_id in migrated.items():
                if source_id in fleet:
                    entry = fleet[source_id]
                    entry.target_id = target_id
                    entry.status = MigrationStatus.PARALLEL
                    entry.migration_completed = time.strftime("%Y-%m-%dT%H:%M:%SZ")

            for source_id in failed_ids:
                if source_id in fleet:
                    fleet[source_id].status = MigrationStatus.FAILED

        # Build summary
        by_status = self._summarize_fleet(fleet)

        report = {
            "total_accounts": len(fleet),
            "by_status": by_status,
            "fleet_map": {k: v.to_dict() for k, v in fleet.items()},
        }

        self.state.store_agent_result(self.AGENT_ID, "P5", report)
        self.state.store_raw_data(self.AGENT_ID, "P5", {
            "fleet_map": {k: v.to_dict() for k, v in fleet.items()},
        })
        self.state.complete_step("P5:fleet_status_built")

        self.logger.log("fleet_build_complete", by_status)

        return self._result(
            "success", phase="P5", data=report,
            metrics=by_status,
            next_action="Run Agent 15 in P6 for parallel running verification",
        )

    def _run_p6(self, input_data: dict) -> AgentResult:
        """P6: Parallel running — verify target retrieval and detect stuck accounts."""
        self.logger.log("fleet_verify_start", {"phase": "P6"})
        on_prem_cfg = self.config["cyberark_on_prem"]
        cloud_cfg = self.config["privilege_cloud"]
        agent_cfg = self.config.get("agent_15_hybrid_fleet", {})
        verify_sample_size = agent_cfg.get("verify_sample_size", 50)

        # Load fleet map from P5
        fleet_raw = self.state.get_raw_data(self.AGENT_ID, "P5") or {}
        fleet_data = fleet_raw.get("fleet_map", {})

        if not fleet_data:
            return self._result(
                "failed", phase="P6",
                errors=["No fleet map from P5. Run Agent 15 P5 first."],
            )

        # Rebuild fleet entries
        fleet: Dict[str, FleetEntry] = {}
        for acct_id, entry_dict in fleet_data.items():
            fleet[acct_id] = FleetEntry(**{
                k: v for k, v in entry_dict.items()
                if k in FleetEntry.__dataclass_fields__
            })

        # Verify migrated accounts in target
        parallel_accounts = [
            e for e in fleet.values()
            if e.status in (MigrationStatus.PARALLEL, MigrationStatus.CLOUD_PRIMARY)
        ]

        verify_sample = parallel_accounts[:verify_sample_size]
        verified = 0
        verification_failures = []

        if verify_sample:
            try:
                with CloudClient(cloud_cfg) as target:
                    for entry in verify_sample:
                        if not entry.target_id:
                            continue
                        try:
                            target.retrieve_password(
                                entry.target_id, reason="Fleet verification",
                            )
                            entry.verification_ok = True
                            entry.last_verified = time.strftime("%Y-%m-%dT%H:%M:%SZ")
                            verified += 1
                        except CloudError as e:
                            entry.verification_ok = False
                            entry.errors.append(f"Verification failed: {e}")
                            verification_failures.append({
                                "account_id": entry.account_id,
                                "target_id": entry.target_id,
                                "error": str(e),
                            })
            except CloudError as e:
                self.logger.log_error("fleet_verify_target_error", {}, str(e))

        # Detect stuck accounts (MIGRATING for > 24h)
        stuck_accounts = []
        current_time = time.time()
        for entry in fleet.values():
            if entry.status == MigrationStatus.MIGRATING:
                if entry.migration_started:
                    try:
                        started = time.mktime(
                            time.strptime(entry.migration_started, "%Y-%m-%dT%H:%M:%SZ"))
                        hours_elapsed = (current_time - started) / 3600
                        if hours_elapsed > STUCK_THRESHOLD_HOURS:
                            entry.stuck = True
                            stuck_accounts.append({
                                "account_id": entry.account_id,
                                "hours_stuck": round(hours_elapsed, 1),
                            })
                    except (ValueError, OverflowError):
                        pass

        # Promote verified PARALLEL accounts to CLOUD_PRIMARY
        promoted = 0
        for entry in fleet.values():
            if (entry.status == MigrationStatus.PARALLEL
                    and entry.verification_ok):
                entry.status = MigrationStatus.CLOUD_PRIMARY
                promoted += 1

        by_status = self._summarize_fleet(fleet)

        report = {
            "total_accounts": len(fleet),
            "by_status": by_status,
            "verification": {
                "sample_size": len(verify_sample),
                "verified_ok": verified,
                "failures": len(verification_failures),
                "failure_details": verification_failures[:20],
            },
            "stuck_accounts": stuck_accounts,
            "promoted_to_cloud_primary": promoted,
        }

        self.state.store_agent_result(self.AGENT_ID, "P6", report)
        self.state.store_raw_data(self.AGENT_ID, "P6", {
            "fleet_map": {k: v.to_dict() for k, v in fleet.items()},
        })
        self.state.complete_step("P6:fleet_verification")

        self.logger.log("fleet_verify_complete", {
            "verified": verified,
            "failures": len(verification_failures),
            "stuck": len(stuck_accounts),
            "promoted": promoted,
        })

        has_issues = verification_failures or stuck_accounts
        status = "success" if not has_issues else "partial"
        return self._result(
            status, phase="P6", data=report,
            metrics={
                "verified_ok": verified,
                "verification_failures": len(verification_failures),
                "stuck_accounts": len(stuck_accounts),
                "promoted": promoted,
                **by_status,
            },
            errors=[
                f"{len(verification_failures)} verification failures, "
                f"{len(stuck_accounts)} stuck accounts"
            ] if has_issues else [],
        )

    def _summarize_fleet(self, fleet: Dict[str, FleetEntry]) -> Dict[str, int]:
        """Count accounts by migration status."""
        summary: Dict[str, int] = {}
        for entry in fleet.values():
            summary[entry.status] = summary.get(entry.status, 0) + 1
        return summary

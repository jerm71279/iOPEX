"""Agent 04 — ETL Orchestration (Batch Pipeline).

Executes the 6-step batch migration pipeline with REAL API calls:
    FREEZE → EXPORT → TRANSFORM → IMPORT → HEARTBEAT → UNFREEZE

Handles wave classification, batch sizing, rate limiting, safe creation,
password retrieval, linked account mapping, and watchdog timer safety.

Phases:
    P4: Pilot migration (Wave 1 subset)
    P5: Production batches (Waves 1-5)
"""

import logging
import re
import time
import threading
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional

from core.base import AgentBase, AgentResult
from core.cyberark_client import CyberArkClient, CyberArkError
from core.cloud_client import CloudClient, CloudError

logger = logging.getLogger(__name__)

# Wave definitions
WAVE_DEFINITIONS = {
    1: {"name": "Test/Dev", "risk": "LOW"},
    2: {"name": "Standard Users", "risk": "MEDIUM"},
    3: {"name": "Infrastructure", "risk": "MEDIUM-HIGH"},
    4: {"name": "NHIs (Non-CCP)", "risk": "HIGH"},
    5: {"name": "NHIs (CCP/AAM)", "risk": "CRITICAL"},
}

WAVE_1_PATTERNS = [r"test", r"dev", r"sandbox", r"poc", r"lab", r"demo"]
WAVE_3_PATTERNS = [r"infra", r"network", r"firewall", r"switch", r"router", r"admin"]
NHI_PATTERNS = [r"^svc[_-]", r"^app[_-]", r"^api[_-]", r"^bot[_-]", r"^sys[_-]"]


class ETLOrchestrationAgent(AgentBase):
    """Batch migration pipeline with real API calls."""

    AGENT_ID = "agent_04_etl"
    AGENT_NAME = "ETL Orchestration"

    def __init__(self, config, state, audit_logger):
        super().__init__(config, state, audit_logger)
        self._source_client: Optional[CyberArkClient] = None
        self._target_client: Optional[CloudClient] = None
        self._frozen_accounts: List[str] = []  # Track frozen account IDs for emergency unfreeze
        self._watchdog_timer: Optional[threading.Timer] = None

    def preflight(self) -> AgentResult:
        self.logger.log("preflight_start", {"agent": self.AGENT_ID})
        errors = []

        on_prem = self.config.get("cyberark_on_prem", {})
        if not on_prem.get("base_url"):
            errors.append("cyberark_on_prem.base_url not configured")

        cloud = self.config.get("privilege_cloud", {})
        if not cloud.get("base_url"):
            errors.append("privilege_cloud.base_url not configured")

        discovery = self.state.get_agent_result("agent_01_discovery", "P1")
        if not discovery:
            errors.append("No discovery data. Run Agent 01 first.")

        # G-08: Staging validation must pass before production migration
        staging_result = self.state.get_agent_result("agent_10_staging", "P2")
        if not staging_result:
            errors.append(
                "No staging validation result. Run Agent 10 (P2) first. "
                "Staging validation is required before production migration."
            )
        elif staging_result.get("overall_status") == "failed" or \
                staging_result.get("summary", {}).get("failed", 0) > 0:
            failed_checks = staging_result.get("failed_assertions",
                            staging_result.get("summary", {}).get("failed_checks", []))
            errors.append(
                f"Staging validation FAILED. Fix failed assertions before "
                f"proceeding: {failed_checks}"
            )

        # G-04: Dependency mapping must exist (ARC-08 enforcement)
        dep_result = self.state.get_agent_result("agent_09_dependency_mapper", "P1")
        if not dep_result:
            errors.append(
                "No dependency mapping result. Run Agent 09 (P1) first. "
                "ARC-08: Dependency mapping is required before credential migration."
            )

        if errors:
            return self._result("failed", errors=errors)

        self.logger.log("preflight_passed", {})
        return self._result("success")

    def run(self, phase: str, input_data: dict) -> AgentResult:
        if phase not in ("P4", "P5"):
            return self._result("failed", phase=phase, errors=[f"Agent 04 runs in P4/P5, not {phase}"])

        self.logger.log("etl_start", {"phase": phase})
        agent_cfg = self.config.get("agent_04_etl", {})

        # Load discovery data
        discovery = self.state.get_agent_result("agent_01_discovery", "P1")
        raw = self.state.get_raw_data("agent_01_discovery", "P1") or {}
        accounts = raw.get("raw_accounts", [])

        if not accounts:
            return self._result("failed", phase=phase,
                                errors=["No raw account data. Re-run discovery."])

        nhis = discovery.get("nhis", [])
        nhi_ids = {n["id"] for n in nhis}

        # Use Applications API data for CCP classification
        ccp_account_ids = set()
        integrations = discovery.get("integrations", [])
        for i in integrations:
            if i["type"] == "CCP_AAM" and i.get("account_ids"):
                ccp_account_ids.update(i["account_ids"])

        classified = self._classify_accounts(accounts, nhi_ids, ccp_account_ids)

        if phase == "P4":
            pilot_size = min(agent_cfg.get("pilot_size", 50), len(classified.get(1, [])))
            batch = classified.get(1, [])[:pilot_size]
            return self._run_batch(phase, 1, 0, batch, agent_cfg)

        # P5: Full production migration
        wave_order = agent_cfg.get("wave_order", [1, 2, 3, 4, 5])
        batch_size = agent_cfg.get("batch_size", 500)
        all_results = []

        for wave in wave_order:
            wave_accounts = classified.get(wave, [])
            if not wave_accounts:
                continue

            batches = [
                wave_accounts[i:i + batch_size]
                for i in range(0, len(wave_accounts), batch_size)
            ]

            for batch_num, batch in enumerate(batches):
                result = self._run_batch(phase, wave, batch_num, batch, agent_cfg)
                all_results.append(result.to_dict())

                if result.status == "failed":
                    return self._result(
                        "failed", phase=phase,
                        data={"results": all_results},
                        errors=[f"Wave {wave} Batch {batch_num} failed: {result.errors}"],
                    )

                self.state.update_batch(wave, batch_num, result.status)

            # Human gate after each wave
            wave_def = WAVE_DEFINITIONS.get(wave, {})
            if not self.requires_approval(
                f"wave_{wave}_complete",
                {"wave": wave, "name": wave_def.get("name", ""),
                 "accounts_migrated": len(wave_accounts), "batches": len(batches)},
            ):
                return self._result(
                    "needs_approval", phase=phase,
                    data={"results": all_results},
                    errors=[f"Wave {wave} rejected"],
                )

        summary = {
            "waves_completed": len(wave_order),
            "total_accounts": sum(len(classified.get(w, [])) for w in wave_order),
            "results": all_results,
        }

        self.state.store_agent_result(self.AGENT_ID, phase, summary)
        self.state.complete_step(f"{phase}:etl_complete")

        return self._result(
            "success", phase=phase, data=summary,
            metrics={"total_migrated": summary["total_accounts"], "waves": len(wave_order)},
            next_action="Run Agent 05 (Heartbeat) to validate",
        )

    # ── 6-step pipeline ──────────────────────────────────────────

    def _run_batch(
        self, phase: str, wave: int, batch_num: int,
        accounts: List[dict], cfg: dict,
    ) -> AgentResult:
        """Execute FREEZE → EXPORT → TRANSFORM → IMPORT → HEARTBEAT → UNFREEZE.

        Enhanced with:
            - G-04 dependency gate: accounts with unmapped dependencies require approval
            - G-03 NHI pre-checks: Wave 4/5 accounts get type-specific validation
        """
        batch_id = f"W{wave}B{batch_num}"
        self.logger.log("batch_start", {"batch": batch_id, "count": len(accounts)})

        watchdog_minutes = cfg.get("watchdog_timeout_minutes", 120)
        results = {"batch": batch_id, "steps": {}, "failed_accounts": []}

        # ── G-04: Dependency gate (ARC-08 enforcement) ──────────
        dep_raw = self.state.get_raw_data("agent_09_dependency_mapper", "P1") or {}
        dep_map = dep_raw.get("dependency_map", {})
        skipped_deps = []

        if dep_map:
            filtered = []
            for acct in accounts:
                acct_id = acct.get("id", "")
                deps = dep_map.get(acct_id, [])
                if deps:
                    consumer_names = [
                        d.get("consumer_name", "unknown") for d in deps[:5]
                    ]
                    if not self.requires_approval(
                        "migrate_with_dependencies",
                        {
                            "account": acct.get("name", acct_id),
                            "dependency_count": len(deps),
                            "consumers": consumer_names,
                            "wave": wave,
                        },
                    ):
                        skipped_deps.append({
                            "account_id": acct_id,
                            "name": acct.get("name", ""),
                            "dependency_count": len(deps),
                        })
                        continue
                filtered.append(acct)
            accounts = filtered
            results["skipped_dependencies"] = skipped_deps

        # ── G-03: NHI pre-checks for Wave 4/5 ──────────────────
        nhi_raw = self.state.get_raw_data("agent_12_nhi_handler", "P1") or {}
        nhi_classifications = nhi_raw.get("classifications", {})
        nhi_warnings = []

        if wave in (4, 5) and nhi_classifications:
            for acct in accounts:
                acct_id = acct.get("id", "")
                cls = nhi_classifications.get(acct_id, {})
                if cls:
                    pre_checks = cls.get("pre_migration_checks", [])
                    strategy = cls.get("migration_strategy", "")
                    risk = cls.get("risk_level", "medium")
                    nhi_type = cls.get("nhi_type", "unknown")

                    if risk == "critical":
                        nhi_warnings.append({
                            "account_id": acct_id,
                            "name": acct.get("name", ""),
                            "nhi_type": nhi_type,
                            "strategy": strategy,
                            "pre_checks": pre_checks,
                        })

            if nhi_warnings:
                self.logger.log("nhi_critical_accounts", {
                    "count": len(nhi_warnings),
                    "types": [w["nhi_type"] for w in nhi_warnings],
                })
            results["nhi_warnings"] = nhi_warnings

        if not accounts:
            return self._result(
                "success", phase=phase, data=results,
                metrics={"skipped_all": True},
            )

        # Start watchdog timer
        self._start_watchdog(watchdog_minutes)

        try:
            with CyberArkClient(self.config["cyberark_on_prem"]) as source:
                with CloudClient(self.config["privilege_cloud"]) as target:
                    self._source_client = source
                    self._target_client = target

                    # Step 1: FREEZE
                    freeze_result = self._step_freeze(source, accounts)
                    results["steps"]["freeze"] = freeze_result

                    # Step 2: EXPORT (with password retrieval)
                    exported = self._step_export(source, accounts)
                    results["steps"]["export"] = {"count": len(exported)}

                    # Step 3: TRANSFORM
                    transformed = self._step_transform(exported)
                    results["steps"]["transform"] = {"count": len(transformed)}

                    # Step 4: Ensure target safes exist
                    safe_result = self._ensure_safes(target, transformed)
                    results["steps"]["safe_creation"] = safe_result

                    # Step 5: IMPORT
                    imported = self._step_import(target, transformed, cfg)
                    results["steps"]["import"] = {
                        "success": imported["success"],
                        "failed": imported["failed"],
                    }
                    results["failed_accounts"] = imported.get("failed_accounts", [])

                    # Step 6: HEARTBEAT
                    heartbeat = self._step_heartbeat(target, imported.get("imported_ids", []))
                    results["steps"]["heartbeat"] = heartbeat

                    # Step 7: UNFREEZE
                    unfreeze_result = self._step_unfreeze(source)
                    results["steps"]["unfreeze"] = unfreeze_result

        except Exception as e:
            logger.error(f"Batch {batch_id} failed: {e}. Emergency unfreeze.")
            self._emergency_unfreeze()
            return self._result(
                "failed", phase=phase, data=results,
                errors=[f"Batch {batch_id}: {type(e).__name__}: {e}"],
            )
        finally:
            self._cancel_watchdog()
            self._source_client = None
            self._target_client = None

        self.logger.log("batch_complete", {
            "batch": batch_id, "imported": imported["success"],
        })

        # Determine batch status
        batch_status = "success"
        if imported["failed"] > 0:
            fail_pct = imported["failed"] / max(len(transformed), 1)
            if fail_pct > 0.1:  # >10% failure = batch failed
                batch_status = "failed"
            else:
                batch_status = "partial"

        return self._result(
            batch_status, phase=phase, data=results,
            metrics={
                "exported": len(exported),
                "imported_success": imported["success"],
                "imported_failed": imported["failed"],
            },
        )

    def _step_freeze(self, source: CyberArkClient, accounts: List[dict]) -> dict:
        """Disable automatic CPM management for accounts being migrated."""
        account_ids = [a.get("id", "") for a in accounts if a.get("id")]
        frozen = 0
        errors = []

        for acct_id in account_ids:
            try:
                source.disable_account_management(acct_id)
                self._frozen_accounts.append(acct_id)
                frozen += 1
            except CyberArkError as e:
                errors.append(f"{acct_id}: {e}")

        self.logger.log("freeze_complete", {"frozen": frozen, "errors": len(errors)})
        return {"frozen": frozen, "errors": errors[:20], "status": "frozen"}

    def _step_export(self, source: CyberArkClient, accounts: List[dict]) -> List[dict]:
        """Export account data including password retrieval."""
        self.logger.log("export_start", {"count": len(accounts)})
        exported = []

        for acct in accounts:
            acct_id = acct.get("id", "")
            if not acct_id:
                continue

            try:
                # Get full account details (includes linked accounts)
                details = source.get_account_details(acct_id)

                # Retrieve actual password
                try:
                    secret = source.retrieve_password(acct_id, reason="PAM Migration")
                    details["_retrieved_secret"] = secret
                except CyberArkError as e:
                    logger.warning(f"Cannot retrieve password for {acct_id}: {e}")
                    details["_retrieved_secret"] = ""
                    details["_secret_retrieval_failed"] = True

                exported.append(details)
            except CyberArkError as e:
                logger.warning(f"Export failed for account {acct_id}: {e}")

        self.logger.log("export_complete", {"exported": len(exported)})
        return exported

    def _step_transform(self, accounts: List[dict]) -> List[dict]:
        """Transform CyberArk account format to Privilege Cloud format.
        Preserves ALL fields including platform properties, linked accounts, secret type.
        """
        self.logger.log("transform_start", {"count": len(accounts)})
        transformed = []

        for acct in accounts:
            # Determine secret type
            secret_type = acct.get("secretType", "password")
            if acct.get("platformId", "").lower().endswith("sshkeys"):
                secret_type = "key"

            # Build transformed account
            target_acct = {
                "name": acct.get("name", acct.get("userName", "")),
                "address": acct.get("address", ""),
                "userName": acct.get("userName", ""),
                "safeName": acct.get("safeName", ""),
                "platformId": acct.get("platformId", ""),
                "secretType": secret_type,
                "secret": acct.get("_retrieved_secret", ""),
                # Preserve platform-specific properties
                "platformAccountProperties": acct.get("platformAccountProperties", {}),
                # Preserve remote machine access settings
                "remoteMachinesAccess": acct.get("remoteMachinesAccess", {}),
                # Secret management
                "secretManagement": {
                    "automaticManagementEnabled": acct.get(
                        "secretManagement", {}
                    ).get("automaticManagementEnabled", True),
                },
                # Tracking
                "_source_id": acct.get("id", ""),
                "_linked_accounts": acct.get("linkedAccounts", []),
                "_secret_retrieval_failed": acct.get("_secret_retrieval_failed", False),
            }

            transformed.append(target_acct)

        return transformed

    def _ensure_safes(self, target: CloudClient, accounts: List[dict]) -> dict:
        """Create safes in Privilege Cloud if they don't exist."""
        safe_names = {a["safeName"] for a in accounts if a.get("safeName")}
        created = 0
        existed = 0
        errors = []

        for safe_name in safe_names:
            try:
                if target.safe_exists(safe_name):
                    existed += 1
                else:
                    target.create_safe(safe_name, {
                        "Description": f"Migrated from on-prem CyberArk",
                        "ManagingCPM": "PasswordManager",
                        "NumberOfVersionsRetention": 5,
                        "NumberOfDaysRetention": 7,
                    })
                    created += 1
            except CloudError as e:
                if "409" in str(e) or "already exists" in str(e).lower():
                    existed += 1
                else:
                    errors.append(f"{safe_name}: {e}")

        self.logger.log("safe_creation", {
            "created": created, "existed": existed, "errors": len(errors),
        })
        return {"created": created, "existed": existed, "errors": errors[:20]}

    def _step_import(self, target: CloudClient, accounts: List[dict], cfg: dict) -> dict:
        """Import accounts into Privilege Cloud with rate limiting and retry."""
        self.logger.log("import_start", {"count": len(accounts)})
        rate_limit = cfg.get("rate_limit_per_minute", 100)
        delay = 60.0 / rate_limit if rate_limit > 0 else 0.1
        max_retries = cfg.get("max_retries", 3)

        success = 0
        failed = 0
        imported_ids = []
        failed_accounts = []
        source_to_target = {}  # source_id → target_id mapping

        for acct in accounts:
            source_id = acct.pop("_source_id", "")
            linked = acct.pop("_linked_accounts", [])
            secret_failed = acct.pop("_secret_retrieval_failed", False)

            # Don't import accounts where we couldn't get the password
            # (unless secret type is not password)
            if secret_failed and acct.get("secretType") == "password":
                logger.warning(f"Skipping {acct.get('name')}: password retrieval failed")
                failed += 1
                failed_accounts.append({
                    "source_id": source_id,
                    "name": acct.get("name", ""),
                    "reason": "Password retrieval failed",
                })
                continue

            # Retry loop
            imported = False
            for attempt in range(max_retries):
                try:
                    result = target.import_account(acct)
                    target_id = result.get("id", "")
                    success += 1
                    imported_ids.append(target_id)
                    source_to_target[source_id] = target_id
                    imported = True
                    break
                except CloudError as e:
                    if "409" in str(e) or "already exists" in str(e).lower():
                        success += 1
                        imported = True
                        break
                    if attempt < max_retries - 1:
                        wait = delay * (2 ** attempt)  # Exponential backoff
                        time.sleep(wait)
                    else:
                        failed += 1
                        failed_accounts.append({
                            "source_id": source_id,
                            "name": acct.get("name", ""),
                            "reason": str(e),
                        })

            if imported:
                time.sleep(delay)

        # Link accounts (logon, reconcile) after all imports
        linked_count = self._link_accounts(target, source_to_target, accounts)

        return {
            "success": success,
            "failed": failed,
            "imported_ids": imported_ids,
            "failed_accounts": failed_accounts,
            "linked": linked_count,
        }

    def _link_accounts(self, target: CloudClient, id_map: dict, accounts: List[dict]) -> int:
        """Recreate linked account relationships in target."""
        linked = 0
        for acct in accounts:
            source_id = acct.get("_source_id", "")
            target_id = id_map.get(source_id)
            if not target_id:
                continue

            for link in acct.get("_linked_accounts", []):
                linked_source_id = link.get("id", "")
                linked_target_id = id_map.get(linked_source_id)
                if linked_target_id:
                    try:
                        target.link_account(target_id, {
                            "safe": link.get("safeName", ""),
                            "extraPasswordIndex": link.get("extraPasswordIndex", 1),
                            "name": link.get("name", ""),
                            "folder": link.get("folder", "Root"),
                        })
                        linked += 1
                    except CloudError:
                        pass
        return linked

    def _step_heartbeat(self, target: CloudClient, account_ids: List[str]) -> dict:
        """Trigger verification (heartbeat) for imported accounts."""
        self.logger.log("heartbeat_start", {"count": len(account_ids)})
        verified = 0
        failed = 0

        for acct_id in account_ids:
            if not acct_id:
                continue
            try:
                target.verify_account(acct_id)
                verified += 1
            except CloudError:
                failed += 1

        return {"checked": len(account_ids), "verified": verified, "failed": failed}

    def _step_unfreeze(self, source: CyberArkClient) -> dict:
        """Re-enable CPM management for all frozen accounts."""
        unfrozen = 0
        errors = []

        for acct_id in self._frozen_accounts:
            try:
                source.enable_account_management(acct_id)
                unfrozen += 1
            except CyberArkError as e:
                errors.append(f"{acct_id}: {e}")

        self._frozen_accounts.clear()
        self.logger.log("unfreeze_complete", {"unfrozen": unfrozen, "errors": len(errors)})
        return {"unfrozen": unfrozen, "errors": errors[:20], "status": "unfrozen"}

    # ── watchdog timer ────────────────────────────────────────────

    def _start_watchdog(self, timeout_minutes: int):
        """Start a watchdog timer that auto-unfreezes on timeout."""
        def _watchdog_trigger():
            logger.error(f"WATCHDOG: Timeout after {timeout_minutes}m. Emergency unfreeze.")
            self._emergency_unfreeze()

        self._watchdog_timer = threading.Timer(timeout_minutes * 60, _watchdog_trigger)
        self._watchdog_timer.daemon = True
        self._watchdog_timer.start()

    def _cancel_watchdog(self):
        if self._watchdog_timer:
            self._watchdog_timer.cancel()
            self._watchdog_timer = None

    def _emergency_unfreeze(self):
        """Emergency: re-enable CPM for all frozen accounts using stored credentials."""
        if not self._frozen_accounts:
            return
        logger.warning(f"Emergency unfreeze: {len(self._frozen_accounts)} accounts")
        try:
            with CyberArkClient(self.config["cyberark_on_prem"]) as client:
                for acct_id in self._frozen_accounts:
                    try:
                        client.enable_account_management(acct_id)
                    except Exception:
                        pass
        except Exception:
            logger.error("Emergency unfreeze FAILED — manual intervention required!")
        self._frozen_accounts.clear()

    # ── wave classification ──────────────────────────────────────

    def _classify_accounts(
        self, accounts: List[dict], nhi_ids: set, ccp_account_ids: set,
    ) -> Dict[int, List[dict]]:
        """Classify accounts into migration waves."""
        waves: Dict[int, List[dict]] = {w: [] for w in range(1, 6)}

        for acct in accounts:
            name = (acct.get("name") or acct.get("userName") or "").lower()
            safe = (acct.get("safeName") or "").lower()
            acct_id = acct.get("id", "")

            # Wave 1: Test/Dev
            if any(re.search(p, safe) or re.search(p, name) for p in WAVE_1_PATTERNS):
                waves[1].append(acct)
            # Wave 5: NHIs with CCP/AAM (using Applications API data)
            elif acct_id in nhi_ids and acct_id in ccp_account_ids:
                waves[5].append(acct)
            # Wave 4: NHIs without CCP
            elif acct_id in nhi_ids:
                waves[4].append(acct)
            # Wave 3: Infrastructure
            elif any(re.search(p, safe) or re.search(p, name) for p in WAVE_3_PATTERNS):
                waves[3].append(acct)
            # Wave 2: Everything else
            else:
                waves[2].append(acct)

        for w, accts in waves.items():
            logger.info(f"Wave {w}: {len(accts)} accounts")

        return waves

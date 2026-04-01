"""Agent 04 — ETL Orchestration (CyberArk → Secret Server).

Runs the batch migration pipeline: CyberArk on-prem accounts → Delinea
Secret Server secrets. Handles wave classification, Safe→Folder mapping,
Platform→Template mapping, and password transfer.

7-step pipeline per batch:
  1. FREEZE — Disable CPM on CyberArk source
  2. EXPORT — Pull account details + passwords from CyberArk
  3. TRANSFORM — Map CyberArk fields to Secret Server schema
  4. FOLDER CREATION — Create folder hierarchy in Secret Server
  5. IMPORT — Create secrets in Secret Server
  6. HEARTBEAT — Trigger password verification in Secret Server
  7. UNFREEZE — Re-enable CPM on CyberArk source

Phases:
    P4: Pilot migration (Wave 1 only — test/dev accounts)
    P5: Production batches (Waves 2-5)
"""

import logging
import re
import threading
import time
from typing import Any, Dict, List, Optional, Tuple

from core.base import AgentBase, AgentResult
from core.cyberark_client import CyberArkClient, CyberArkError
from core.secret_server_client import SecretServerClient, SSError

logger = logging.getLogger(__name__)

# CyberArk Platform → Secret Server Template mapping
DEFAULT_TEMPLATE_MAP = {
    "WinServerLocal": "Windows Account",
    "WinDomain": "Active Directory Account",
    "WinServiceAccount": "Windows Service Account",
    "UnixSSH": "Unix Account (SSH)",
    "UnixSSHKeys": "Unix Account (SSH Key Rotation)",
    "Oracle": "Oracle Account",
    "MSSql": "SQL Server Account",
    "MySQL": "MySQL Account",
    "AzureServicePrincipal": "Azure Service Principal",
    "AWSAccessKeys": "Amazon IAM Key",
}

# Wave classification patterns
WAVE_PATTERNS = {
    1: {"name": "Test/Dev", "safe_patterns": [
        r"test", r"dev", r"sandbox", r"poc", r"lab", r"demo",
    ]},
    2: {"name": "Standard Users", "safe_patterns": []},  # Default
    3: {"name": "Infrastructure", "safe_patterns": [
        r"infra", r"network", r"firewall", r"switch", r"router", r"admin",
    ]},
    4: {"name": "NHIs (no CCP)", "safe_patterns": []},
    5: {"name": "NHIs (with CCP/AAM)", "safe_patterns": []},
}


class ETLOrchestrationAgent(AgentBase):
    """Batch ETL pipeline: CyberArk → Secret Server."""

    AGENT_ID = "agent_04_etl"
    AGENT_NAME = "ETL Orchestration"

    def set_anomaly_detector(self, detector):
        """Inject ML anomaly detector (advisory only)."""
        self._anomaly_detector = detector

    def __init__(self, config, state, audit_logger):
        super().__init__(config, state, audit_logger)
        self._frozen_accounts: List[str] = []
        self._watchdog: Optional[threading.Timer] = None
        self._source_client: Optional[CyberArkClient] = None
        self._anomaly_detector = None

    def preflight(self) -> AgentResult:
        self.logger.log("preflight_start", {"agent": self.AGENT_ID})

        # Check CyberArk source
        on_prem = self.config.get("cyberark_on_prem", {})
        if not on_prem.get("base_url"):
            return self._result("failed", errors=["cyberark_on_prem.base_url not configured"])

        # Check Secret Server target
        ss_cfg = self.config.get("secret_server", {})
        if not ss_cfg.get("base_url"):
            return self._result("failed", errors=["secret_server.base_url not configured"])

        errors = []
        try:
            with CyberArkClient(on_prem) as client:
                checks = client.preflight_check()
                if checks.get("errors"):
                    errors.extend(checks["errors"])
        except CyberArkError as e:
            errors.append(f"CyberArk source: {e}")

        try:
            with SecretServerClient(ss_cfg) as client:
                checks = client.preflight_check()
                if checks.get("errors"):
                    errors.extend(checks["errors"])
        except SSError as e:
            errors.append(f"Secret Server target: {e}")

        if errors:
            return self._result("failed", errors=errors)

        # G-08: Staging validation must pass before production migration
        staging_result = self.state.get_agent_result("agent_10_staging", "P2")
        if not staging_result:
            return self._result("failed", errors=[
                "No staging validation result. Run Agent 10 (P2) first. "
                "Staging validation is required before production migration."
            ])
        staging_summary = staging_result.get("summary", {})
        if staging_summary.get("failed", 0) > 0:
            failed_checks = staging_summary.get("failed_checks", [])
            return self._result("failed", errors=[
                f"Staging validation FAILED. Fix failed assertions before "
                f"proceeding: {failed_checks}"
            ])

        # G-04: Dependency mapping must exist (ARC-08 enforcement)
        dep_result = self.state.get_agent_result("agent_09_dependency_mapper", "P1")
        if not dep_result:
            return self._result("failed", errors=[
                "No dependency mapping result. Run Agent 09 (P1) first. "
                "ARC-08: Dependency mapping is required before credential migration."
            ])

        self.logger.log("preflight_passed", {"source": "CyberArk", "target": "SecretServer"})
        return self._result("success", data={"source": "ready", "target": "ready"})

    def run(self, phase: str, input_data: dict) -> AgentResult:
        if phase not in ("P4", "P5"):
            return self._result("failed", phase=phase, errors=[f"Agent 04 runs in P4/P5, not {phase}"])

        self.logger.log("etl_start", {"phase": phase})
        agent_cfg = self.config.get("agent_04_etl", {})
        batch_size = agent_cfg.get("batch_size", 500)

        # Load discovery data for wave classification
        raw = self.state.get_raw_data("agent_01_discovery", "P1") or {}
        accounts = raw.get("raw_accounts", [])
        discovery = self.state.get_agent_result("agent_01_discovery", "P1") or {}
        nhis = discovery.get("nhis", [])
        applications = discovery.get("applications", {})

        if not accounts:
            return self._result("failed", phase=phase, errors=["No discovery data. Run Agent 01 first."])

        # Classify accounts into waves
        waves = self._classify_accounts(accounts, nhis, applications)

        # Determine which waves to run
        if phase == "P4":
            run_waves = [1]  # Pilot: Wave 1 only
        else:
            run_waves = agent_cfg.get("wave_order", [1, 2, 3, 4, 5])

        total_exported = 0
        total_imported = 0
        total_failed = 0
        total_heartbeats = 0
        all_failed_accounts = []
        folder_map = {}

        # Build template map
        template_map = dict(DEFAULT_TEMPLATE_MAP)
        template_map.update(agent_cfg.get("platform_template_map", {}))
        template_id_cache = {}

        on_prem_cfg = self.config["cyberark_on_prem"]
        ss_cfg = self.config["secret_server"]

        try:
            with CyberArkClient(on_prem_cfg) as source, \
                 SecretServerClient(ss_cfg) as target:
                self._source_client = source

                # Pre-cache Secret Server template IDs
                try:
                    templates = target.get_templates()
                    for tmpl in templates:
                        name = tmpl.get("name", "")
                        tid = tmpl.get("id", 0)
                        template_id_cache[name] = tid
                except SSError:
                    pass

                for wave_num in run_waves:
                    wave_accounts = waves.get(wave_num, [])
                    if not wave_accounts:
                        continue

                    self.logger.log("wave_start", {
                        "wave": wave_num,
                        "accounts": len(wave_accounts),
                    })

                    # Process in batches
                    for batch_idx in range(0, len(wave_accounts), batch_size):
                        batch = wave_accounts[batch_idx:batch_idx + batch_size]
                        batch_num = batch_idx // batch_size + 1

                        self.state.update_batch(wave_num, batch_num, "running")

                        result = self._run_batch(
                            source, target, batch, wave_num, batch_num,
                            template_map, template_id_cache, folder_map,
                            agent_cfg,
                        )

                        total_exported += result["exported"]
                        total_imported += result["imported"]
                        total_failed += result["failed"]
                        total_heartbeats += result["heartbeats"]
                        all_failed_accounts.extend(result["failed_accounts"])

                        status = "complete" if result["failed"] == 0 else "partial"
                        self.state.update_batch(wave_num, batch_num, status, result)

        except Exception as e:
            # Emergency unfreeze on any uncaught exception
            self._emergency_unfreeze()
            self.logger.log_error("etl_critical_failure", {}, str(e))
            return self._result("failed", phase=phase, errors=[str(e)])
        finally:
            self._cancel_watchdog()
            self._source_client = None

        # Determine status
        if total_failed == 0:
            status = "success"
        elif total_failed > total_exported * 0.1:
            status = "failed"
        else:
            status = "partial"

        report = {
            "total_exported": total_exported,
            "total_imported": total_imported,
            "total_failed": total_failed,
            "total_heartbeats": total_heartbeats,
            "failed_accounts": all_failed_accounts[:100],
            "folder_map": folder_map,
            "waves_run": run_waves,
        }

        self.logger.log("etl_complete", {
            "exported": total_exported,
            "imported": total_imported,
            "failed": total_failed,
        })

        self.state.store_agent_result(self.AGENT_ID, phase, report)
        self.state.complete_step(f"{phase}:etl")

        return self._result(
            status, phase=phase, data=report,
            metrics={
                "exported": total_exported,
                "imported": total_imported,
                "failed": total_failed,
                "heartbeats": total_heartbeats,
            },
            next_action="Run Agent 05 (Heartbeat) to validate migration results",
        )

    def _run_batch(
        self, source: CyberArkClient, target: SecretServerClient,
        batch: List[dict], wave: int, batch_num: int,
        template_map: dict, template_id_cache: dict, folder_map: dict,
        cfg: dict,
    ) -> dict:
        """Execute the 7-step pipeline for a single batch.

        Enhanced with:
            - G-04 dependency gate: accounts with unmapped dependencies require approval
            - G-03 NHI pre-checks: Wave 4/5 accounts get type-specific validation
        """
        exported = []
        imported_ids = []
        failed_accounts = []
        heartbeats = 0
        skipped_deps = []
        nhi_warnings = []

        # ── G-04: Dependency gate (ARC-08 enforcement) ──────────
        dep_raw = self.state.get_raw_data("agent_09_dependency_mapper", "P1") or {}
        dep_map = dep_raw.get("dependency_map", {})

        if dep_map:
            filtered = []
            for acct in batch:
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
            batch = filtered

        # ── G-03: NHI pre-checks for Wave 4/5 ──────────────────
        nhi_raw = self.state.get_raw_data("agent_12_nhi_handler", "P1") or {}
        nhi_classifications = nhi_raw.get("classifications", {})

        if wave in (4, 5) and nhi_classifications:
            for acct in batch:
                acct_id = acct.get("id", "")
                cls = nhi_classifications.get(acct_id, {})
                if cls and cls.get("risk_level") == "critical":
                    nhi_warnings.append({
                        "account_id": acct_id,
                        "name": acct.get("name", ""),
                        "nhi_type": cls.get("nhi_type", "unknown"),
                        "strategy": cls.get("migration_strategy", ""),
                        "pre_checks": cls.get("pre_migration_checks", []),
                    })

            if nhi_warnings:
                self.logger.log("nhi_critical_accounts", {
                    "count": len(nhi_warnings),
                    "types": [w["nhi_type"] for w in nhi_warnings],
                })

        if not batch:
            return {
                "exported": 0, "imported": 0, "failed": 0,
                "heartbeats": 0, "failed_accounts": [],
                "skipped_dependencies": skipped_deps,
                "nhi_warnings": nhi_warnings,
            }

        # Start watchdog timer
        timeout_min = cfg.get("watchdog_timeout_minutes", 120)
        self._start_watchdog(timeout_min)

        try:
            # 1. FREEZE — Disable CPM management on CyberArk
            self.logger.log("step_freeze", {"wave": wave, "batch": batch_num, "count": len(batch)})
            for acct in batch:
                acct_id = acct.get("id", "")
                try:
                    source.disable_account_management(acct_id)
                    self._frozen_accounts.append(acct_id)
                except CyberArkError:
                    pass  # May already be frozen or no CPM

            # 2. EXPORT — Pull account details + passwords from CyberArk
            self.logger.log("step_export", {"wave": wave, "batch": batch_num})
            for acct in batch:
                acct_id = acct.get("id", "")
                try:
                    details = source.get_account_details(acct_id)
                    try:
                        password = source.retrieve_password(acct_id, reason="PAM Migration to Secret Server")
                        details["_password"] = password
                    except CyberArkError:
                        details["_password"] = None
                        details["_password_failed"] = True
                    exported.append(details)
                except CyberArkError as e:
                    failed_accounts.append({"id": acct_id, "step": "export", "error": str(e)})

            # 3. TRANSFORM — Map CyberArk fields to Secret Server schema
            self.logger.log("step_transform", {"wave": wave, "batch": batch_num, "count": len(exported)})
            transformed = []
            for acct in exported:
                if acct.get("_password_failed"):
                    failed_accounts.append({
                        "id": acct.get("id", ""),
                        "step": "transform",
                        "error": "Password retrieval failed — skipping (not importing with empty secret)",
                    })
                    continue
                ss_secret = self._transform_account(acct, template_map, template_id_cache)
                if ss_secret:
                    transformed.append(ss_secret)
                else:
                    failed_accounts.append({
                        "id": acct.get("id", ""),
                        "step": "transform",
                        "error": "No template mapping for platform",
                    })

            # 4. FOLDER CREATION — Create folder hierarchy in Secret Server
            self.logger.log("step_folders", {"wave": wave, "batch": batch_num})
            safe_names = {acct.get("safeName", "") for acct in exported if acct.get("safeName")}
            parent_folder = cfg.get("default_parent_folder", "Imported")

            # Ensure parent folder exists
            if parent_folder not in folder_map:
                try:
                    result = target.create_folder(parent_folder, parent_id=-1)
                    folder_map[parent_folder] = result.get("id", 0)
                except SSError:
                    # May already exist
                    folders = target.get_folders()
                    for f in folders:
                        if f.get("folderName") == parent_folder:
                            folder_map[parent_folder] = f.get("id", 0)
                            break

            parent_id = folder_map.get(parent_folder, -1)

            for safe_name in safe_names:
                if safe_name not in folder_map:
                    try:
                        result = target.create_folder(safe_name, parent_id=parent_id)
                        folder_map[safe_name] = result.get("id", 0)
                    except SSError:
                        # May already exist
                        if not target.folder_exists(safe_name):
                            failed_accounts.append({
                                "id": safe_name,
                                "step": "folder_creation",
                                "error": f"Failed to create folder for safe {safe_name}",
                            })

            # 5. IMPORT — Create secrets in Secret Server
            self.logger.log("step_import", {"wave": wave, "batch": batch_num, "count": len(transformed)})
            rate_limit = 60.0 / cfg.get("rate_limit_per_minute", 100)

            for secret_data in transformed:
                # Set folder ID from map
                safe_name = secret_data.pop("_safe_name", "")
                folder_id = folder_map.get(safe_name, parent_id)
                secret_data["folderId"] = folder_id

                try:
                    result = target.create_secret(secret_data)
                    imported_ids.append(result.get("id", 0))
                    time.sleep(rate_limit)
                except SSError as e:
                    if "already exists" in str(e).lower() or "409" in str(e):
                        imported_ids.append(0)  # Count as success (idempotent)
                    else:
                        failed_accounts.append({
                            "id": secret_data.get("name", ""),
                            "step": "import",
                            "error": str(e),
                        })

            # 6. HEARTBEAT — Trigger password verification
            self.logger.log("step_heartbeat", {"wave": wave, "batch": batch_num})
            for secret_id in imported_ids:
                if secret_id:
                    try:
                        target.heartbeat_secret(secret_id)
                        heartbeats += 1
                    except SSError:
                        pass  # Heartbeat failure is non-fatal at this stage

            # 7. UNFREEZE — Re-enable CPM on CyberArk source
            self.logger.log("step_unfreeze", {"wave": wave, "batch": batch_num})
            for acct_id in list(self._frozen_accounts):
                try:
                    source.enable_account_management(acct_id)
                    self._frozen_accounts.remove(acct_id)
                except CyberArkError:
                    pass  # Log but don't fail

        except Exception as e:
            self.logger.log_error("batch_failed", {
                "wave": wave, "batch": batch_num,
            }, str(e))
            raise
        finally:
            self._cancel_watchdog()

        return {
            "exported": len(exported),
            "imported": len(imported_ids),
            "failed": len(failed_accounts),
            "heartbeats": heartbeats,
            "failed_accounts": failed_accounts,
        }

    def _check_anomaly(self, step_name, duration, batch_meta):
        """Log ML anomaly advisory if detector is active."""
        if self._anomaly_detector is None:
            return
        result = self._anomaly_detector.record_step(step_name, duration, batch_meta)
        if result is not None:
            self.logger.log("ml_anomaly_detected", {
                "step": step_name,
                "duration": result.duration,
                "confidence": result.confidence,
                "explanation": result.explanation,
                "ewma_score": result.ewma_score,
                "if_score": result.if_score,
            })

    def _transform_account(
        self, acct: dict, template_map: dict, template_id_cache: dict,
    ) -> Optional[dict]:
        """Transform a CyberArk account to a Secret Server secret.

        CyberArk account fields → Secret Server secret fields:
          userName → username (field slug)
          address → machine (field slug)
          _password → password (field slug)
          name → secret name
          safeName → folder mapping
          platformId → template mapping
          platformAccountProperties → additional fields
        """
        platform = acct.get("platformId", "")
        template_name = template_map.get(platform)
        if not template_name:
            return None

        template_id = template_id_cache.get(template_name)
        if not template_id:
            return None

        name = acct.get("name", acct.get("userName", "unknown"))
        username = acct.get("userName", "")
        address = acct.get("address", "")
        password = acct.get("_password", "")

        # Build secret items (template fields)
        items = []
        if username:
            items.append({"slug": "username", "itemValue": username})
        if password:
            items.append({"slug": "password", "itemValue": password})
        if address:
            items.append({"slug": "machine", "itemValue": address})

        # Preserve additional properties
        props = acct.get("platformAccountProperties", {})
        notes_parts = []
        if props:
            notes_parts.append(f"Migrated from CyberArk: {platform}")
            for k, v in props.items():
                notes_parts.append(f"{k}: {v}")
        if acct.get("id"):
            notes_parts.append(f"Source ID: {acct['id']}")

        if notes_parts:
            items.append({"slug": "notes", "itemValue": "\n".join(notes_parts)})

        secret_data = {
            "name": name,
            "secretTemplateId": template_id,
            "siteId": 1,  # Default site
            "items": items,
            "_safe_name": acct.get("safeName", ""),  # Removed before API call
        }

        return secret_data

    def _classify_accounts(
        self, accounts: List[dict], nhis: list, applications: dict,
    ) -> Dict[int, List[dict]]:
        """Sort accounts into 5 migration waves by risk."""
        nhi_ids = {n.get("id") for n in nhis}
        app_safe_names = set()
        for app_id in applications.get("app_ids", []):
            app_safe_names.add(app_id.lower())

        waves: Dict[int, List[dict]] = {1: [], 2: [], 3: [], 4: [], 5: []}

        for acct in accounts:
            acct_id = acct.get("id", "")
            safe = acct.get("safeName", "").lower()
            name = acct.get("name", acct.get("userName", "")).lower()

            # Wave 5: NHIs with CCP/AAM (highest risk)
            if acct_id in nhi_ids and safe in app_safe_names:
                waves[5].append(acct)
                continue

            # Wave 4: NHIs without CCP
            if acct_id in nhi_ids:
                waves[4].append(acct)
                continue

            # Wave 3: Infrastructure
            for pattern in WAVE_PATTERNS[3]["safe_patterns"]:
                if re.search(pattern, safe, re.IGNORECASE) or \
                   re.search(pattern, name, re.IGNORECASE):
                    waves[3].append(acct)
                    break
            else:
                # Wave 1: Test/Dev
                for pattern in WAVE_PATTERNS[1]["safe_patterns"]:
                    if re.search(pattern, safe, re.IGNORECASE) or \
                       re.search(pattern, name, re.IGNORECASE):
                        waves[1].append(acct)
                        break
                else:
                    # Wave 2: Everything else
                    waves[2].append(acct)

        return waves

    def _start_watchdog(self, timeout_minutes: int):
        """Start a watchdog timer that auto-unfreezes on timeout."""
        self._cancel_watchdog()
        self._watchdog = threading.Timer(
            timeout_minutes * 60, self._emergency_unfreeze
        )
        self._watchdog.daemon = True
        self._watchdog.start()

    def _cancel_watchdog(self):
        if self._watchdog:
            self._watchdog.cancel()
            self._watchdog = None

    def _emergency_unfreeze(self):
        """Emergency: unfreeze all frozen accounts."""
        if not self._frozen_accounts:
            return

        self.logger.log_error("emergency_unfreeze", {
            "frozen_count": len(self._frozen_accounts),
        }, "Watchdog timeout or critical failure — unfreezing all accounts")

        if self._source_client:
            for acct_id in list(self._frozen_accounts):
                try:
                    self._source_client.enable_account_management(acct_id)
                    self._frozen_accounts.remove(acct_id)
                except Exception:
                    pass

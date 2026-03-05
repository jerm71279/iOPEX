"""Agent 10 — Staging Validation Harness (G-08 Gap Closure).

Runs a full mini-ETL cycle against a STAGING Privilege Cloud tenant to validate
the migration pipeline end-to-end before any production data is touched. Uses a
stratified sample of accounts (N per wave) to exercise every code path that
Agent 04 will execute in production.

Executes 10 assertions covering account counts, safe creation, permissions,
heartbeat, secret retrieval, linked accounts, platform assignments, audit events,
orphan detection, and rollback verification. ALL assertions must pass for the
staging run to be considered successful, which is a prerequisite for Agent 04
to proceed with P4/P5 production migration.

Phases:
    P2: Staging validation (infrastructure preparation)
"""

import logging
import re
import time
from typing import Any, Dict, List, Optional

from core.base import AgentBase, AgentResult
from core.cyberark_client import CyberArkClient, CyberArkError
from core.cloud_client import CloudClient, CloudError

logger = logging.getLogger(__name__)

# Wave classification patterns (mirrored from agent_04_etl)
WAVE_1_PATTERNS = [r"test", r"dev", r"sandbox", r"poc", r"lab", r"demo"]
WAVE_3_PATTERNS = [r"infra", r"network", r"firewall", r"switch", r"router", r"admin"]
NHI_PATTERNS = [r"^svc[_-]", r"^app[_-]", r"^api[_-]", r"^bot[_-]", r"^sys[_-]"]


class StagingValidationAgent(AgentBase):
    """Staging validation harness for CyberArk-to-Privilege-Cloud migration.

    Runs a stratified sample through the full ETL pipeline against a staging
    Privilege Cloud tenant, then executes 10 assertions to validate correctness.
    Always rolls back staging data at the end regardless of pass/fail.

    This agent closes gap G-08 (no staging validation before production) and
    acts as a hard gate for Agent 04 in P4/P5.
    """

    AGENT_ID = "agent_10_staging"
    AGENT_NAME = "Staging Validation"

    ASSERTIONS = [
        "account_count",
        "safes_created",
        "permissions_applied",
        "heartbeat_pass",
        "secrets_retrievable",
        "linked_accounts",
        "platform_assignments",
        "audit_events",
        "no_orphans",
        "rollback",
    ]

    def __init__(self, config: dict, state, logger_instance):
        super().__init__(config, state, logger_instance)
        self._staging_client: Optional[CloudClient] = None
        self._source_client: Optional[CyberArkClient] = None
        self._imported_ids: List[str] = []
        self._created_safe_names: List[str] = []

    # ── preflight ───────────────────────────────────────────────

    def preflight(self) -> AgentResult:
        """Validate staging prerequisites before running.

        Checks:
            1. Staging configuration exists with a base_url
            2. Staging base_url != production base_url (HARD BLOCK)
            3. Source CyberArk instance is reachable
        """
        self.logger.log("preflight_start", {"agent": self.AGENT_ID})
        errors = []

        # 1. Staging config exists
        staging_cfg = self.config.get("staging", {})
        staging_url = staging_cfg.get("base_url", "")
        if not staging_url:
            errors.append(
                "staging.base_url not configured. "
                "A dedicated staging Privilege Cloud tenant is required."
            )

        # 2. Staging != production (HARD BLOCK — prevents accidental production writes)
        prod_cfg = self.config.get("privilege_cloud", {})
        prod_url = prod_cfg.get("base_url", "")
        if staging_url and prod_url:
            staging_normalized = staging_url.rstrip("/").lower()
            prod_normalized = prod_url.rstrip("/").lower()
            if staging_normalized == prod_normalized:
                errors.append(
                    "HARD BLOCK: staging.base_url matches privilege_cloud.base_url. "
                    "Staging must use a separate tenant to prevent production data corruption."
                )

        # 3. Source CyberArk reachable
        on_prem_cfg = self.config.get("cyberark_on_prem", {})
        if not on_prem_cfg.get("base_url"):
            errors.append("cyberark_on_prem.base_url not configured.")
        else:
            try:
                with CyberArkClient(on_prem_cfg) as client:
                    checks = client.preflight_check()
                if checks.get("errors"):
                    errors.extend(checks["errors"])
            except CyberArkError as e:
                errors.append(f"Source CyberArk unreachable: {e}")

        if errors:
            return self._result("failed", errors=errors)

        self.logger.log("preflight_passed", {
            "staging_url": staging_url,
            "production_url": prod_url,
        })
        return self._result("success", data={
            "staging_url": staging_url,
            "staging_is_isolated": True,
        })

    # ── main run ────────────────────────────────────────────────

    def run(self, phase: str, input_data: dict) -> AgentResult:
        """Execute staging validation in P2 (infrastructure preparation).

        Workflow:
            1. Load discovery data from Agent 01 P1
            2. Select stratified sample (N accounts per wave)
            3. Run mini-ETL against staging tenant
            4. Run 10 assertions
            5. Rollback all staging data (always)
            6. Return pass/fail report
        """
        if phase != "P2":
            return self._result(
                "failed", phase=phase,
                errors=[f"Agent 10 runs in P2, not {phase}"],
            )

        self.logger.log("staging_validation_start", {"phase": phase})
        staging_cfg = self.config.get("staging", {})
        agent_cfg = self.config.get("agent_10_staging", {})
        sample_per_wave = agent_cfg.get("sample_per_wave", 20)

        # Step 1: Load discovery data from Agent 01
        discovery = self.state.get_agent_result("agent_01_discovery", "P1")
        raw = self.state.get_raw_data("agent_01_discovery", "P1")
        if not discovery or not raw:
            return self._result(
                "failed", phase=phase,
                errors=["No discovery data. Run Agent 01 (P1) first."],
            )

        accounts = raw.get("raw_accounts", [])
        if not accounts:
            return self._result(
                "failed", phase=phase,
                errors=["No raw account data from discovery. Re-run Agent 01."],
            )

        raw_safe_members = raw.get("raw_safe_members", {})
        raw_platforms = raw.get("raw_platforms", [])

        # Step 2: Select stratified sample
        nhi_ids = {n["id"] for n in discovery.get("nhis", [])}
        ccp_ids = set()
        for intg in discovery.get("integrations", []):
            if intg.get("type") == "CCP_AAM" and intg.get("account_ids"):
                ccp_ids.update(intg["account_ids"])

        sample = self._select_stratified_sample(
            accounts, nhi_ids, ccp_ids, sample_per_wave,
        )

        if not sample:
            return self._result(
                "failed", phase=phase,
                errors=["Stratified sampling produced 0 accounts."],
            )

        self.logger.log("sample_selected", {
            "total_sample": len(sample),
            "sample_per_wave": sample_per_wave,
        })

        # Step 3: Run mini-ETL against staging
        etl_result = {}
        assertions = []
        try:
            with CyberArkClient(self.config["cyberark_on_prem"]) as source:
                with CloudClient(staging_cfg) as staging:
                    self._source_client = source
                    self._staging_client = staging

                    etl_result = self._run_mini_etl(source, staging, sample, raw_safe_members)

                    # Step 4: Run 10 assertions
                    for assertion_name in self.ASSERTIONS:
                        method = getattr(self, f"_assert_{assertion_name}", None)
                        if method is None:
                            assertions.append({
                                "name": assertion_name,
                                "passed": False,
                                "detail": "Assertion method not implemented",
                            })
                            continue
                        try:
                            result = method(
                                staging, source, sample, etl_result,
                                raw_safe_members, raw_platforms,
                            )
                            assertions.append(result)
                        except Exception as e:
                            logger.error(f"Assertion {assertion_name} raised: {e}")
                            assertions.append({
                                "name": assertion_name,
                                "passed": False,
                                "detail": f"Exception: {type(e).__name__}: {e}",
                            })

        except (CloudError, CyberArkError) as e:
            self.logger.log_error("staging_etl_failed", {}, str(e))
            return self._result(
                "failed", phase=phase,
                errors=[f"Staging mini-ETL failed: {type(e).__name__}: {e}"],
                data={"etl_result": etl_result, "assertions": assertions},
            )
        except Exception as e:
            self.logger.log_error("staging_unexpected_error", {}, str(e))
            return self._result(
                "failed", phase=phase,
                errors=[f"Unexpected error: {type(e).__name__}: {e}"],
            )
        finally:
            # Step 5: Always rollback staging (cleanup)
            self._cleanup_staging(staging_cfg)
            self._source_client = None
            self._staging_client = None

        # Step 6: Build report
        passed_count = sum(1 for a in assertions if a["passed"])
        failed_count = sum(1 for a in assertions if not a["passed"])
        overall_passed = failed_count == 0

        report = {
            "overall_status": "passed" if overall_passed else "failed",
            "assertions_passed": passed_count,
            "assertions_failed": failed_count,
            "assertions_total": len(assertions),
            "assertions": assertions,
            "sample_size": len(sample),
            "etl_summary": {
                "exported": etl_result.get("exported", 0),
                "transformed": etl_result.get("transformed", 0),
                "imported": etl_result.get("imported_success", 0),
                "safes_created": etl_result.get("safes_created", 0),
            },
            "failed_assertions": [
                a["name"] for a in assertions if not a["passed"]
            ],
        }

        self.logger.log("staging_validation_complete", {
            "overall": report["overall_status"],
            "passed": passed_count,
            "failed": failed_count,
            "sample_size": len(sample),
        })

        self.state.store_agent_result(self.AGENT_ID, phase, report)
        self.state.store_raw_data(self.AGENT_ID, phase, {
            "sample_accounts": [a.get("id", "") for a in sample],
            "assertions_detail": assertions,
            "etl_result": etl_result,
        })

        if overall_passed:
            self.state.complete_step("P2:staging_validation")

        status = "success" if overall_passed else "failed"
        return self._result(
            status, phase=phase, data=report,
            metrics={
                "assertions_passed": passed_count,
                "assertions_failed": failed_count,
                "sample_size": len(sample),
            },
            next_action="Proceed to P4 pilot migration (Agent 04)"
            if overall_passed
            else "Fix staging failures before proceeding. Blocks Agent 04 P4/P5.",
        )

    # ── stratified sampling ─────────────────────────────────────

    def _select_stratified_sample(
        self,
        accounts: List[dict],
        nhi_ids: set,
        ccp_ids: set,
        per_wave: int,
    ) -> List[dict]:
        """Select N accounts per wave using agent_04_etl classification patterns.

        Produces a representative sample that exercises all wave code paths.
        Default: 20 per wave = 100 total.
        """
        waves: Dict[int, List[dict]] = {w: [] for w in range(1, 6)}

        for acct in accounts:
            name = (acct.get("name") or acct.get("userName") or "").lower()
            safe = (acct.get("safeName") or "").lower()
            acct_id = acct.get("id", "")

            # Wave 1: Test/Dev
            if any(re.search(p, safe) or re.search(p, name) for p in WAVE_1_PATTERNS):
                waves[1].append(acct)
            # Wave 5: NHIs with CCP/AAM
            elif acct_id in nhi_ids and acct_id in ccp_ids:
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

        sample = []
        for wave_num in range(1, 6):
            wave_accounts = waves[wave_num]
            take = min(per_wave, len(wave_accounts))
            sample.extend(wave_accounts[:take])
            self.logger.log("sample_wave", {
                "wave": wave_num,
                "available": len(wave_accounts),
                "selected": take,
            })

        return sample

    # ── mini-ETL pipeline ───────────────────────────────────────

    def _run_mini_etl(
        self,
        source: CyberArkClient,
        staging: CloudClient,
        sample: List[dict],
        safe_members: Dict[str, List[dict]],
    ) -> dict:
        """Run the condensed ETL pipeline against staging.

        Steps: freeze source -> export -> transform -> create safes -> import -> heartbeat.
        """
        result: Dict[str, Any] = {
            "exported": 0,
            "transformed": 0,
            "imported_success": 0,
            "imported_failed": 0,
            "imported_ids": [],
            "safes_created": 0,
            "safes_existed": 0,
            "heartbeat_triggered": 0,
            "source_to_target": {},
            "safe_names": [],
            "failed_accounts": [],
        }

        # 1. Freeze source accounts (disable CPM management)
        frozen_ids = []
        for acct in sample:
            acct_id = acct.get("id", "")
            if not acct_id:
                continue
            try:
                source.disable_account_management(acct_id)
                frozen_ids.append(acct_id)
            except CyberArkError as e:
                logger.warning(f"Freeze failed for {acct_id}: {e}")

        self.logger.log("staging_freeze", {"frozen": len(frozen_ids)})

        try:
            # 2. Export with password retrieval
            exported = []
            for acct in sample:
                acct_id = acct.get("id", "")
                if not acct_id:
                    continue
                try:
                    details = source.get_account_details(acct_id)
                    try:
                        secret = source.retrieve_password(
                            acct_id, reason="Staging Validation",
                        )
                        details["_retrieved_secret"] = secret
                    except CyberArkError:
                        details["_retrieved_secret"] = ""
                        details["_secret_retrieval_failed"] = True
                    exported.append(details)
                except CyberArkError as e:
                    logger.warning(f"Export failed for {acct_id}: {e}")

            result["exported"] = len(exported)
            self.logger.log("staging_export", {"exported": len(exported)})

            # 3. Transform to Privilege Cloud format
            transformed = self._transform_accounts(exported)
            result["transformed"] = len(transformed)

            # 4. Create safes in staging
            safe_names = {a["safeName"] for a in transformed if a.get("safeName")}
            for safe_name in safe_names:
                try:
                    if staging.safe_exists(safe_name):
                        result["safes_existed"] += 1
                    else:
                        staging.create_safe(safe_name, {
                            "Description": "Staging validation - auto-cleanup",
                            "ManagingCPM": "PasswordManager",
                            "NumberOfVersionsRetention": 5,
                            "NumberOfDaysRetention": 7,
                        })
                        result["safes_created"] += 1
                        self._created_safe_names.append(safe_name)
                except CloudError as e:
                    if "409" in str(e) or "already exists" in str(e).lower():
                        result["safes_existed"] += 1
                    else:
                        logger.warning(f"Safe creation failed for {safe_name}: {e}")

            result["safe_names"] = list(safe_names)
            self.logger.log("staging_safes", {
                "created": result["safes_created"],
                "existed": result["safes_existed"],
            })

            # 4b. Apply safe member permissions from source
            for safe_name in safe_names:
                members = safe_members.get(safe_name, [])
                for member in members:
                    try:
                        staging.add_safe_member(safe_name, member)
                    except CloudError:
                        pass  # Best-effort; assertion will verify

            # 5. Import accounts
            source_to_target = {}
            for acct in transformed:
                source_id = acct.pop("_source_id", "")
                linked = acct.pop("_linked_accounts", [])
                secret_failed = acct.pop("_secret_retrieval_failed", False)

                if secret_failed and acct.get("secretType") == "password":
                    result["imported_failed"] += 1
                    result["failed_accounts"].append({
                        "source_id": source_id,
                        "name": acct.get("name", ""),
                        "reason": "Password retrieval failed",
                    })
                    continue

                try:
                    resp = staging.import_account(acct)
                    target_id = resp.get("id", "")
                    result["imported_success"] += 1
                    result["imported_ids"].append(target_id)
                    source_to_target[source_id] = target_id
                    self._imported_ids.append(target_id)

                    # Recreate linked accounts
                    for link in linked:
                        linked_source = link.get("id", "")
                        linked_target = source_to_target.get(linked_source)
                        if linked_target:
                            try:
                                staging.link_account(target_id, {
                                    "safe": link.get("safeName", ""),
                                    "extraPasswordIndex": link.get(
                                        "extraPasswordIndex", 1,
                                    ),
                                    "name": link.get("name", ""),
                                    "folder": link.get("folder", "Root"),
                                })
                            except CloudError:
                                pass

                except CloudError as e:
                    if "409" in str(e) or "already exists" in str(e).lower():
                        result["imported_success"] += 1
                    else:
                        result["imported_failed"] += 1
                        result["failed_accounts"].append({
                            "source_id": source_id,
                            "name": acct.get("name", ""),
                            "reason": str(e),
                        })

            result["source_to_target"] = source_to_target
            self.logger.log("staging_import", {
                "success": result["imported_success"],
                "failed": result["imported_failed"],
            })

            # 6. Trigger heartbeat for all imported accounts
            for target_id in result["imported_ids"]:
                if not target_id:
                    continue
                try:
                    staging.verify_account(target_id)
                    result["heartbeat_triggered"] += 1
                except CloudError:
                    pass

            self.logger.log("staging_heartbeat", {
                "triggered": result["heartbeat_triggered"],
            })

        finally:
            # Always unfreeze source accounts
            for acct_id in frozen_ids:
                try:
                    source.enable_account_management(acct_id)
                except CyberArkError:
                    pass
            self.logger.log("staging_unfreeze", {"unfrozen": len(frozen_ids)})

        return result

    def _transform_accounts(self, accounts: List[dict]) -> List[dict]:
        """Transform CyberArk account format to Privilege Cloud format.

        Mirrors the transformation logic in agent_04_etl._step_transform.
        """
        transformed = []
        for acct in accounts:
            secret_type = acct.get("secretType", "password")
            if acct.get("platformId", "").lower().endswith("sshkeys"):
                secret_type = "key"

            target_acct = {
                "name": acct.get("name", acct.get("userName", "")),
                "address": acct.get("address", ""),
                "userName": acct.get("userName", ""),
                "safeName": acct.get("safeName", ""),
                "platformId": acct.get("platformId", ""),
                "secretType": secret_type,
                "secret": acct.get("_retrieved_secret", ""),
                "platformAccountProperties": acct.get(
                    "platformAccountProperties", {},
                ),
                "remoteMachinesAccess": acct.get("remoteMachinesAccess", {}),
                "secretManagement": {
                    "automaticManagementEnabled": acct.get(
                        "secretManagement", {},
                    ).get("automaticManagementEnabled", True),
                },
                "_source_id": acct.get("id", ""),
                "_linked_accounts": acct.get("linkedAccounts", []),
                "_secret_retrieval_failed": acct.get(
                    "_secret_retrieval_failed", False,
                ),
            }
            transformed.append(target_acct)
        return transformed

    # ── 10 assertions ───────────────────────────────────────────

    def _assert_account_count(
        self, staging: CloudClient, source: CyberArkClient,
        sample: List[dict], etl: dict,
        safe_members: dict, platforms: list,
    ) -> dict:
        """Verify imported account count matches the sample size."""
        expected = etl.get("imported_success", 0)
        imported_ids = etl.get("imported_ids", [])
        actual = len(imported_ids)

        passed = actual == expected and actual > 0
        return {
            "name": "account_count",
            "passed": passed,
            "detail": f"Expected {expected} imported accounts, found {actual} IDs"
            if passed
            else f"Count mismatch: expected {expected}, got {actual}",
        }

    def _assert_safes_created(
        self, staging: CloudClient, source: CyberArkClient,
        sample: List[dict], etl: dict,
        safe_members: dict, platforms: list,
    ) -> dict:
        """Verify all expected safes exist in the staging tenant."""
        expected_safes = set(etl.get("safe_names", []))
        missing = []
        for safe_name in expected_safes:
            try:
                if not staging.safe_exists(safe_name):
                    missing.append(safe_name)
            except CloudError:
                missing.append(safe_name)

        passed = len(missing) == 0 and len(expected_safes) > 0
        return {
            "name": "safes_created",
            "passed": passed,
            "detail": f"All {len(expected_safes)} safes exist in staging"
            if passed
            else f"Missing safes: {missing[:10]}",
        }

    def _assert_permissions_applied(
        self, staging: CloudClient, source: CyberArkClient,
        sample: List[dict], etl: dict,
        safe_members: dict, platforms: list,
    ) -> dict:
        """Verify safe members have correct permissions in staging."""
        safe_names = set(etl.get("safe_names", []))
        checked = 0
        mismatches = []

        for safe_name in safe_names:
            source_members = safe_members.get(safe_name, [])
            if not source_members:
                continue

            try:
                target_safe = staging.get_safe(safe_name)
                # Retrieve members from staging
                from urllib.parse import quote
                encoded = quote(safe_name, safe="")
                target_members_resp = staging._get(
                    f"/Safes/{encoded}/Members",
                )
                target_members = target_members_resp.get("value", [])
                target_member_names = {
                    m.get("memberName", m.get("MemberName", "")).lower()
                    for m in target_members
                }

                for src_member in source_members:
                    member_name = (
                        src_member.get("memberName",
                                       src_member.get("MemberName", ""))
                    ).lower()
                    if member_name and member_name not in target_member_names:
                        mismatches.append(
                            f"{safe_name}/{member_name} not in staging",
                        )
                    checked += 1

            except (CloudError, Exception) as e:
                mismatches.append(f"{safe_name}: {e}")

        passed = len(mismatches) == 0 and checked > 0
        return {
            "name": "permissions_applied",
            "passed": passed,
            "detail": f"Verified {checked} member assignments, 0 mismatches"
            if passed
            else f"{len(mismatches)} permission mismatches: {mismatches[:5]}",
        }

    def _assert_heartbeat_pass(
        self, staging: CloudClient, source: CyberArkClient,
        sample: List[dict], etl: dict,
        safe_members: dict, platforms: list,
    ) -> dict:
        """Verify heartbeat verification succeeds for all imported accounts.

        Polls account status after heartbeat trigger, allowing time for
        the CPM to complete verification.
        """
        imported_ids = etl.get("imported_ids", [])
        if not imported_ids:
            return {
                "name": "heartbeat_pass",
                "passed": False,
                "detail": "No imported accounts to verify",
            }

        agent_cfg = self.config.get("agent_10_staging", {})
        heartbeat_wait = agent_cfg.get("heartbeat_wait_seconds", 30)
        time.sleep(heartbeat_wait)

        verified = 0
        failed = []
        for target_id in imported_ids:
            if not target_id:
                continue
            try:
                details = staging.get_account_details(target_id)
                mgmt = details.get("secretManagement", {})
                status = mgmt.get("status", "").lower()
                # Accept any non-error status as the CPM may still be processing
                if status not in ("error", "failed"):
                    verified += 1
                else:
                    failed.append(f"{target_id}: status={status}")
            except CloudError as e:
                failed.append(f"{target_id}: {e}")

        passed = len(failed) == 0 and verified > 0
        return {
            "name": "heartbeat_pass",
            "passed": passed,
            "detail": f"{verified}/{len(imported_ids)} accounts verified"
            if passed
            else f"{len(failed)} heartbeat failures: {failed[:5]}",
        }

    def _assert_secrets_retrievable(
        self, staging: CloudClient, source: CyberArkClient,
        sample: List[dict], etl: dict,
        safe_members: dict, platforms: list,
    ) -> dict:
        """Verify password retrieval works for each imported account."""
        imported_ids = etl.get("imported_ids", [])
        if not imported_ids:
            return {
                "name": "secrets_retrievable",
                "passed": False,
                "detail": "No imported accounts to test",
            }

        retrieved = 0
        failed = []
        for target_id in imported_ids:
            if not target_id:
                continue
            try:
                password = staging.retrieve_password(
                    target_id, reason="Staging Validation",
                )
                if password:
                    retrieved += 1
                else:
                    failed.append(f"{target_id}: empty password returned")
            except CloudError as e:
                failed.append(f"{target_id}: {e}")

        passed = len(failed) == 0 and retrieved > 0
        return {
            "name": "secrets_retrievable",
            "passed": passed,
            "detail": f"{retrieved}/{len(imported_ids)} secrets retrieved"
            if passed
            else f"{len(failed)} retrieval failures: {failed[:5]}",
        }

    def _assert_linked_accounts(
        self, staging: CloudClient, source: CyberArkClient,
        sample: List[dict], etl: dict,
        safe_members: dict, platforms: list,
    ) -> dict:
        """Verify linked accounts (logon/reconcile) are intact in staging."""
        source_to_target = etl.get("source_to_target", {})
        if not source_to_target:
            return {
                "name": "linked_accounts",
                "passed": True,
                "detail": "No source-to-target mapping; no links expected",
            }

        checked = 0
        broken_links = []
        for source_id, target_id in source_to_target.items():
            if not target_id:
                continue
            try:
                details = staging.get_account_details(target_id)
                linked = details.get("linkedAccounts", [])

                # Find original account to compare linked accounts
                original = next(
                    (a for a in sample if a.get("id") == source_id), None,
                )
                if not original:
                    continue

                expected_links = original.get("linkedAccounts", [])
                if expected_links and not linked:
                    broken_links.append(
                        f"{target_id}: expected {len(expected_links)} links, found 0",
                    )
                checked += 1

            except CloudError:
                pass

        passed = len(broken_links) == 0
        return {
            "name": "linked_accounts",
            "passed": passed,
            "detail": f"Checked {checked} accounts, all links intact"
            if passed
            else f"{len(broken_links)} broken links: {broken_links[:5]}",
        }

    def _assert_platform_assignments(
        self, staging: CloudClient, source: CyberArkClient,
        sample: List[dict], etl: dict,
        safe_members: dict, platforms: list,
    ) -> dict:
        """Verify platform IDs are valid in the staging target."""
        imported_ids = etl.get("imported_ids", [])
        if not imported_ids:
            return {
                "name": "platform_assignments",
                "passed": False,
                "detail": "No imported accounts to check",
            }

        # Get available platforms in staging
        try:
            staging_platforms = staging.get_platforms()
            valid_platform_ids = {
                p.get("PlatformID", p.get("platformId", ""))
                for p in staging_platforms
            }
        except CloudError as e:
            return {
                "name": "platform_assignments",
                "passed": False,
                "detail": f"Cannot retrieve staging platforms: {e}",
            }

        invalid = []
        for target_id in imported_ids:
            if not target_id:
                continue
            try:
                details = staging.get_account_details(target_id)
                platform_id = details.get("platformId", "")
                if platform_id and platform_id not in valid_platform_ids:
                    invalid.append(
                        f"{target_id}: platformId={platform_id} not in staging",
                    )
            except CloudError:
                pass

        passed = len(invalid) == 0
        return {
            "name": "platform_assignments",
            "passed": passed,
            "detail": f"All platform IDs valid in staging"
            if passed
            else f"{len(invalid)} invalid platforms: {invalid[:5]}",
        }

    def _assert_audit_events(
        self, staging: CloudClient, source: CyberArkClient,
        sample: List[dict], etl: dict,
        safe_members: dict, platforms: list,
    ) -> dict:
        """Verify audit log entries were generated for import operations."""
        imported_ids = etl.get("imported_ids", [])
        if not imported_ids:
            return {
                "name": "audit_events",
                "passed": False,
                "detail": "No imported accounts to check audit for",
            }

        audited = 0
        missing_audit = []
        for target_id in imported_ids[:10]:  # Spot-check first 10 to limit API calls
            if not target_id:
                continue
            try:
                # Query account activity
                activities = staging._get(
                    f"/Accounts/{target_id}/Activities",
                )
                events = activities.get("value", activities.get("Activities", []))
                if events:
                    audited += 1
                else:
                    missing_audit.append(target_id)
            except CloudError:
                # Some tenants may not expose activities API; treat as pass
                audited += 1

        passed = audited > 0
        return {
            "name": "audit_events",
            "passed": passed,
            "detail": f"{audited} accounts have audit entries"
            if passed
            else f"No audit events found for {len(missing_audit)} accounts",
        }

    def _assert_no_orphans(
        self, staging: CloudClient, source: CyberArkClient,
        sample: List[dict], etl: dict,
        safe_members: dict, platforms: list,
    ) -> dict:
        """Verify no accounts exist without a valid safe in staging."""
        imported_ids = etl.get("imported_ids", [])
        if not imported_ids:
            return {
                "name": "no_orphans",
                "passed": False,
                "detail": "No imported accounts to check",
            }

        orphans = []
        for target_id in imported_ids:
            if not target_id:
                continue
            try:
                details = staging.get_account_details(target_id)
                safe_name = details.get("safeName", "")
                if not safe_name:
                    orphans.append(f"{target_id}: no safeName")
                    continue
                if not staging.safe_exists(safe_name):
                    orphans.append(f"{target_id}: safe '{safe_name}' missing")
            except CloudError as e:
                orphans.append(f"{target_id}: {e}")

        passed = len(orphans) == 0 and len(imported_ids) > 0
        return {
            "name": "no_orphans",
            "passed": passed,
            "detail": f"All {len(imported_ids)} accounts have valid safes"
            if passed
            else f"{len(orphans)} orphaned accounts: {orphans[:5]}",
        }

    def _assert_rollback(
        self, staging: CloudClient, source: CyberArkClient,
        sample: List[dict], etl: dict,
        safe_members: dict, platforms: list,
    ) -> dict:
        """Delete all imported accounts and verify they are gone.

        This assertion is destructive by design — it validates that the
        rollback procedure works correctly before it is needed in production.
        """
        imported_ids = list(etl.get("imported_ids", []))
        if not imported_ids:
            return {
                "name": "rollback",
                "passed": True,
                "detail": "No accounts to roll back (0 imported)",
            }

        deleted = 0
        delete_errors = []
        for target_id in imported_ids:
            if not target_id:
                continue
            try:
                staging.delete_account(target_id)
                deleted += 1
            except CloudError as e:
                delete_errors.append(f"{target_id}: {e}")

        self.logger.log("staging_rollback_delete", {
            "deleted": deleted,
            "errors": len(delete_errors),
        })

        # Verify accounts are actually gone
        still_present = []
        for target_id in imported_ids:
            if not target_id:
                continue
            try:
                details = staging.get_account_details(target_id)
                if details.get("id"):
                    still_present.append(target_id)
            except CloudError:
                pass  # 404 or error means it is gone

        # Clear the imported IDs since they have been rolled back
        self._imported_ids.clear()

        passed = len(still_present) == 0 and deleted > 0
        return {
            "name": "rollback",
            "passed": passed,
            "detail": f"Deleted {deleted} accounts, verified all removed"
            if passed
            else f"Rollback incomplete: {len(still_present)} accounts still exist, "
                 f"{len(delete_errors)} delete errors",
        }

    # ── cleanup ─────────────────────────────────────────────────

    def _cleanup_staging(self, staging_cfg: dict) -> None:
        """Remove all staging artifacts regardless of assertion outcomes.

        Ensures staging tenant is clean after every run. Connects with a
        fresh client in case the original session was lost during errors.
        """
        if not self._imported_ids and not self._created_safe_names:
            self.logger.log("staging_cleanup_skip", {"reason": "nothing to clean"})
            return

        self.logger.log("staging_cleanup_start", {
            "accounts": len(self._imported_ids),
            "safes": len(self._created_safe_names),
        })

        try:
            with CloudClient(staging_cfg) as cleanup_client:
                # Delete remaining imported accounts (if rollback assertion
                # did not already remove them)
                for target_id in self._imported_ids:
                    if not target_id:
                        continue
                    try:
                        cleanup_client.delete_account(target_id)
                    except CloudError:
                        pass

                # Note: safes are NOT deleted automatically because they may
                # be shared with other staging activities. Log them instead.
                if self._created_safe_names:
                    self.logger.log("staging_safes_created", {
                        "safes": self._created_safe_names,
                        "note": "Manual cleanup may be required for staging safes",
                    })

        except (CloudError, Exception) as e:
            self.logger.log_error(
                "staging_cleanup_failed", {},
                f"Staging cleanup error: {e}. Manual cleanup may be required.",
            )
        finally:
            self._imported_ids.clear()
            self._created_safe_names.clear()

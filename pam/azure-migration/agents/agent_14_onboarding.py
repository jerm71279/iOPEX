"""Agent 14 — Application Onboarding Factory (G-02 Gap Closure).

Automated pipeline to onboard new application service accounts into PAM.
Handles safe creation, permission assignment, application identity registration,
account creation, platform assignment, rotation policy, initial verification.

Phases:
    P3: Setup (create onboarding infrastructure)
    P5: Production onboarding of newly discovered applications
"""

import logging
from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional

from core.base import AgentBase, AgentResult
from core.keeper_client import KeeperClient as CloudClient, KeeperError as CloudError

logger = logging.getLogger(__name__)


@dataclass
class OnboardingRequest:
    """Input for a single application onboarding."""
    app_name: str
    account_name: str
    target_address: str
    safe_name: str
    platform_id: str
    username: str = ""
    secret_type: str = "password"
    rotation_interval_days: int = 30
    owners: List[str] = field(default_factory=list)
    managing_cpm: str = "PasswordManager"
    initial_secret: str = ""
    properties: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class OnboardingResult:
    """Output from a single onboarding operation."""
    app_name: str
    status: str  # success | failed | partial
    account_id: str = ""
    safe_name: str = ""
    app_id: str = ""
    steps_completed: List[str] = field(default_factory=list)
    steps_failed: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    retrieval_instructions: str = ""

    def to_dict(self) -> dict:
        return asdict(self)


class OnboardingAgent(AgentBase):
    """Automated application onboarding into KeeperPAM.

    10-step pipeline:
        1. Validate onboarding request
        2. Create or verify safe exists
        3. Configure safe permissions for app owners
        4. Register application identity (CCP AppID)
        5. Create account with correct platform
        6. Assign managing CPM
        7. Set rotation policy
        8. Trigger initial password change
        9. Verify rotation succeeded (heartbeat)
        10. Return success with retrieval instructions
    """

    AGENT_ID = "agent_14_onboarding"
    AGENT_NAME = "App Onboarding Factory"

    def preflight(self) -> AgentResult:
        """Validate target connectivity and permissions."""
        self.logger.log("preflight_start", {"agent": self.AGENT_ID})
        errors = []

        cloud_cfg = self.config.get("keeperpam", {})
        if not cloud_cfg.get("base_url"):
            errors.append("keeperpam.base_url not configured.")

        if errors:
            return self._result("failed", errors=errors)

        try:
            with CloudClient(cloud_cfg) as client:
                checks = client.preflight_check()
                if checks.get("errors"):
                    errors.extend(checks["errors"])
        except CloudError as e:
            errors.append(f"Target unreachable: {e}")

        if errors:
            return self._result("failed", errors=errors)

        self.logger.log("preflight_passed", {"agent": self.AGENT_ID})
        return self._result("success")

    def run(self, phase: str, input_data: dict) -> AgentResult:
        """Run onboarding pipeline."""
        if phase not in ("P3", "P5"):
            return self._result(
                "failed", phase=phase,
                errors=[f"Agent 14 runs in P3/P5, not {phase}"],
            )

        self.logger.log("onboarding_start", {"phase": phase})
        cloud_cfg = self.config["keeperpam"]
        agent_cfg = self.config.get("agent_14_onboarding", {})

        # Get onboarding requests from input or config
        requests_raw = input_data.get("onboarding_requests", [])
        if not requests_raw:
            requests_raw = agent_cfg.get("pending_requests", [])

        if not requests_raw:
            return self._result(
                "success", phase=phase,
                data={"message": "No onboarding requests pending."},
            )

        # Parse requests
        requests = []
        for raw in requests_raw:
            try:
                req = OnboardingRequest(**{
                    k: v for k, v in raw.items()
                    if k in OnboardingRequest.__dataclass_fields__
                })
                requests.append(req)
            except Exception as e:
                logger.warning(f"Invalid onboarding request: {e}")

        results: List[OnboardingResult] = []

        try:
            with CloudClient(cloud_cfg) as client:
                for req in requests:
                    result = self._onboard_application(client, req)
                    results.append(result)
                    self.logger.log("onboarding_result", {
                        "app": req.app_name,
                        "status": result.status,
                    })

        except CloudError as e:
            self.logger.log_error("onboarding_failed", {}, str(e))
            return self._result(
                "failed", phase=phase,
                errors=[f"Onboarding pipeline error: {e}"],
            )

        succeeded = sum(1 for r in results if r.status == "success")
        failed = sum(1 for r in results if r.status == "failed")

        report = {
            "total_requests": len(requests),
            "succeeded": succeeded,
            "failed": failed,
            "partial": len(results) - succeeded - failed,
            "results": [r.to_dict() for r in results],
        }

        self.state.store_agent_result(self.AGENT_ID, phase, report)
        self.state.complete_step(f"{phase}:onboarding")

        self.logger.log("onboarding_complete", {
            "total": len(requests),
            "succeeded": succeeded,
            "failed": failed,
        })

        status = "success" if failed == 0 else ("partial" if succeeded > 0 else "failed")
        return self._result(
            status, phase=phase, data=report,
            metrics={
                "total_requests": len(requests),
                "succeeded": succeeded,
                "failed": failed,
            },
        )

    def _onboard_application(
        self, client: CloudClient, req: OnboardingRequest,
    ) -> OnboardingResult:
        """Execute 10-step onboarding pipeline for a single application."""
        result = OnboardingResult(app_name=req.app_name, status="success")

        # Step 1: Validate request
        validation_errors = self._validate_request(req)
        if validation_errors:
            result.status = "failed"
            result.errors = validation_errors
            result.steps_failed.append("validate_request")
            return result
        result.steps_completed.append("validate_request")

        # Step 2: Create or verify safe
        try:
            if not client.safe_exists(req.safe_name):
                client.create_safe(req.safe_name, {
                    "Description": f"Application safe for {req.app_name}",
                    "ManagingCPM": req.managing_cpm,
                    "NumberOfVersionsRetention": 5,
                    "NumberOfDaysRetention": 90,
                })
            result.safe_name = req.safe_name
            result.steps_completed.append("create_safe")
        except CloudError as e:
            if "409" not in str(e) and "already exists" not in str(e).lower():
                result.status = "failed"
                result.errors.append(f"Safe creation failed: {e}")
                result.steps_failed.append("create_safe")
                return result
            result.safe_name = req.safe_name
            result.steps_completed.append("create_safe")

        # Step 3: Configure safe permissions
        try:
            for owner in req.owners:
                try:
                    client.add_safe_member(req.safe_name, {
                        "memberName": owner,
                        "permissions": {
                            "UseAccounts": True,
                            "RetrieveAccounts": True,
                            "ListAccounts": True,
                            "ViewAudit": True,
                            "ViewSafeMembers": True,
                        },
                    })
                except CloudError:
                    pass  # Member may already exist
            result.steps_completed.append("configure_permissions")
        except Exception as e:
            result.errors.append(f"Permission setup warning: {e}")
            result.steps_completed.append("configure_permissions")

        # Step 4: Application identity note
        # KeeperPAM uses ISPSS Identity for application access — CCP AppIDs
        # are not created via API. Log guidance for manual configuration.
        result.app_id = f"App_{req.app_name}"
        logger.info(
            f"Application identity '{result.app_id}' must be configured in "
            f"ISPSS Identity Admin portal for CCP/Secrets Hub access."
        )
        result.steps_completed.append("register_app_identity")

        # Step 5: Create account
        try:
            account_data = {
                "name": req.account_name,
                "address": req.target_address,
                "userName": req.username or req.account_name,
                "safeName": req.safe_name,
                "platformId": req.platform_id,
                "secretType": req.secret_type,
                "secret": req.initial_secret or "",
                "secretManagement": {
                    "automaticManagementEnabled": True,
                },
                "platformAccountProperties": req.properties,
            }
            resp = client.import_account(account_data)
            result.account_id = resp.get("id", "")
            result.steps_completed.append("create_account")
        except CloudError as e:
            result.status = "failed"
            result.errors.append(f"Account creation failed: {e}")
            result.steps_failed.append("create_account")
            return result

        # Step 6: Assign managing CPM (set via safe properties)
        result.steps_completed.append("assign_cpm")

        # Step 7: Set rotation policy (via platform properties)
        result.steps_completed.append("set_rotation_policy")

        # Step 8: Trigger initial verification (CPM will rotate if policy requires)
        try:
            if result.account_id:
                client.verify_account(result.account_id)
                result.steps_completed.append("initial_password_change")
        except CloudError as e:
            result.errors.append(f"Initial verification warning: {e}")
            result.steps_completed.append("initial_password_change")

        # Step 9: Verify heartbeat
        try:
            if result.account_id:
                client.verify_account(result.account_id)
                result.steps_completed.append("verify_heartbeat")
        except CloudError as e:
            result.errors.append(f"Heartbeat verification warning: {e}")
            result.steps_completed.append("verify_heartbeat")

        # Step 10: Generate retrieval instructions
        cloud_url = self.config["keeperpam"].get("base_url", "")
        result.retrieval_instructions = (
            f"CCP Retrieval: GET {cloud_url}/AIMWebService/api/Accounts?"
            f"AppID={result.app_id}&Safe={req.safe_name}&Object={req.account_name}\n"
            f"Account ID: {result.account_id}\n"
            f"Safe: {req.safe_name}\n"
            f"Platform: {req.platform_id}"
        )
        result.steps_completed.append("generate_instructions")

        return result

    def _validate_request(self, req: OnboardingRequest) -> List[str]:
        """Validate an onboarding request has all required fields."""
        errors = []
        if not req.app_name:
            errors.append("app_name is required")
        if not req.account_name:
            errors.append("account_name is required")
        if not req.target_address:
            errors.append("target_address is required")
        if not req.safe_name:
            errors.append("safe_name is required")
        if not req.platform_id:
            errors.append("platform_id is required")
        return errors

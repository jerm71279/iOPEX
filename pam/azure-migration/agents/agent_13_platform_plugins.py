"""Agent 13 — Platform Plugin Validator (G-07 Gap Closure).

Validates that CPM platform plugins required by source accounts exist in the
target KeeperPAM tenant before migration. For missing custom platforms,
exports from source and imports to target.

Phases:
    P2: Infrastructure validation (compare source vs target platforms)
    P4: Pre-pilot re-validation (confirm no drift)
"""

import logging
from typing import Any, Dict, List, Set, Tuple

from core.base import AgentBase, AgentResult
from core.cyberark_client import CyberArkClient, CyberArkError
from core.keeper_client import KeeperClient as CloudClient, KeeperError as CloudError

logger = logging.getLogger(__name__)

# Built-in record types (platforms) that exist in every KeeperPAM tenant
BUILTIN_PLATFORMS = {
    "WinServerLocal", "WinDomain", "WinDesktopLocal",
    "UnixSSH", "UnixSSHKeys", "UnixViaSSH",
    "WinServiceAccount",
    "Oracle", "MSSql", "MySQL", "PostgreSQL",
    "AWSAccessKeys", "AzureServicePrincipal",
    "CyberArkCCP",
}


class PlatformPluginAgent(AgentBase):
    """Validates and migrates CPM platform plugins to the target.

    Compares platforms used by source accounts against what exists in the
    target. Built-in platforms need no action. Custom platforms are exported
    as ZIP from source PVWA and imported to the target.
    """

    AGENT_ID = "agent_13_platform_plugins"
    AGENT_NAME = "Platform Plugin Validator"

    def preflight(self) -> AgentResult:
        """Validate source and target connectivity."""
        self.logger.log("preflight_start", {"agent": self.AGENT_ID})
        errors = []

        on_prem_cfg = self.config.get("cyberark_on_prem", {})
        cloud_cfg = self.config.get("keeperpam", {})

        if not on_prem_cfg.get("base_url"):
            errors.append("cyberark_on_prem.base_url not configured.")
        if not cloud_cfg.get("base_url"):
            errors.append("keeperpam.base_url not configured.")

        # Check discovery data exists
        discovery = self.state.get_agent_result("agent_01_discovery", "P1")
        if not discovery:
            errors.append("No discovery data. Run Agent 01 (P1) first.")

        if errors:
            return self._result("failed", errors=errors)

        self.logger.log("preflight_passed", {"agent": self.AGENT_ID})
        return self._result("success")

    def run(self, phase: str, input_data: dict) -> AgentResult:
        """Run platform validation."""
        if phase not in ("P2", "P4"):
            return self._result(
                "failed", phase=phase,
                errors=[f"Agent 13 runs in P2/P4, not {phase}"],
            )

        self.logger.log("platform_validation_start", {"phase": phase})
        on_prem_cfg = self.config["cyberark_on_prem"]
        cloud_cfg = self.config["keeperpam"]
        agent_cfg = self.config.get("agent_13_platform_plugins", {})
        auto_import = agent_cfg.get("auto_import_custom", True)

        # Get platforms used by accounts from discovery
        raw = self.state.get_raw_data("agent_01_discovery", "P1") or {}
        accounts = raw.get("raw_accounts", [])

        # Collect all platform IDs in use
        platforms_in_use: Dict[str, int] = {}
        for acct in accounts:
            pid = acct.get("platformId", "")
            if pid:
                platforms_in_use[pid] = platforms_in_use.get(pid, 0) + 1

        if not platforms_in_use:
            return self._result(
                "failed", phase=phase,
                errors=["No platform IDs found in account data."],
            )

        self.logger.log("platforms_in_use", {
            "total": len(platforms_in_use),
            "counts": platforms_in_use,
        })

        try:
            with CyberArkClient(on_prem_cfg) as source, \
                 CloudClient(cloud_cfg) as target:

                # Get source platforms
                source_platforms = source.get_platforms()
                source_platform_map = {
                    p.get("PlatformID", p.get("id", "")): p
                    for p in source_platforms
                }

                # Get target platforms
                target_platforms = target.get_platforms()
                target_platform_ids = {
                    p.get("PlatformID", p.get("platformId", ""))
                    for p in target_platforms
                }

                # Classify each platform
                matched = []
                builtin_ok = []
                missing_custom = []
                migrated = []
                still_missing = []

                for platform_id, account_count in platforms_in_use.items():
                    if platform_id in target_platform_ids:
                        matched.append({
                            "platform_id": platform_id,
                            "account_count": account_count,
                            "status": "matched",
                        })
                    elif platform_id in BUILTIN_PLATFORMS:
                        builtin_ok.append({
                            "platform_id": platform_id,
                            "account_count": account_count,
                            "status": "builtin_expected",
                        })
                    else:
                        missing_custom.append({
                            "platform_id": platform_id,
                            "account_count": account_count,
                            "source_data": source_platform_map.get(platform_id, {}),
                        })

                # Import missing custom platforms
                if missing_custom and auto_import:
                    for custom in missing_custom:
                        pid = custom["platform_id"]
                        result = self._import_platform(
                            source, target, pid, custom.get("source_data", {}),
                        )
                        if result["success"]:
                            migrated.append({
                                "platform_id": pid,
                                "account_count": custom["account_count"],
                                "status": "migrated",
                            })
                        else:
                            still_missing.append({
                                "platform_id": pid,
                                "account_count": custom["account_count"],
                                "status": "import_failed",
                                "error": result.get("error", ""),
                            })
                elif missing_custom:
                    still_missing = [{
                        "platform_id": c["platform_id"],
                        "account_count": c["account_count"],
                        "status": "missing_no_auto_import",
                    } for c in missing_custom]

        except (CyberArkError, CloudError) as e:
            self.logger.log_error("platform_validation_failed", {}, str(e))
            return self._result(
                "failed", phase=phase,
                errors=[f"Platform validation error: {e}"],
            )

        report = {
            "platforms_in_use": len(platforms_in_use),
            "matched_in_target": len(matched),
            "builtin_expected": len(builtin_ok),
            "custom_migrated": len(migrated),
            "still_missing": len(still_missing),
            "matched": matched,
            "builtin": builtin_ok,
            "migrated": migrated,
            "missing": still_missing,
        }

        self.state.store_agent_result(self.AGENT_ID, phase, report)
        self.state.complete_step(f"{phase}:platform_validation")

        self.logger.log("platform_validation_complete", {
            "matched": len(matched),
            "builtin": len(builtin_ok),
            "migrated": len(migrated),
            "missing": len(still_missing),
        })

        status = "success" if not still_missing else "partial"
        return self._result(
            status, phase=phase, data=report,
            metrics={
                "platforms_in_use": len(platforms_in_use),
                "matched": len(matched),
                "migrated": len(migrated),
                "missing": len(still_missing),
            },
            errors=[
                f"Platform '{m['platform_id']}' missing ({m['account_count']} accounts)"
                for m in still_missing
            ] if still_missing else [],
            next_action="All platforms available in target."
            if not still_missing
            else f"Resolve {len(still_missing)} missing platforms before P4.",
        )

    def _import_platform(
        self,
        source: CyberArkClient,
        target: CloudClient,
        platform_id: str,
        source_data: dict,
    ) -> dict:
        """Export platform ZIP from source and import to target.

        CyberArk PVWA exports platforms as ZIP packages containing the
        platform definition, connection component, and CPM policy.
        """
        try:
            # Export from source
            self.logger.log("platform_export", {"platform_id": platform_id})
            zip_data = source.export_platform(platform_id)

            if not zip_data:
                return {
                    "success": False,
                    "error": f"Export returned empty data for {platform_id}",
                }

            # Import to target
            self.logger.log("platform_import", {"platform_id": platform_id})
            result = target.import_platform(zip_data)

            self.logger.log("platform_import_success", {
                "platform_id": platform_id,
            })
            return {"success": True, "result": result}

        except (CyberArkError, CloudError) as e:
            self.logger.log_error("platform_import_failed", {
                "platform_id": platform_id,
            }, str(e))
            return {"success": False, "error": str(e)}

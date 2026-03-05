"""Agent 13 — Platform Plugin Validator (G-07 Gap Closure).

Validates that Secret Server secret templates required by source CyberArk
platforms exist in the target Secret Server instance. For missing templates,
creates them via the Secret Server API.

Secret Server uses templates (not CyberArk-style platform ZIPs), so migration
involves creating new templates with the correct fields.

Phases:
    P2: Infrastructure validation (compare source platforms vs target templates)
    P4: Pre-pilot re-validation (confirm no drift)
"""

import logging
from typing import Any, Dict, List, Set

from core.base import AgentBase, AgentResult
from core.cyberark_client import CyberArkClient, CyberArkError
from core.secret_server_client import SecretServerClient, SSError

logger = logging.getLogger(__name__)

# CyberArk platform → Secret Server template mapping
DEFAULT_TEMPLATE_MAP = {
    "WinServerLocal": "Windows Account",
    "WinDomain": "Active Directory Account",
    "WinDesktopLocal": "Windows Account",
    "WinServiceAccount": "Windows Service Account",
    "UnixSSH": "Unix Account (SSH)",
    "UnixSSHKeys": "Unix Account (SSH Key Rotation)",
    "Oracle": "Oracle Account",
    "MSSql": "SQL Server Account",
    "MySQL": "MySQL Account",
    "PostgreSQL": "PostgreSQL Account",
    "AWSAccessKeys": "Amazon IAM Key",
    "AzureServicePrincipal": "Azure Service Principal",
}

# Template field definitions for auto-creation
TEMPLATE_FIELDS = {
    "Windows Account": [
        {"name": "Username", "slug": "username", "fieldType": "Text", "isRequired": True},
        {"name": "Password", "slug": "password", "fieldType": "Password", "isRequired": True},
        {"name": "Machine", "slug": "machine", "fieldType": "Text", "isRequired": True},
        {"name": "Notes", "slug": "notes", "fieldType": "Notes", "isRequired": False},
    ],
    "Active Directory Account": [
        {"name": "Domain", "slug": "domain", "fieldType": "Text", "isRequired": True},
        {"name": "Username", "slug": "username", "fieldType": "Text", "isRequired": True},
        {"name": "Password", "slug": "password", "fieldType": "Password", "isRequired": True},
        {"name": "Notes", "slug": "notes", "fieldType": "Notes", "isRequired": False},
    ],
    "Unix Account (SSH)": [
        {"name": "Machine", "slug": "machine", "fieldType": "Text", "isRequired": True},
        {"name": "Username", "slug": "username", "fieldType": "Text", "isRequired": True},
        {"name": "Password", "slug": "password", "fieldType": "Password", "isRequired": True},
        {"name": "Notes", "slug": "notes", "fieldType": "Notes", "isRequired": False},
    ],
    "Unix Account (SSH Key Rotation)": [
        {"name": "Machine", "slug": "machine", "fieldType": "Text", "isRequired": True},
        {"name": "Username", "slug": "username", "fieldType": "Text", "isRequired": True},
        {"name": "Private Key", "slug": "private-key", "fieldType": "Password", "isRequired": True},
        {"name": "Private Key Passphrase", "slug": "private-key-passphrase", "fieldType": "Password", "isRequired": False},
        {"name": "Notes", "slug": "notes", "fieldType": "Notes", "isRequired": False},
    ],
}


class PlatformPluginAgent(AgentBase):
    """Validates and creates Secret Server templates for source platforms.

    Compares CyberArk platforms used by source accounts against templates
    available in the target Secret Server. Missing templates are auto-created
    via the API.
    """

    AGENT_ID = "agent_13_platform_plugins"
    AGENT_NAME = "Platform Plugin Validator"

    def preflight(self) -> AgentResult:
        """Validate source and target connectivity."""
        self.logger.log("preflight_start", {"agent": self.AGENT_ID})
        errors = []

        on_prem_cfg = self.config.get("cyberark_on_prem", {})
        ss_cfg = self.config.get("secret_server", {})

        if not on_prem_cfg.get("base_url"):
            errors.append("cyberark_on_prem.base_url not configured.")
        if not ss_cfg.get("base_url"):
            errors.append("secret_server.base_url not configured.")

        discovery = self.state.get_agent_result("agent_01_discovery", "P1")
        if not discovery:
            errors.append("No discovery data. Run Agent 01 (P1) first.")

        if errors:
            return self._result("failed", errors=errors)

        self.logger.log("preflight_passed", {"agent": self.AGENT_ID})
        return self._result("success")

    def run(self, phase: str, input_data: dict) -> AgentResult:
        """Run template validation."""
        if phase not in ("P2", "P4"):
            return self._result(
                "failed", phase=phase,
                errors=[f"Agent 13 runs in P2/P4, not {phase}"],
            )

        self.logger.log("template_validation_start", {"phase": phase})
        ss_cfg = self.config["secret_server"]
        agent_cfg = self.config.get("agent_13_platform_plugins", {})
        auto_create = agent_cfg.get("auto_create_templates", True)

        # Custom template map overrides
        template_map = dict(DEFAULT_TEMPLATE_MAP)
        template_map.update(agent_cfg.get("platform_template_map", {}))

        # Get platforms in use from discovery
        raw = self.state.get_raw_data("agent_01_discovery", "P1") or {}
        accounts = raw.get("raw_accounts", [])

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

        try:
            with SecretServerClient(ss_cfg) as target:
                # Get existing templates in target
                target_templates = target.get_templates()
                target_template_names = {
                    t.get("name", ""): t.get("id", 0) for t in target_templates
                }

                matched = []
                created = []
                unmapped = []
                still_missing = []

                for platform_id, count in platforms_in_use.items():
                    template_name = template_map.get(platform_id)

                    if not template_name:
                        unmapped.append({
                            "platform_id": platform_id,
                            "account_count": count,
                            "status": "no_template_mapping",
                        })
                        continue

                    if template_name in target_template_names:
                        matched.append({
                            "platform_id": platform_id,
                            "template_name": template_name,
                            "template_id": target_template_names[template_name],
                            "account_count": count,
                            "status": "matched",
                        })
                    elif auto_create:
                        result = self._create_template(target, template_name)
                        if result["success"]:
                            created.append({
                                "platform_id": platform_id,
                                "template_name": template_name,
                                "template_id": result.get("template_id"),
                                "account_count": count,
                                "status": "created",
                            })
                        else:
                            still_missing.append({
                                "platform_id": platform_id,
                                "template_name": template_name,
                                "account_count": count,
                                "status": "create_failed",
                                "error": result.get("error", ""),
                            })
                    else:
                        still_missing.append({
                            "platform_id": platform_id,
                            "template_name": template_name,
                            "account_count": count,
                            "status": "missing_no_auto_create",
                        })

        except SSError as e:
            self.logger.log_error("template_validation_failed", {}, str(e))
            return self._result(
                "failed", phase=phase,
                errors=[f"Template validation error: {e}"],
            )

        report = {
            "platforms_in_use": len(platforms_in_use),
            "matched": len(matched),
            "created": len(created),
            "unmapped": len(unmapped),
            "still_missing": len(still_missing),
            "details": {
                "matched": matched,
                "created": created,
                "unmapped": unmapped,
                "missing": still_missing,
            },
        }

        self.state.store_agent_result(self.AGENT_ID, phase, report)
        self.state.complete_step(f"{phase}:template_validation")

        self.logger.log("template_validation_complete", {
            "matched": len(matched),
            "created": len(created),
            "unmapped": len(unmapped),
            "missing": len(still_missing),
        })

        has_issues = still_missing or unmapped
        status = "success" if not has_issues else "partial"
        return self._result(
            status, phase=phase, data=report,
            metrics={
                "platforms_in_use": len(platforms_in_use),
                "matched": len(matched),
                "created": len(created),
                "unmapped": len(unmapped),
                "missing": len(still_missing),
            },
            errors=[
                f"Template '{m.get('template_name', m.get('platform_id'))}' "
                f"not available ({m['account_count']} accounts)"
                for m in (still_missing + unmapped)
            ] if has_issues else [],
            next_action="All templates ready."
            if not has_issues
            else f"Resolve {len(still_missing) + len(unmapped)} template gaps.",
        )

    def _create_template(
        self, target: SecretServerClient, template_name: str,
    ) -> dict:
        """Create a Secret Server template with standard fields."""
        fields = TEMPLATE_FIELDS.get(template_name)
        if not fields:
            # Create a generic template with basic fields
            fields = [
                {"name": "Username", "slug": "username", "fieldType": "Text", "isRequired": True},
                {"name": "Password", "slug": "password", "fieldType": "Password", "isRequired": True},
                {"name": "Machine", "slug": "machine", "fieldType": "Text", "isRequired": False},
                {"name": "Notes", "slug": "notes", "fieldType": "Notes", "isRequired": False},
            ]

        try:
            self.logger.log("template_create", {"name": template_name})
            result = target.create_template({
                "name": template_name,
                "fields": fields,
            })
            template_id = result.get("id", 0)
            return {"success": True, "template_id": template_id}

        except SSError as e:
            self.logger.log_error("template_create_failed", {
                "name": template_name,
            }, str(e))
            return {"success": False, "error": str(e)}

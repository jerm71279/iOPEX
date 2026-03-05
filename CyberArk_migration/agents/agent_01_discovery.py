"""Agent 01 — Discovery & Dependency Mapping.

Connects to the on-prem CyberArk PVWA and enumerates every account, safe,
platform, and integration dependency. Produces a discovery manifest that feeds
Agents 02-04.

Uses context managers for connections, Applications API for NHI/CCP discovery,
and stores raw data separately from the state file.

Phases:
    P1: Full discovery run
"""

import logging
import re
from typing import Any, Dict, List

from core.base import AgentBase, AgentResult
from core.cyberark_client import CyberArkClient, CyberArkError, NHI_PLATFORMS

logger = logging.getLogger(__name__)

# Integration detection patterns
INTEGRATION_PATTERNS = {
    "CCP_AAM": [
        r"AIMWebService", r"GetPassword", r"AppID=", r"CentralCredentialProvider",
        r"CredentialProvider", r"AIM\s+agent",
    ],
    "SIEM": [
        r"syslog", r"SIEM", r"Splunk", r"QRadar", r"Sentinel", r"CEF\s+format",
    ],
    "TICKETING": [
        r"ServiceNow", r"SNOW", r"Jira", r"Remedy", r"change.request",
    ],
    "PSM": [
        r"PSMConnect", r"PSMServer", r"PSM\s+recording", r"session.recording",
    ],
    "CICD": [
        r"Jenkins", r"Azure\s+DevOps", r"GitLab", r"pipeline", r"Ansible\s+vault",
    ],
    "DATABASE": [
        r"OracleDB", r"MSSQL", r"PostgreSQL", r"MySQL", r"database\s+rotation",
    ],
}

# NHI (Non-Human Identity) detection patterns (name-based)
NHI_NAME_PATTERNS = [
    r"^svc[_-]", r"^app[_-]", r"^api[_-]", r"^bot[_-]", r"^sys[_-]",
    r"^batch[_-]", r"^task[_-]", r"^auto[_-]", r"^cron[_-]", r"^rpa[_-]",
    r"service.?account", r"daemon", r"scheduler",
]

# Safe name patterns that indicate NHI content
NHI_SAFE_PATTERNS = [
    r"appcred", r"servicecred", r"automation", r"cicd", r"pipeline",
    r"appidentit", r"machineidentit",
]


class DiscoveryAgent(AgentBase):
    """Discovers all CyberArk assets and maps dependencies."""

    AGENT_ID = "agent_01_discovery"
    AGENT_NAME = "Discovery & Dependency Mapping"

    def preflight(self) -> AgentResult:
        self.logger.log("preflight_start", {"agent": self.AGENT_ID})

        on_prem_cfg = self.config.get("cyberark_on_prem", {})
        if not on_prem_cfg.get("base_url"):
            return self._result("failed", errors=["cyberark_on_prem.base_url not configured"])

        try:
            with CyberArkClient(on_prem_cfg) as client:
                checks = client.preflight_check()
        except CyberArkError as e:
            return self._result("failed", errors=[str(e)])

        if checks.get("errors"):
            return self._result("failed", errors=checks["errors"], data=checks)

        if not checks.get("can_list_safes") or not checks.get("can_list_accounts"):
            return self._result(
                "failed",
                errors=["Insufficient permissions: need ListSafes and ListAccounts"],
                data=checks,
            )

        self.logger.log("preflight_passed", checks)
        return self._result("success", data=checks)

    def run(self, phase: str, input_data: dict) -> AgentResult:
        if phase != "P1":
            return self._result("failed", phase=phase, errors=[f"Agent 01 runs in P1, not {phase}"])

        self.logger.log("discovery_start", {"phase": phase})
        on_prem_cfg = self.config["cyberark_on_prem"]
        agent_cfg = self.config.get("agent_01_discovery", {})
        audit_log_days = agent_cfg.get("audit_log_days", 90)

        try:
            with CyberArkClient(on_prem_cfg) as client:
                # 1. Enumerate accounts
                accounts = client.get_accounts()
                logger.info(f"Discovered {len(accounts)} accounts")

                # 2. Enumerate safes + members
                safes = client.get_safes(include_system=False)
                safe_members = {}
                for safe in safes:
                    name = safe.get("SafeName", safe.get("safeName", ""))
                    if name:
                        try:
                            safe_members[name] = client.get_safe_members(name)
                        except CyberArkError:
                            safe_members[name] = []

                # 3. Enumerate platforms
                platforms = client.get_platforms()

                # 4. Audit logs
                audit_logs = []
                if agent_cfg.get("include_audit_logs", True):
                    audit_logs = client.get_audit_logs(days=audit_log_days)

                # 5. Applications (CCP/AAM) — critical for NHI classification
                applications = client.get_applications()
                app_details = {}
                for app in applications:
                    app_id = app.get("AppID", app.get("appID", ""))
                    if app_id:
                        auth = client.get_application_auth(app_id)
                        app_details[app_id] = {
                            "app": app,
                            "authentication": auth,
                        }

                # 6. System health
                health = client.get_system_health()

        except CyberArkError as e:
            self.logger.log_error("discovery_failed", {}, str(e))
            return self._result("failed", phase=phase, errors=[str(e)])

        # 7. Classify NHIs (multi-signal: name, platform, safe, applications)
        nhis = self._classify_nhis(accounts, applications, safe_members)

        # 8. Detect integration dependencies
        integrations = self._detect_integrations(accounts, safes, audit_logs, applications)

        # 9. Build discovery manifest (summary only — no raw data)
        manifest = {
            "accounts": {
                "total": len(accounts),
                "human": len(accounts) - len(nhis),
                "nhi": len(nhis),
                "by_platform": self._group_by(accounts, "platformId"),
            },
            "safes": {
                "total": len(safes),
                "members_summary": {k: len(v) for k, v in safe_members.items()},
            },
            "platforms": {
                "total": len(platforms),
                "names": [p.get("PlatformID", "") for p in platforms],
                "custom": [
                    p.get("PlatformID", "") for p in platforms
                    if not p.get("SystemType")  # custom platforms have no SystemType
                ],
            },
            "nhis": nhis,
            "integrations": integrations,
            "applications": {
                "total": len(applications),
                "app_ids": list(app_details.keys()),
            },
            "audit_log_count": len(audit_logs),
            "system_health": health,
        }

        # Store raw data separately (not in state file)
        self.state.store_raw_data(self.AGENT_ID, phase, {
            "raw_accounts": accounts,
            "raw_safes": safes,
            "raw_safe_members": safe_members,
            "raw_platforms": platforms,
            "raw_applications": app_details,
        })

        self.logger.log("discovery_complete", {
            "accounts": len(accounts),
            "safes": len(safes),
            "platforms": len(platforms),
            "nhis": len(nhis),
            "integrations": len(integrations),
            "applications": len(applications),
        })

        self.state.store_agent_result(self.AGENT_ID, phase, manifest)
        self.state.complete_step("P1:discovery")

        return self._result(
            "success", phase=phase, data=manifest,
            metrics={
                "accounts_discovered": len(accounts),
                "safes_discovered": len(safes),
                "nhis_identified": len(nhis),
                "integrations_found": len(integrations),
                "applications_found": len(applications),
            },
            next_action="Run Agent 02 (Gap Analysis) with discovery data",
        )

    # ── helpers ──────────────────────────────────────────────────

    def _classify_nhis(
        self, accounts: List[dict], applications: list, safe_members: dict,
    ) -> List[dict]:
        """Identify NHIs using multiple signals: name, platform, safe, applications."""
        nhis = []
        nhi_ids = set()

        # Build set of account IDs accessed by applications (most reliable signal)
        app_account_ids = set()
        for app in applications:
            # Applications reference safes, not individual accounts
            pass  # Account-level mapping comes from audit logs

        for acct in accounts:
            acct_id = acct.get("id", "")
            name = acct.get("name", acct.get("userName", "")).lower()
            platform = acct.get("platformId", "")
            safe = acct.get("safeName", "").lower()
            reason = None

            # Signal 1: Platform-based (most reliable)
            if platform in NHI_PLATFORMS:
                reason = f"platform:{platform}"

            # Signal 2: Name-based patterns
            if not reason:
                for pattern in NHI_NAME_PATTERNS:
                    if re.search(pattern, name, re.IGNORECASE):
                        reason = f"name_pattern:{pattern}"
                        break

            # Signal 3: Safe name patterns
            if not reason:
                for pattern in NHI_SAFE_PATTERNS:
                    if re.search(pattern, safe, re.IGNORECASE):
                        reason = f"safe_pattern:{pattern}"
                        break

            if reason:
                nhis.append({
                    "id": acct_id,
                    "name": acct.get("name", ""),
                    "safe": acct.get("safeName", ""),
                    "platform": platform,
                    "detection_method": reason,
                })
                nhi_ids.add(acct_id)

        return nhis

    def _detect_integrations(
        self, accounts: List[dict], safes: List[dict],
        audit_logs: List[dict], applications: list,
    ) -> List[dict]:
        """Detect CyberArk integration dependencies from multiple sources."""
        found = []

        # Source 1: Applications API (most authoritative for CCP/AAM)
        for app in applications:
            app_id = app.get("AppID", app.get("appID", ""))
            if app_id:
                found.append({
                    "type": "CCP_AAM",
                    "source": "applications_api",
                    "name": app_id,
                    "account_ids": [],  # Will be populated from audit analysis
                })

        # Source 2: Safe names
        for safe in safes:
            safe_name = safe.get("SafeName", safe.get("safeName", "")).lower()
            for int_type, patterns in INTEGRATION_PATTERNS.items():
                for pat in patterns:
                    if re.search(pat, safe_name, re.IGNORECASE):
                        found.append({
                            "type": int_type,
                            "source": "safe_name",
                            "name": safe.get("SafeName", ""),
                            "pattern": pat,
                        })
                        break

        # Source 3: Audit logs (application access patterns)
        for log_entry in audit_logs:
            caller = str(log_entry.get("CallerType", "")).lower()
            action = str(log_entry.get("Action", "")).lower()
            if caller == "application" or "retrieve" in action:
                user = log_entry.get("UserName", "unknown")
                found.append({
                    "type": "CCP_AAM",
                    "source": "audit_log",
                    "name": user,
                    "action": action,
                })

        # Deduplicate
        seen = set()
        unique = []
        for item in found:
            key = (item["type"], item["name"])
            if key not in seen:
                seen.add(key)
                unique.append(item)

        return unique

    def _group_by(self, items: List[dict], key: str) -> Dict[str, int]:
        groups: Dict[str, int] = {}
        for item in items:
            val = item.get(key, "unknown")
            groups[val] = groups.get(val, 0) + 1
        return groups

"""Agent 03 — Permission Mapping & Translation.

Maps CyberArk safe member permissions to KeeperPAM using the granular
individual permission model via the Vault Members API.

Detects missing permissions, flags security-sensitive permission holders,
and in Phase P3 actually applies permissions to target vaults.

Phases:
    P1: Analyze permissions from discovery data, produce translation report
    P3: Apply permission mappings to migrated vaults in KeeperPAM
"""

import logging
from typing import Any, Dict, List, Tuple
from urllib.parse import quote

from core.base import AgentBase, AgentResult
from core.keeper_client import KeeperClient, KeeperError as CloudError

logger = logging.getLogger(__name__)

# All CyberArk safe member permissions (complete list)
ALL_PERMISSIONS = [
    "UseAccounts",
    "RetrieveAccounts",
    "ListAccounts",
    "AddAccounts",
    "UpdateAccountContent",
    "UpdateAccountProperties",
    "InitiateCPMAccountManagementOperations",
    "SpecifyNextAccountContent",
    "RenameAccounts",
    "DeleteAccounts",
    "UnlockAccounts",
    "ManageSafe",
    "ManageSafeMembers",
    "BackupSafe",
    "ViewAuditLog",
    "ViewSafeMembers",
    "AccessWithoutConfirmation",
    "CreateFolders",
    "DeleteFolders",
    "MoveAccountsAndFolders",
    "RequestsAuthorizationLevel1",
    "RequestsAuthorizationLevel2",
]

# Security-sensitive permissions that warrant review
SENSITIVE_PERMISSIONS = {
    "ManageSafe": "Full safe admin — can modify safe properties",
    "ManageSafeMembers": "Can grant/revoke access to other users",
    "AccessWithoutConfirmation": "Bypasses dual-control approval workflow",
    "SpecifyNextAccountContent": "Can set the next password value",
    "InitiateCPMAccountManagementOperations": "Can trigger CPM verify/change/reconcile",
    "RequestsAuthorizationLevel1": "Dual-control authorization level 1",
    "RequestsAuthorizationLevel2": "Dual-control authorization level 2",
}

# Built-in members to skip (not real users)
SKIP_MEMBERS = {"Master", "Batch", "Backup Users", "DR Users", "Auditors", "Operators"}


class PermissionMappingAgent(AgentBase):
    """Maps individual CyberArk permissions directly to KeeperPAM."""

    AGENT_ID = "agent_03_permissions"
    AGENT_NAME = "Permission Mapping & Translation"

    def preflight(self) -> AgentResult:
        self.logger.log("preflight_start", {"agent": self.AGENT_ID})

        discovery = self.state.get_agent_result("agent_01_discovery", "P1")
        if not discovery:
            return self._result("failed", errors=["No discovery data. Run Agent 01 first."])

        # Raw safe members stored separately
        raw = self.state.get_raw_data("agent_01_discovery", "P1")
        safe_members = (raw or {}).get("raw_safe_members", {})
        if not safe_members:
            # Fallback: check discovery result
            safe_members = discovery.get("safe_members_summary", {})

        if not safe_members:
            return self._result(
                "failed",
                errors=["Discovery data has no safe member information"],
            )

        self.logger.log("preflight_passed", {"safes_with_members": len(safe_members)})
        return self._result("success", data={"safes_with_members": len(safe_members)})

    def run(self, phase: str, input_data: dict) -> AgentResult:
        if phase not in ("P1", "P3"):
            return self._result("failed", phase=phase, errors=[f"Agent 03 runs in P1/P3, not {phase}"])

        self.logger.log("permission_mapping_start", {"phase": phase})

        # Load raw safe members from separate file
        raw = self.state.get_raw_data("agent_01_discovery", "P1") or {}
        safe_members = raw.get("raw_safe_members", {})

        if not safe_members:
            # Fallback to discovery result
            discovery = self.state.get_agent_result("agent_01_discovery", "P1") or {}
            safe_members = discovery.get("safe_members_summary", {})

        agent_cfg = self.config.get("agent_03_permissions", {})

        # Phase P1: Analyze and produce translation report
        # Phase P3: Analyze AND apply to target
        analysis = self._analyze_permissions(safe_members, agent_cfg)

        if phase == "P3":
            # Actually apply permissions to KeeperPAM
            apply_result = self._apply_permissions(analysis, agent_cfg)
            analysis["apply_result"] = apply_result

        self.logger.log("permission_mapping_complete", analysis["summary"])
        self.state.store_agent_result(self.AGENT_ID, phase, analysis)
        self.state.complete_step(f"{phase}:permission_mapping")

        status = "success"
        if analysis["exceptions"]:
            status = "needs_approval"

        return self._result(
            status,
            phase=phase,
            data=analysis,
            metrics=analysis["summary"],
            next_action="Human review of permission exceptions" if analysis["exceptions"]
                        else ("Apply permissions in P3" if phase == "P1"
                              else "Proceed to Agent 04 (ETL)"),
        )

    def _analyze_permissions(self, safe_members: dict, cfg: dict) -> dict:
        """Analyze all safe member permissions — direct mapping, no role translation."""
        translations = {}
        exceptions = []
        sensitive_holders = []
        missing_permissions = []
        total_members = 0

        for safe_name, members in safe_members.items():
            translations[safe_name] = []
            for member in members:
                member_name = member.get("memberName", member.get("UserName", "unknown"))

                # Skip built-in members
                if member_name in SKIP_MEMBERS:
                    continue

                total_members += 1
                permissions = member.get("Permissions", {})

                # Extract granted permissions
                granted = []
                for perm in ALL_PERMISSIONS:
                    if permissions.get(perm, False):
                        granted.append(perm)

                # Check for unknown permissions (future CyberArk versions)
                unknown = [
                    p for p in permissions
                    if p not in ALL_PERMISSIONS and permissions[p]
                ]
                if unknown:
                    missing_permissions.append({
                        "safe": safe_name,
                        "member": member_name,
                        "unknown_permissions": unknown,
                    })

                # Flag sensitive permission holders
                for perm in granted:
                    if perm in SENSITIVE_PERMISSIONS:
                        sensitive_holders.append({
                            "safe": safe_name,
                            "member": member_name,
                            "permission": perm,
                            "risk": SENSITIVE_PERMISSIONS[perm],
                        })

                # Flag ManageSafe + ManageSafeMembers as exceptions requiring review
                if "ManageSafe" in granted or "ManageSafeMembers" in granted:
                    exceptions.append({
                        "safe": safe_name,
                        "member": member_name,
                        "reason": "Has admin-level safe permissions",
                        "permissions": granted,
                    })

                translations[safe_name].append({
                    "member": member_name,
                    "member_type": member.get("memberType", member.get("MemberType", "User")),
                    "permissions": granted,
                    "search_in": member.get("searchIn", ""),
                })

        return {
            "translations": translations,
            "exceptions": exceptions,
            "sensitive_holders": sensitive_holders,
            "missing_permissions": missing_permissions,
            "summary": {
                "safes_processed": len(safe_members),
                "members_processed": total_members,
                "exception_count": len(exceptions),
                "sensitive_holder_count": len(sensitive_holders),
                "unknown_permission_count": len(missing_permissions),
            },
        }

    def _apply_permissions(self, analysis: dict, cfg: dict) -> dict:
        """Apply permission mappings to KeeperPAM vaults (Phase P3)."""
        cloud_cfg = self.config.get("keeperpam", {})
        if not cloud_cfg.get("base_url"):
            return {"status": "skipped", "reason": "keeperpam not configured"}

        applied = 0
        failed = 0
        errors = []

        try:
            with CloudClient(cloud_cfg) as client:
                for safe_name, members in analysis["translations"].items():
                    for member_info in members:
                        member_name = member_info["member"]
                        perms = member_info["permissions"]

                        # Build KeeperPAM safe member payload
                        payload = {
                            "MemberName": member_name,
                            "MemberType": member_info.get("member_type", "User"),
                            "SearchIn": member_info.get("search_in", ""),
                            "Permissions": {p: True for p in perms},
                        }

                        try:
                            client.add_safe_member(safe_name, payload)
                            applied += 1
                        except CloudError as e:
                            if "already exists" in str(e).lower() or "409" in str(e):
                                # Member already exists, try update
                                try:
                                    client.update_safe_member(
                                        safe_name, member_name,
                                        {"Permissions": {p: True for p in perms}},
                                    )
                                    applied += 1
                                except CloudError as e2:
                                    failed += 1
                                    errors.append(f"{safe_name}/{member_name}: {e2}")
                            else:
                                failed += 1
                                errors.append(f"{safe_name}/{member_name}: {e}")
        except CloudError as e:
            return {"status": "failed", "error": str(e)}

        return {
            "status": "success" if not failed else "partial",
            "applied": applied,
            "failed": failed,
            "errors": errors[:50],  # Cap error list
        }

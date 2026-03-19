"""Agent 03 — Permission Mapping & Translation (CyberArk → Secret Server).

Translates CyberArk's 22 individual safe member permissions to Secret Server's
4-tier role model (Owner, Edit, View, List). This is a LOSSY translation —
some CyberArk permissions have no Secret Server equivalent.

The agent produces a detailed loss report showing:
- Which role each member was assigned
- Which permissions were lost in translation
- Escalation risks (members who receive MORE access than they had)

Phases:
    P1: Analyze permissions, produce translation + loss report
    P3: Apply folder permissions to Secret Server
"""

import logging
from typing import Any, Dict, List, Tuple

from core.base import AgentBase, AgentResult
from core.secret_server_client import SecretServerClient, SSError

logger = logging.getLogger(__name__)

# All 22 CyberArk safe member permissions
ALL_CYBERARK_PERMISSIONS = [
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

# Secret Server 4-tier role model
SS_ROLES = ["Owner", "Edit", "View", "List"]

# Translation rules: CyberArk permissions → SS role (highest match wins)
# Order matters: Owner > Edit > View > List
ROLE_TRIGGERS = {
    "Owner": {
        "requires_all": ["ManageSafe", "ManageSafeMembers"],
        "description": "Full admin — manage folder and member access",
    },
    "Edit": {
        "requires_any": [
            "AddAccounts", "UpdateAccountContent", "UpdateAccountProperties",
            "DeleteAccounts", "RenameAccounts", "UnlockAccounts",
        ],
        "description": "Create/modify/delete secrets in the folder",
    },
    "View": {
        "requires_any": ["UseAccounts", "RetrieveAccounts"],
        "description": "View and retrieve secret values",
    },
    "List": {
        "requires_any": ["ListAccounts", "ViewSafeMembers", "ViewAuditLog"],
        "description": "See that secrets exist (no value access)",
    },
}

# Permissions that have NO Secret Server equivalent — always lost
LOST_PERMISSIONS = {
    "AccessWithoutConfirmation": "No SS equivalent — SS uses Workflow templates instead of dual-control bypass",
    "SpecifyNextAccountContent": "No SS equivalent — SS RPC sets passwords automatically",
    "BackupSafe": "No SS equivalent — folder backup is a server-level operation",
    "CreateFolders": "SS folder permissions are inherited, not per-member",
    "DeleteFolders": "SS folder permissions are inherited, not per-member",
    "MoveAccountsAndFolders": "SS move is a separate admin permission, not folder-level",
    "RequestsAuthorizationLevel1": "SS uses Workflow templates — different approval model",
    "RequestsAuthorizationLevel2": "SS uses Workflow templates — different approval model",
    "InitiateCPMAccountManagementOperations": "SS RPC is all-or-nothing per template, not per-member",
}

# Permissions that map cleanly to SS roles (not lost, just collapsed)
MAPPED_PERMISSIONS = {
    "ManageSafe": "Owner",
    "ManageSafeMembers": "Owner",
    "AddAccounts": "Edit",
    "UpdateAccountContent": "Edit",
    "UpdateAccountProperties": "Edit",
    "DeleteAccounts": "Edit",
    "RenameAccounts": "Edit",
    "UnlockAccounts": "Edit",
    "UseAccounts": "View",
    "RetrieveAccounts": "View",
    "ListAccounts": "List",
    "ViewSafeMembers": "List",
    "ViewAuditLog": "List",
}

# Built-in CyberArk members to skip
SKIP_MEMBERS = {"Master", "Batch", "Backup Users", "DR Users", "Auditors", "Operators"}


def translate_permissions(cyberark_perms: dict) -> dict:
    """Translate CyberArk permissions to an SS role + loss report.

    Args:
        cyberark_perms: Dict of {permission_name: True/False}

    Returns:
        {
            "role": "Edit",
            "lost_permissions": [{"perm": "...", "reason": "..."}],
            "escalation_risk": True/False,
            "escalation_details": "...",
            "original_count": 5,
        }
    """
    granted = [p for p in ALL_CYBERARK_PERMISSIONS if cyberark_perms.get(p, False)]

    if not granted:
        return {
            "role": None,
            "lost_permissions": [],
            "escalation_risk": False,
            "escalation_details": "",
            "original_count": 0,
        }

    # Determine highest matching role
    role = None
    granted_set = set(granted)

    # Check Owner first (requires BOTH ManageSafe AND ManageSafeMembers)
    owner_req = ROLE_TRIGGERS["Owner"]["requires_all"]
    if all(p in granted_set for p in owner_req):
        role = "Owner"

    # Check Edit
    if not role:
        edit_req = ROLE_TRIGGERS["Edit"]["requires_any"]
        if granted_set.intersection(edit_req):
            role = "Edit"

    # Check View
    if not role:
        view_req = ROLE_TRIGGERS["View"]["requires_any"]
        if granted_set.intersection(view_req):
            role = "View"

    # Check List
    if not role:
        list_req = ROLE_TRIGGERS["List"]["requires_any"]
        if granted_set.intersection(list_req):
            role = "List"

    # Identify lost permissions
    lost = []
    for perm in granted:
        if perm in LOST_PERMISSIONS:
            lost.append({
                "permission": perm,
                "reason": LOST_PERMISSIONS[perm],
            })

    # Detect escalation risk: member gets MORE access than they had
    escalation_risk = False
    escalation_details = ""

    if role == "Edit":
        # Did they only have View-level perms plus one Edit trigger?
        view_only = granted_set.intersection({"UseAccounts", "RetrieveAccounts"})
        edit_triggers = granted_set.intersection(set(ROLE_TRIGGERS["Edit"]["requires_any"]))
        if view_only and edit_triggers == {"UnlockAccounts"}:
            escalation_risk = True
            escalation_details = (
                "Member had only UseAccounts/RetrieveAccounts + UnlockAccounts. "
                "SS Edit role grants full create/modify/delete — over-provisioning risk."
            )

    if role == "Owner":
        # Owner in SS gets everything. Did they have restricted perms beyond ManageSafe?
        non_admin = granted_set - {"ManageSafe", "ManageSafeMembers"}
        if not non_admin:
            escalation_risk = True
            escalation_details = (
                "Member only had ManageSafe/ManageSafeMembers (admin, no data access). "
                "SS Owner role grants full secret access — escalation from admin-only to full access."
            )

    return {
        "role": role,
        "lost_permissions": lost,
        "escalation_risk": escalation_risk,
        "escalation_details": escalation_details,
        "original_count": len(granted),
    }


class PermissionMappingAgent(AgentBase):
    """Translates CyberArk 22-permission model to SS 4-role model (lossy)."""

    AGENT_ID = "agent_03_permissions"
    AGENT_NAME = "Permission Mapping & Translation"

    def preflight(self) -> AgentResult:
        self.logger.log("preflight_start", {"agent": self.AGENT_ID})

        discovery = self.state.get_agent_result("agent_01_discovery", "P1")
        if not discovery:
            return self._result("failed", errors=["No discovery data. Run Agent 01 first."])

        raw = self.state.get_raw_data("agent_01_discovery", "P1")
        safe_members = (raw or {}).get("raw_safe_members", {})
        if not safe_members:
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

        raw = self.state.get_raw_data("agent_01_discovery", "P1") or {}
        safe_members = raw.get("raw_safe_members", {})
        if not safe_members:
            discovery = self.state.get_agent_result("agent_01_discovery", "P1") or {}
            safe_members = discovery.get("safe_members_summary", {})

        agent_cfg = self.config.get("agent_03_permissions", {})

        # Analyze: translate all permissions (22 → 4 roles + loss tracking)
        analysis = self._analyze_permissions(safe_members, agent_cfg)

        if phase == "P3":
            apply_result = self._apply_permissions(analysis, agent_cfg)
            analysis["apply_result"] = apply_result

        self.logger.log("permission_mapping_complete", analysis["summary"])
        self.state.store_agent_result(self.AGENT_ID, phase, analysis)
        self.state.complete_step(f"{phase}:permission_mapping")

        status = "success"
        if analysis["escalation_risks"] or analysis["lost_permission_count"] > 0:
            status = "needs_approval"

        return self._result(
            status,
            phase=phase,
            data=analysis,
            metrics=analysis["summary"],
            next_action="Human review of permission loss + escalation report"
                        if status == "needs_approval"
                        else ("Apply folder permissions in P3" if phase == "P1"
                              else "Proceed to Agent 04 (ETL)"),
        )

    def _analyze_permissions(self, safe_members: dict, cfg: dict) -> dict:
        """Translate all safe member permissions to SS roles with loss tracking."""
        translations = {}
        escalation_risks = []
        all_lost = []
        role_distribution = {"Owner": 0, "Edit": 0, "View": 0, "List": 0, "None": 0}
        total_members = 0

        skip_members = set(cfg.get("skip_members", SKIP_MEMBERS))

        for safe_name, members in safe_members.items():
            translations[safe_name] = []
            for member in members:
                member_name = member.get("memberName", member.get("UserName", "unknown"))

                if member_name in skip_members:
                    continue

                total_members += 1
                permissions = member.get("Permissions", {})

                # Translate
                result = translate_permissions(permissions)

                role = result["role"]
                role_distribution[role or "None"] += 1

                # Track escalation risks
                if result["escalation_risk"]:
                    escalation_risks.append({
                        "safe": safe_name,
                        "member": member_name,
                        "assigned_role": role,
                        "details": result["escalation_details"],
                        "original_count": result["original_count"],
                    })

                # Track lost permissions
                for lost in result["lost_permissions"]:
                    all_lost.append({
                        "safe": safe_name,
                        "member": member_name,
                        "permission": lost["permission"],
                        "reason": lost["reason"],
                    })

                translations[safe_name].append({
                    "member": member_name,
                    "member_type": member.get("memberType", member.get("MemberType", "User")),
                    "ss_role": role,
                    "lost_permissions": result["lost_permissions"],
                    "escalation_risk": result["escalation_risk"],
                    "original_permissions": [
                        p for p in ALL_CYBERARK_PERMISSIONS if permissions.get(p, False)
                    ],
                    "search_in": member.get("searchIn", ""),
                })

        return {
            "translations": translations,
            "escalation_risks": escalation_risks,
            "lost_permissions": all_lost,
            "lost_permission_count": len(all_lost),
            "role_distribution": role_distribution,
            "summary": {
                "safes_processed": len(safe_members),
                "members_processed": total_members,
                "escalation_risk_count": len(escalation_risks),
                "lost_permission_count": len(all_lost),
                "role_distribution": role_distribution,
            },
        }

    def _apply_permissions(self, analysis: dict, cfg: dict) -> dict:
        """Apply translated folder permissions to Secret Server (Phase P3)."""
        ss_cfg = self.config.get("secret_server", {})
        if not ss_cfg.get("base_url"):
            return {"status": "skipped", "reason": "secret_server not configured"}

        applied = 0
        failed = 0
        skipped = 0
        errors = []

        # Build folder name → ID mapping from state
        etl_result = self.state.get_agent_result("agent_04_etl", "P4") or {}
        folder_map = etl_result.get("folder_map", {})

        try:
            with SecretServerClient(ss_cfg) as client:
                # If no folder map yet, build from SS
                if not folder_map:
                    folders = client.get_folders()
                    folder_map = {f.get("folderName", ""): f.get("id", 0) for f in folders}

                for safe_name, members in analysis["translations"].items():
                    folder_id = folder_map.get(safe_name)
                    if not folder_id:
                        skipped += 1
                        continue

                    for member_info in members:
                        role = member_info.get("ss_role")
                        if not role:
                            skipped += 1
                            continue

                        member_name = member_info["member"]
                        payload = {
                            "folderAccessRoleName": role,
                            "secretAccessRoleName": role,
                        }
                        # Determine if user or group
                        member_type = member_info.get("member_type", "User")
                        if member_type.lower() in ("group", "role"):
                            payload["groupName"] = member_name
                        else:
                            payload["userName"] = member_name

                        try:
                            client.set_folder_permission(folder_id, payload)
                            applied += 1
                        except SSError as e:
                            if "already exists" in str(e).lower() or "409" in str(e):
                                skipped += 1  # Permission already set
                            else:
                                failed += 1
                                errors.append(f"{safe_name}/{member_name}: {e}")

        except SSError as e:
            return {"status": "failed", "error": str(e)}

        return {
            "status": "success" if not failed else "partial",
            "applied": applied,
            "failed": failed,
            "skipped": skipped,
            "errors": errors[:50],
        }

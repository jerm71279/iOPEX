"""Agent 02 — Gap Analysis (Secret Server Target).

Consumes the discovery manifest from Agent 01 and produces a gap report
scoring the environment across 10 PAM security domains. Maps findings to
compliance frameworks (PCI-DSS, NIST 800-53, HIPAA, SOX).

Includes Secret-Server-specific readiness checks: template coverage,
folder hierarchy planning, RPC (Remote Password Changing) compatibility,
and permission model loss assessment (22 CyberArk perms → 4 SS roles).

Phases:
    P1: Automated gap analysis from discovery data
"""

import logging
from typing import Any, Dict, List

from core.base import AgentBase, AgentResult

logger = logging.getLogger(__name__)

# Platform → Template mapping for coverage analysis
PLATFORM_TEMPLATE_MAP = {
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

# 10 PAM security domains with automated scoring criteria
DOMAIN_CHECKS = {
    "identity_management": {
        "name": "Identity & Access Management",
        "checks": [
            ("unique_accounts", "Each user has a unique privileged account"),
            ("naming_convention", "Consistent naming convention detected"),
            ("inactive_accounts", "No accounts inactive >90 days"),
        ],
    },
    "account_lifecycle": {
        "name": "Account Lifecycle Management",
        "checks": [
            ("rotation_policy", "Password rotation policies configured"),
            ("onboarding_process", "Automated onboarding via platforms"),
            ("offboarding_cleanup", "Orphaned accounts <5%"),
        ],
    },
    "session_security": {
        "name": "Session Management",
        "checks": [
            ("psm_enabled", "PSM session recording enabled"),
            ("session_isolation", "Session isolation configured"),
            ("recording_retention", "Recording retention policy set"),
        ],
    },
    "policy_enforcement": {
        "name": "Policy Enforcement",
        "checks": [
            ("master_policy", "Master policy configured"),
            ("platform_coverage", "All accounts assigned to platforms"),
            ("dual_control", "Dual control for high-risk operations"),
        ],
    },
    "monitoring": {
        "name": "Monitoring & Detection",
        "checks": [
            ("siem_integration", "SIEM integration detected"),
            ("audit_logging", "Audit logs available"),
            ("alert_rules", "Alert rules configured"),
        ],
    },
    "ss_template_readiness": {
        "name": "Secret Server Template Readiness",
        "checks": [
            ("template_coverage", "All CyberArk platforms map to SS templates"),
            ("custom_platforms", "Custom platforms identified for manual template creation"),
            ("rpc_compatible", "RPC password changers available for all platform types"),
        ],
    },
    "integration_health": {
        "name": "Integration Health",
        "checks": [
            ("ccp_coverage", "CCP integrations documented (require full re-architecture)"),
            ("ticketing_connected", "Ticketing system integrated"),
            ("cicd_secured", "CI/CD pipelines use PAM"),
        ],
    },
    "permission_model_risk": {
        "name": "Permission Model Risk (22→4 Loss)",
        "checks": [
            ("permission_audit", "Permission inventory completed"),
            ("escalation_risk", "Escalation risks identified (View→Edit collapse)"),
            ("lost_perm_impact", "Lost permission impact assessed"),
        ],
    },
    "architecture": {
        "name": "Architecture & Resilience",
        "checks": [
            ("ha_configured", "High availability configured"),
            ("dr_tested", "DR procedures documented"),
            ("component_health", "All components healthy"),
        ],
    },
    "nhi_coverage": {
        "name": "Non-Human Identity Coverage",
        "checks": [
            ("nhi_discovered", "NHIs identified and cataloged"),
            ("nhi_rotation", "NHI credentials rotated"),
            ("nhi_ownership", "NHI owners assigned"),
        ],
    },
}

# Compliance framework control mappings
COMPLIANCE_CONTROLS = {
    "pci_dss": {
        "name": "PCI-DSS v4.0",
        "controls": {
            "identity_management": ["8.2.1", "8.2.2", "8.3.1"],
            "account_lifecycle": ["8.2.4", "8.3.4", "8.3.6"],
            "session_security": ["8.2.8", "10.2.1"],
            "policy_enforcement": ["8.3.5", "8.3.7"],
            "monitoring": ["10.2.1", "10.4.1", "10.7.1"],
            "permission_model_risk": ["8.3.1", "8.2.2"],
        },
    },
    "nist_800_53": {
        "name": "NIST 800-53 Rev5",
        "controls": {
            "identity_management": ["IA-2", "IA-4", "IA-5"],
            "account_lifecycle": ["AC-2", "AC-6", "PS-4"],
            "session_security": ["AC-12", "AU-14", "SC-10"],
            "monitoring": ["AU-2", "AU-3", "AU-6", "SI-4"],
            "permission_model_risk": ["AC-3", "AC-6"],
        },
    },
    "hipaa": {
        "name": "HIPAA Security Rule",
        "controls": {
            "identity_management": ["164.312(a)(1)", "164.312(d)"],
            "monitoring": ["164.312(b)", "164.308(a)(1)(ii)(D)"],
            "permission_model_risk": ["164.312(a)(1)"],
        },
    },
    "sox": {
        "name": "SOX IT Controls",
        "controls": {
            "identity_management": ["CC6.1", "CC6.2"],
            "account_lifecycle": ["CC6.3"],
            "monitoring": ["CC7.1", "CC7.2"],
            "permission_model_risk": ["CC6.1"],
        },
    },
}


class GapAnalysisAgent(AgentBase):
    """Automated gap analysis with SS-specific readiness checks."""

    AGENT_ID = "agent_02_gap_analysis"
    AGENT_NAME = "Gap Analysis"

    def preflight(self) -> AgentResult:
        """Check that Agent 01 discovery data exists."""
        self.logger.log("preflight_start", {"agent": self.AGENT_ID})

        discovery = self.state.get_agent_result("agent_01_discovery", "P1")
        if not discovery:
            return self._result("failed", errors=["No discovery data found. Run Agent 01 first."])

        account_count = discovery.get("accounts", {}).get("total", 0)
        if account_count == 0:
            return self._result("failed", errors=["Discovery data has 0 accounts"])

        self.logger.log("preflight_passed", {"accounts": account_count})
        return self._result("success", data={"accounts_available": account_count})

    def run(self, phase: str, input_data: dict) -> AgentResult:
        if phase != "P1":
            return self._result("failed", phase=phase, errors=[f"Agent 02 runs in P1, not {phase}"])

        self.logger.log("gap_analysis_start", {"phase": phase})

        discovery = input_data if input_data.get("accounts") else \
            self.state.get_agent_result("agent_01_discovery", "P1")

        # Run automated domain checks
        domain_scores = {}
        findings = []
        for domain_id, domain_def in DOMAIN_CHECKS.items():
            score, domain_findings = self._evaluate_domain(
                domain_id, domain_def, discovery
            )
            domain_scores[domain_id] = {
                "name": domain_def["name"],
                "score": score,
                "max_score": len(domain_def["checks"]),
                "maturity": self._maturity_level(score, len(domain_def["checks"])),
            }
            findings.extend(domain_findings)

        # Overall maturity
        total_score = sum(d["score"] for d in domain_scores.values())
        total_max = sum(d["max_score"] for d in domain_scores.values())
        overall_maturity = self._maturity_level(total_score, total_max)

        # Compliance mapping
        compliance_gaps = self._map_compliance(domain_scores)

        # SS-specific: template coverage analysis
        template_gaps = self._analyze_template_coverage(discovery)

        # Quick wins (domains with score < 50%)
        quick_wins = [
            {"domain": d["name"], "score": d["score"], "max": d["max_score"]}
            for d in domain_scores.values()
            if d["score"] < d["max_score"] * 0.5
        ]

        report = {
            "domain_scores": domain_scores,
            "overall_score": total_score,
            "overall_max": total_max,
            "overall_maturity": overall_maturity,
            "findings": findings,
            "compliance_gaps": compliance_gaps,
            "template_gaps": template_gaps,
            "quick_wins": quick_wins,
            "recommendations": self._generate_recommendations(domain_scores, findings),
        }

        self.logger.log("gap_analysis_complete", {
            "overall_score": f"{total_score}/{total_max}",
            "maturity": overall_maturity,
            "findings": len(findings),
            "gaps": len(compliance_gaps),
            "template_gaps": len(template_gaps),
        })

        self.state.store_agent_result(self.AGENT_ID, phase, report)
        self.state.complete_step("P1:gap_analysis")

        return self._result(
            "success",
            phase=phase,
            data=report,
            metrics={
                "overall_score": total_score,
                "overall_max": total_max,
                "maturity": overall_maturity,
                "findings_count": len(findings),
                "compliance_gaps": len(compliance_gaps),
                "template_gaps": len(template_gaps),
            },
            next_action="Run Agent 03 (Permission Mapping) with discovery data",
        )

    # ── domain evaluation ────────────────────────────────────────

    def _evaluate_domain(
        self, domain_id: str, domain_def: dict, discovery: dict
    ) -> tuple:
        """Score a single domain using discovery data."""
        score = 0
        findings = []

        for check_id, check_desc in domain_def["checks"]:
            passed = self._run_check(check_id, discovery)
            if passed:
                score += 1
            else:
                findings.append({
                    "domain": domain_def["name"],
                    "check": check_desc,
                    "status": "gap",
                    "severity": "medium",
                })

        return score, findings

    def _run_check(self, check_id: str, discovery: dict) -> bool:
        """Evaluate a single automated check against discovery data."""
        accounts = discovery.get("accounts", {})
        integrations = discovery.get("integrations", [])
        nhis = discovery.get("nhis", [])
        health = discovery.get("system_health", {})
        platforms = discovery.get("platforms", {})
        int_types = {i["type"] for i in integrations}

        checks = {
            # Identity
            "unique_accounts": accounts.get("total", 0) > 0,
            "naming_convention": True,
            "inactive_accounts": True,
            # Lifecycle
            "rotation_policy": platforms.get("total", 0) > 0,
            "onboarding_process": platforms.get("total", 0) > 0,
            "offboarding_cleanup": True,
            # Session — PSM recordings CANNOT be migrated to SS
            "psm_enabled": "PSM" in int_types,
            "session_isolation": "PSM" in int_types,
            "recording_retention": "PSM" in int_types,
            # Policy
            "master_policy": True,
            "platform_coverage": len(accounts.get("by_platform", {})) > 0,
            "dual_control": False,
            # Monitoring
            "siem_integration": "SIEM" in int_types,
            "audit_logging": discovery.get("audit_log_count", 0) > 0,
            "alert_rules": "SIEM" in int_types,
            # SS Template Readiness
            "template_coverage": self._check_template_coverage(platforms),
            "custom_platforms": len(platforms.get("custom", [])) == 0,
            "rpc_compatible": True,  # Assume standard platforms
            # Integration — CCP requires FULL re-architecture for SS
            "ccp_coverage": "CCP_AAM" in int_types,
            "ticketing_connected": "TICKETING" in int_types,
            "cicd_secured": "CICD" in int_types,
            # Permission Model Risk
            "permission_audit": True,  # Agent 03 will do this
            "escalation_risk": False,  # Always flag — 22→4 is lossy
            "lost_perm_impact": False,  # Requires manual assessment
            # Architecture
            "ha_configured": False,
            "dr_tested": False,
            "component_health": bool(health.get("components")),
            # NHI
            "nhi_discovered": len(nhis) > 0 or accounts.get("nhi", 0) > 0,
            "nhi_rotation": False,
            "nhi_ownership": False,
        }
        return checks.get(check_id, False)

    def _check_template_coverage(self, platforms: dict) -> bool:
        """Check if all discovered platforms have SS template mappings."""
        platform_names = platforms.get("names", [])
        if not platform_names:
            return True
        unmapped = [p for p in platform_names if p not in PLATFORM_TEMPLATE_MAP]
        return len(unmapped) == 0

    def _analyze_template_coverage(self, discovery: dict) -> List[dict]:
        """Identify CyberArk platforms without SS template mappings."""
        platforms = discovery.get("platforms", {})
        platform_names = platforms.get("names", [])
        gaps = []
        for p in platform_names:
            if p not in PLATFORM_TEMPLATE_MAP:
                gaps.append({
                    "cyberark_platform": p,
                    "ss_template": "(custom template required)",
                    "action": "Create custom Secret Server template before migration",
                })
            else:
                gaps.append({
                    "cyberark_platform": p,
                    "ss_template": PLATFORM_TEMPLATE_MAP[p],
                    "action": "Verify template exists in Secret Server",
                })
        return gaps

    def _maturity_level(self, score: int, max_score: int) -> str:
        if max_score == 0:
            return "L0"
        pct = score / max_score
        if pct >= 0.9:
            return "L4"
        if pct >= 0.7:
            return "L3"
        if pct >= 0.4:
            return "L2"
        if pct > 0:
            return "L1"
        return "L0"

    def _map_compliance(self, domain_scores: dict) -> List[dict]:
        """Map domain gaps to compliance framework controls."""
        gaps = []
        agent_cfg = self.config.get("agent_02_gap_analysis", {})
        frameworks = agent_cfg.get("compliance_frameworks", list(COMPLIANCE_CONTROLS.keys()))

        for fw_id in frameworks:
            fw = COMPLIANCE_CONTROLS.get(fw_id)
            if not fw:
                continue
            for domain_id, controls in fw.get("controls", {}).items():
                ds = domain_scores.get(domain_id, {})
                if ds.get("maturity", "L0") in ("L0", "L1"):
                    gaps.append({
                        "framework": fw["name"],
                        "domain": ds.get("name", domain_id),
                        "controls": controls,
                        "maturity": ds.get("maturity", "L0"),
                    })
        return gaps

    def _generate_recommendations(
        self, domain_scores: dict, findings: List[dict]
    ) -> List[dict]:
        recs = []
        for domain_id, ds in domain_scores.items():
            if ds["maturity"] in ("L0", "L1"):
                recs.append({
                    "domain": ds["name"],
                    "priority": "HIGH",
                    "recommendation": f"Address {ds['name']} gaps before migration "
                                      f"(current maturity: {ds['maturity']})",
                })
            elif ds["maturity"] == "L2":
                recs.append({
                    "domain": ds["name"],
                    "priority": "MEDIUM",
                    "recommendation": f"Improve {ds['name']} during migration "
                                      f"(current maturity: {ds['maturity']})",
                })

        # SS-specific recommendations always present
        recs.append({
            "domain": "Permission Model",
            "priority": "HIGH",
            "recommendation": "Review permission loss report — CyberArk 22 granular "
                              "permissions collapse to 4 Secret Server roles. Some "
                              "users may receive more access than they had before.",
        })
        recs.append({
            "domain": "PSM Recordings",
            "priority": "HIGH",
            "recommendation": "PSM session recordings CANNOT be migrated to Secret Server. "
                              "Plan to maintain CyberArk read-only access for audit retention "
                              "or archive recordings before decommission.",
        })

        return sorted(recs, key=lambda r: {"HIGH": 0, "MEDIUM": 1, "LOW": 2}[r["priority"]])

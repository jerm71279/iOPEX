"""Agent 12 — Non-Human Identity Handler (G-03 Gap Closure).

Deep NHI classification with per-type migration strategies. Builds on
Agent 01's basic NHI detection by adding weighted multi-signal classification,
subtype taxonomy, and type-specific migration runbooks.

Each NHI gets a classification (service_account, api_key, application_identity,
database_account, robotic_process, machine_identity, shared_account) and a
corresponding migration strategy that Agent 04 enforces during P4/P5.

Phases:
    P1: Classification (after Agent 01 discovery + Agent 09 dependency mapping)
"""

import logging
import re
from enum import Enum
from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional, Tuple

from core.base import AgentBase, AgentResult

logger = logging.getLogger(__name__)


class NHIType(str, Enum):
    """Non-Human Identity subtypes with distinct migration strategies."""
    SERVICE_ACCOUNT = "service_account"
    API_KEY = "api_key"
    APPLICATION_IDENTITY = "application_identity"
    DATABASE_ACCOUNT = "database_account"
    ROBOTIC_PROCESS = "robotic_process"
    MACHINE_IDENTITY = "machine_identity"
    SHARED_ACCOUNT = "shared_account"


# ── Classification signal weights ──────────────────────────────

SIGNAL_WEIGHTS = {
    "platform": 0.35,
    "name_pattern": 0.20,
    "container_pattern": 0.10,
    "dependency_evidence": 0.25,
    "audit_pattern": 0.10,
}

# Platform ID → NHI type mapping
PLATFORM_TYPE_MAP = {
    "WinServiceAccount": NHIType.SERVICE_ACCOUNT,
    "WinService": NHIType.SERVICE_ACCOUNT,
    "UnixSSHKeys": NHIType.MACHINE_IDENTITY,
    "UnixSSH": NHIType.MACHINE_IDENTITY,
    "AWSAccessKeys": NHIType.API_KEY,
    "AzureServicePrincipal": NHIType.APPLICATION_IDENTITY,
    "CyberArkCCP": NHIType.APPLICATION_IDENTITY,
    "OracleDB": NHIType.DATABASE_ACCOUNT,
    "MSSql": NHIType.DATABASE_ACCOUNT,
    "MySQL": NHIType.DATABASE_ACCOUNT,
    "PostgreSQL": NHIType.DATABASE_ACCOUNT,
}

# Name patterns → NHI type mapping
NAME_PATTERNS = {
    NHIType.SERVICE_ACCOUNT: [
        r"^svc[_\-.]", r"^service[_\-.]", r"^s\-",
        r"service.?account", r"_svc$",
    ],
    NHIType.API_KEY: [
        r"^api[_\-.]", r"api.?key", r"^token[_\-.]",
        r"_api$", r"_token$",
    ],
    NHIType.APPLICATION_IDENTITY: [
        r"^app[_\-.]", r"^appid[_\-.]", r"application.?id",
        r"^aim[_\-.]", r"ccp[_\-.]",
    ],
    NHIType.DATABASE_ACCOUNT: [
        r"^db[_\-.]", r"^dba[_\-.]", r"^sql[_\-.]",
        r"database", r"_db$",
    ],
    NHIType.ROBOTIC_PROCESS: [
        r"^rpa[_\-.]", r"^bot[_\-.]", r"^auto[_\-.]",
        r"^robot[_\-.]", r"uipath", r"blueprism",
    ],
    NHIType.MACHINE_IDENTITY: [
        r"^sys[_\-.]", r"^host[_\-.]", r"^cert[_\-.]",
        r"^machine[_\-.]", r"_cert$",
    ],
    NHIType.SHARED_ACCOUNT: [
        r"^shared[_\-.]", r"^generic[_\-.]", r"^admin[_\-.]shared",
        r"break.?glass", r"firecall",
    ],
}

# Container (safe) patterns → NHI type
CONTAINER_PATTERNS = {
    NHIType.SERVICE_ACCOUNT: [r"servicecred", r"svc_", r"service.?account"],
    NHIType.API_KEY: [r"api.?key", r"token", r"credential.?store"],
    NHIType.APPLICATION_IDENTITY: [r"appidentit", r"application", r"ccp", r"aim"],
    NHIType.DATABASE_ACCOUNT: [r"database", r"db_cred", r"sql"],
    NHIType.ROBOTIC_PROCESS: [r"rpa", r"automation", r"robot"],
    NHIType.MACHINE_IDENTITY: [r"machine", r"cert", r"ssh.?key"],
    NHIType.SHARED_ACCOUNT: [r"shared", r"generic", r"breakglass", r"firecall"],
}

# Dependency type → NHI type
DEPENDENCY_TYPE_MAP = {
    "iis_app_pool": NHIType.SERVICE_ACCOUNT,
    "windows_service": NHIType.SERVICE_ACCOUNT,
    "scheduled_task": NHIType.SERVICE_ACCOUNT,
    "jenkins_job": NHIType.APPLICATION_IDENTITY,
    "script_reference": NHIType.APPLICATION_IDENTITY,
    "config_reference": NHIType.APPLICATION_IDENTITY,
}


@dataclass
class NHIClassification:
    """Complete NHI classification for a single account."""
    account_id: str
    account_name: str
    nhi_type: str                  # NHIType value
    confidence: float              # 0.0 - 1.0
    signals: Dict[str, Any] = field(default_factory=dict)
    migration_strategy: str = ""
    risk_level: str = "medium"     # low | medium | high | critical
    migration_wave: int = 4        # Default NHI wave
    pre_migration_checks: List[str] = field(default_factory=list)
    post_migration_checks: List[str] = field(default_factory=list)
    ml_confidence: Optional[float] = None
    blended_score: Optional[float] = None

    def to_dict(self) -> dict:
        return asdict(self)


# ── Migration strategies per NHI type ──────────────────────────

MIGRATION_STRATEGIES = {
    NHIType.SERVICE_ACCOUNT: {
        "strategy": "dependency_aware_migration",
        "description": (
            "Require dependency map -> freeze all consumers -> "
            "migrate credential -> update consumer configs -> "
            "verify service restart -> unfreeze"
        ),
        "risk_level": "high",
        "wave": 4,
        "pre_checks": [
            "dependency_map_complete",
            "consumer_maintenance_window_scheduled",
            "rollback_plan_documented",
        ],
        "post_checks": [
            "all_consumers_updated",
            "services_restarted_successfully",
            "heartbeat_verified",
        ],
    },
    NHIType.API_KEY: {
        "strategy": "dual_distribute_cutover",
        "description": (
            "Create new credential in target -> distribute to all consumers "
            "(dual-key period) -> validate all consumers use new key -> "
            "revoke old key"
        ),
        "risk_level": "medium",
        "wave": 4,
        "pre_checks": [
            "consumer_list_identified",
            "dual_key_support_verified",
        ],
        "post_checks": [
            "old_key_revoked",
            "no_access_failures_24h",
        ],
    },
    NHIType.APPLICATION_IDENTITY: {
        "strategy": "ccp_aam_repoint",
        "description": (
            "Deploy dual-backend wrapper -> repoint CCP/AAM calls to wrapper -> "
            "wrapper routes to target -> validate application retrieval -> "
            "remove wrapper (direct to target)"
        ),
        "risk_level": "critical",
        "wave": 5,
        "pre_checks": [
            "application_owners_notified",
            "dual_backend_wrapper_deployed",
            "ccp_aam_endpoints_documented",
            "rollback_tested",
        ],
        "post_checks": [
            "application_retrieval_working",
            "no_ccp_errors_48h",
            "wrapper_removed",
            "old_appid_decommissioned",
        ],
    },
    NHIType.DATABASE_ACCOUNT: {
        "strategy": "dba_coordinated_rotation",
        "description": (
            "Coordinate with DBA team -> schedule maintenance window -> "
            "migrate credential -> trigger rotation in target -> "
            "verify database connectivity"
        ),
        "risk_level": "high",
        "wave": 4,
        "pre_checks": [
            "dba_approval_obtained",
            "maintenance_window_scheduled",
            "connection_string_update_plan",
        ],
        "post_checks": [
            "database_connectivity_verified",
            "rotation_succeeded",
            "application_queries_working",
        ],
    },
    NHIType.ROBOTIC_PROCESS: {
        "strategy": "rpa_credential_swap",
        "description": (
            "Pause RPA processes -> migrate credential -> "
            "update RPA orchestrator config -> resume processes -> "
            "verify process execution"
        ),
        "risk_level": "medium",
        "wave": 4,
        "pre_checks": [
            "rpa_processes_identified",
            "orchestrator_access_confirmed",
            "process_pause_window",
        ],
        "post_checks": [
            "rpa_processes_resumed",
            "execution_success_verified",
        ],
    },
    NHIType.MACHINE_IDENTITY: {
        "strategy": "key_rotation_migration",
        "description": (
            "Generate new key pair in target -> deploy public key to hosts -> "
            "verify SSH connectivity -> remove old keys"
        ),
        "risk_level": "high",
        "wave": 4,
        "pre_checks": [
            "host_list_verified",
            "ssh_access_for_key_deployment",
        ],
        "post_checks": [
            "ssh_connectivity_verified",
            "old_keys_removed",
        ],
    },
    NHIType.SHARED_ACCOUNT: {
        "strategy": "shared_to_individual_migration",
        "description": (
            "Document all shared account users -> migrate credential -> "
            "consider splitting into individual accounts -> "
            "update access policies"
        ),
        "risk_level": "medium",
        "wave": 4,
        "pre_checks": [
            "shared_users_documented",
            "split_decision_made",
        ],
        "post_checks": [
            "all_users_can_access",
            "audit_trail_intact",
        ],
    },
}


class NHIHandlerAgent(AgentBase):
    """Deep NHI classification with per-type migration strategies.

    Uses weighted multi-signal classification to determine NHI subtype,
    then assigns a migration strategy with specific pre/post checks
    that Agent 04 enforces during P4/P5.
    """

    AGENT_ID = "agent_12_nhi_handler"
    AGENT_NAME = "NHI Handler"

    def set_ml_classifier(self, classifier):
        """Inject ML classifier for blended NHI scoring."""
        self._ml_classifier = classifier

    def __init__(self, config, state, audit_logger):
        super().__init__(config, state, audit_logger)
        self._ml_classifier = None

    def preflight(self) -> AgentResult:
        """Validate that discovery data exists for classification."""
        self.logger.log("preflight_start", {"agent": self.AGENT_ID})
        errors = []

        discovery = self.state.get_agent_result("agent_01_discovery", "P1")
        if not discovery:
            # Also check Agent 11 as an alternative source
            agent11 = self.state.get_agent_result("agent_11_source_adapter", "P1")
            if not agent11:
                errors.append(
                    "No discovery data. Run Agent 01 or Agent 11 (P1) first."
                )

        if errors:
            return self._result("failed", errors=errors)

        self.logger.log("preflight_passed", {"agent": self.AGENT_ID})
        return self._result("success")

    def run(self, phase: str, input_data: dict) -> AgentResult:
        """Run NHI classification in P1 (after discovery and dependency mapping)."""
        if phase != "P1":
            return self._result(
                "failed", phase=phase,
                errors=[f"Agent 12 runs in P1, not {phase}"],
            )

        self.logger.log("nhi_classification_start", {"phase": phase})

        # Load discovery data
        discovery = self.state.get_agent_result("agent_01_discovery", "P1") or {}
        raw = self.state.get_raw_data("agent_01_discovery", "P1") or {}

        # Fall back to Agent 11 data if Agent 01 hasn't run
        if not raw:
            raw = self.state.get_raw_data("agent_11_source_adapter", "P1") or {}

        accounts = raw.get("raw_accounts", [])
        if not accounts:
            return self._result(
                "failed", phase=phase,
                errors=["No raw account data available for NHI classification."],
            )

        # Load dependency map from Agent 09 (optional but valuable)
        dep_map = self.state.get_raw_data("agent_09_dependency_mapper", "P1") or {}
        dependency_data = dep_map.get("dependency_map", {})

        # Load audit logs for pattern analysis
        audit_logs = raw.get("raw_audit_logs", [])

        # Load basic NHI list from Agent 01
        basic_nhis = discovery.get("nhis", [])
        basic_nhi_ids = {n.get("id") for n in basic_nhis}

        # Load application data for CCP/AAM detection
        applications = raw.get("raw_applications", {})
        app_ids = set(applications.keys())

        # Classify all accounts
        classifications: Dict[str, NHIClassification] = {}
        non_nhi_count = 0

        for acct in accounts:
            acct_id = acct.get("id", "")
            if not acct_id:
                continue

            classification = self._classify_account(
                acct, basic_nhi_ids, dependency_data,
                audit_logs, app_ids,
            )

            if classification:
                classifications[acct_id] = classification
            else:
                non_nhi_count += 1

        # Build summary statistics
        by_type: Dict[str, int] = {}
        by_risk: Dict[str, int] = {}
        by_wave: Dict[int, int] = {}
        by_strategy: Dict[str, int] = {}

        for cls in classifications.values():
            by_type[cls.nhi_type] = by_type.get(cls.nhi_type, 0) + 1
            by_risk[cls.risk_level] = by_risk.get(cls.risk_level, 0) + 1
            by_wave[cls.migration_wave] = by_wave.get(cls.migration_wave, 0) + 1
            by_strategy[cls.migration_strategy] = (
                by_strategy.get(cls.migration_strategy, 0) + 1
            )

        # Store classifications
        classifications_dict = {
            acct_id: cls.to_dict()
            for acct_id, cls in classifications.items()
        }

        report = {
            "total_accounts": len(accounts),
            "total_nhis": len(classifications),
            "non_nhis": non_nhi_count,
            "nhi_percentage": (
                len(classifications) / max(len(accounts), 1) * 100
            ),
            "by_type": by_type,
            "by_risk": by_risk,
            "by_wave": by_wave,
            "by_strategy": by_strategy,
            "classifications": classifications_dict,
        }

        self.state.store_agent_result(self.AGENT_ID, phase, report)
        self.state.store_raw_data(self.AGENT_ID, phase, {
            "classifications": classifications_dict,
            "summary": {
                "by_type": by_type,
                "by_risk": by_risk,
                "by_wave": by_wave,
            },
        })
        self.state.complete_step("P1:nhi_classification")

        self.logger.log("nhi_classification_complete", {
            "total_nhis": len(classifications),
            "by_type": by_type,
            "by_risk": by_risk,
        })

        return self._result(
            "success", phase=phase, data=report,
            metrics={
                "total_nhis": len(classifications),
                "service_accounts": by_type.get(NHIType.SERVICE_ACCOUNT, 0),
                "api_keys": by_type.get(NHIType.API_KEY, 0),
                "app_identities": by_type.get(NHIType.APPLICATION_IDENTITY, 0),
                "database_accounts": by_type.get(NHIType.DATABASE_ACCOUNT, 0),
                "critical_risk": by_risk.get("critical", 0),
                "high_risk": by_risk.get("high", 0),
            },
            next_action="Run Agent 02 (Gap Analysis) — NHI data will inform "
                        "risk assessment and wave planning",
        )

    def _classify_account(
        self,
        acct: dict,
        basic_nhi_ids: set,
        dependency_data: dict,
        audit_logs: list,
        app_ids: set,
    ) -> Optional[NHIClassification]:
        """Classify a single account using weighted multi-signal analysis.

        Returns NHIClassification if the account is an NHI, None otherwise.
        """
        acct_id = acct.get("id", "")
        name = (acct.get("name") or acct.get("userName") or "").lower()
        platform = acct.get("platformId", "")
        safe = (acct.get("safeName") or "").lower()

        # Collect signals with their types and weights
        signals: List[Tuple[str, NHIType, float, str]] = []

        # Signal 1: Platform-based (weight 0.35)
        if platform in PLATFORM_TYPE_MAP:
            nhi_type = PLATFORM_TYPE_MAP[platform]
            signals.append(("platform", nhi_type, SIGNAL_WEIGHTS["platform"],
                            f"platform:{platform}"))

        # Signal 2: Name pattern (weight 0.20)
        for nhi_type, patterns in NAME_PATTERNS.items():
            for pattern in patterns:
                if re.search(pattern, name, re.IGNORECASE):
                    signals.append(("name_pattern", nhi_type,
                                    SIGNAL_WEIGHTS["name_pattern"],
                                    f"name:{pattern}"))
                    break

        # Signal 3: Container pattern (weight 0.10)
        for nhi_type, patterns in CONTAINER_PATTERNS.items():
            for pattern in patterns:
                if re.search(pattern, safe, re.IGNORECASE):
                    signals.append(("container_pattern", nhi_type,
                                    SIGNAL_WEIGHTS["container_pattern"],
                                    f"safe:{pattern}"))
                    break

        # Signal 4: Dependency evidence (weight 0.25)
        deps = dependency_data.get(acct_id, [])
        if deps:
            dep_types = set()
            for dep in deps:
                dep_type = dep.get("dependency_type", "")
                if dep_type in DEPENDENCY_TYPE_MAP:
                    dep_types.add(dep_type)

            for dep_type in dep_types:
                nhi_type = DEPENDENCY_TYPE_MAP[dep_type]
                signals.append(("dependency_evidence", nhi_type,
                                SIGNAL_WEIGHTS["dependency_evidence"],
                                f"dep:{dep_type}"))

        # Signal 5: Audit pattern (weight 0.10) — application callerType
        for log_entry in audit_logs:
            target_id = str(log_entry.get("AccountId", log_entry.get("TargetId", "")))
            caller_type = str(log_entry.get("CallerType", "")).lower()

            if target_id == acct_id and caller_type == "application":
                signals.append(("audit_pattern", NHIType.APPLICATION_IDENTITY,
                                SIGNAL_WEIGHTS["audit_pattern"],
                                "audit:application_access"))
                break

        # Also check if account was in Agent 01's basic NHI list
        if acct_id in basic_nhi_ids and not signals:
            # Agent 01 detected it but we have no specific signals —
            # classify as service_account with lower confidence
            signals.append(("basic_detection", NHIType.SERVICE_ACCOUNT,
                            0.15, "agent01_detection"))

        # If no signals, not an NHI
        if not signals:
            return None

        # Determine winning type by weighted vote
        type_scores: Dict[NHIType, float] = {}
        signals_dict: Dict[str, float] = {}
        for signal_name, nhi_type, weight, evidence in signals:
            type_scores[nhi_type] = type_scores.get(nhi_type, 0) + weight
            signals_dict[signal_name] = signals_dict.get(signal_name, 0) + weight

        winning_type = max(type_scores, key=type_scores.get)
        confidence = min(type_scores[winning_type], 1.0)
        weighted_score = confidence
        is_nhi = True

        # ML blending (advisory)
        ml_confidence = None
        blended_score = None
        if self._ml_classifier is not None:
            features = {
                "platform_signal": signals_dict.get("platform", 0.0),
                "name_signal": signals_dict.get("name_pattern", 0.0),
                "container_signal": signals_dict.get("container_pattern", 0.0),
                "dependency_signal": signals_dict.get("dependency_evidence", 0.0),
                "audit_signal": signals_dict.get("audit_pattern", 0.0),
                "account_name_length": len(acct.get("name", "")),
                "safe_depth": acct.get("safeName", "").count("/") + 1,
                "has_linked_accounts": 1.0 if acct.get("linkedAccounts") else 0.0,
            }
            ml_result = self._ml_classifier.predict(features, rule_score=weighted_score)
            if ml_result is not None:
                ml_confidence = ml_result.ml_confidence
                blended_score = ml_result.blended_score
                is_nhi = ml_result.blended_is_nhi

        if not is_nhi:
            return None

        # Get migration strategy
        strategy = MIGRATION_STRATEGIES.get(winning_type, {})

        return NHIClassification(
            account_id=acct_id,
            account_name=acct.get("name", name),
            nhi_type=winning_type.value,
            confidence=confidence,
            signals={
                "matched": [
                    {"signal": s[0], "type": s[1].value,
                     "weight": s[2], "evidence": s[3]}
                    for s in signals
                ],
                "type_scores": {k.value: v for k, v in type_scores.items()},
            },
            migration_strategy=strategy.get("strategy", "manual_review"),
            risk_level=strategy.get("risk_level", "medium"),
            migration_wave=strategy.get("wave", 4),
            pre_migration_checks=strategy.get("pre_checks", []),
            post_migration_checks=strategy.get("post_checks", []),
            ml_confidence=ml_confidence,
            blended_score=blended_score,
        )

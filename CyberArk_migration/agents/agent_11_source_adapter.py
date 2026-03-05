"""Agent 11 — Multi-Vendor Source Adapter (G-01 + G-06 Gap Closure).

Loads accounts from any supported PAM vendor (CyberArk, BeyondTrust,
Delinea Secret Server, HashiCorp Vault) or cloud secrets store
(AWS Secrets Manager, Azure Key Vault, GCP Secret Manager) and
normalizes them to a canonical schema.

When this agent runs in P1, it produces normalized data that Agent 01
can consume instead of connecting to CyberArk directly. This enables
migration FROM any source TO Privilege Cloud.

Phases:
    P0: Adapter selection and connectivity validation
    P1: Full discovery via selected adapter
"""

import logging
from typing import Any, Dict, List, Optional

from core.base import AgentBase, AgentResult
from core.source_adapters import (
    ADAPTER_REGISTRY,
    NormalizedAccount,
    NormalizedContainer,
    NormalizedPlatform,
    SourceAdapter,
    get_source_adapter,
)

logger = logging.getLogger(__name__)


class SourceAdapterAgent(AgentBase):
    """Multi-vendor source adapter for PAM migrations.

    Wraps core/source_adapters.py to provide a standard agent interface.
    Normalizes all source data to the canonical NormalizedAccount format,
    then converts to CyberArk-style dicts so downstream agents (02-08)
    can consume the data without modification.

    Config:
        source.type: Adapter key (cyberark|beyondtrust|secretserver|hashicorp|aws|azure|gcp)
        source.<vendor>: Vendor-specific connection settings
        agent_11_source_adapter.cloud_discovery: List of cloud adapters to run alongside
    """

    AGENT_ID = "agent_11_source_adapter"
    AGENT_NAME = "Multi-Vendor Source Adapter"

    def __init__(self, config: dict, state, logger_instance):
        super().__init__(config, state, logger_instance)
        self._adapter: Optional[SourceAdapter] = None

    def preflight(self) -> AgentResult:
        """Validate source configuration and test connectivity."""
        self.logger.log("preflight_start", {"agent": self.AGENT_ID})
        errors = []

        source_cfg = self.config.get("source", {})
        source_type = source_cfg.get("type", "cyberark").lower()

        # Validate source type is known
        if source_type not in ADAPTER_REGISTRY:
            errors.append(
                f"Unknown source.type '{source_type}'. "
                f"Supported: {', '.join(ADAPTER_REGISTRY.keys())}"
            )
            return self._result("failed", errors=errors)

        # Test connectivity
        try:
            adapter = get_source_adapter(self.config)
            adapter.connect()
            checks = adapter.preflight_check()
            adapter.disconnect()
        except Exception as e:
            errors.append(f"Source connectivity failed: {type(e).__name__}: {e}")
            return self._result("failed", errors=errors)

        if checks.get("errors"):
            errors.extend(checks["errors"])

        if not checks.get("can_list_accounts"):
            errors.append(
                f"Source adapter '{source_type}' cannot list accounts. "
                "Check credentials and permissions."
            )

        if errors:
            return self._result("failed", errors=errors, data=checks)

        self.logger.log("preflight_passed", {
            "source_type": source_type,
            "checks": checks,
        })
        return self._result("success", data={
            "source_type": source_type,
            "connectivity": checks,
        })

    def run(self, phase: str, input_data: dict) -> AgentResult:
        """Run source discovery and normalization."""
        if phase not in ("P0", "P1"):
            return self._result(
                "failed", phase=phase,
                errors=[f"Agent 11 runs in P0/P1, not {phase}"],
            )

        if phase == "P0":
            return self._run_p0(input_data)
        return self._run_p1(input_data)

    def _run_p0(self, input_data: dict) -> AgentResult:
        """P0: Validate adapter selection and report capabilities."""
        source_cfg = self.config.get("source", {})
        source_type = source_cfg.get("type", "cyberark").lower()
        agent_cfg = self.config.get("agent_11_source_adapter", {})
        cloud_sources = agent_cfg.get("cloud_discovery", [])

        adapters_info = {"primary": source_type, "cloud_discovery": cloud_sources}

        # Validate cloud adapters if configured
        for cloud_type in cloud_sources:
            if cloud_type not in ADAPTER_REGISTRY:
                return self._result(
                    "failed", phase="P0",
                    errors=[f"Unknown cloud adapter '{cloud_type}' in cloud_discovery"],
                )

        self.logger.log("adapter_selection", adapters_info)
        self.state.store_agent_result(self.AGENT_ID, "P0", adapters_info)
        self.state.complete_step("P0:source_adapter_selection")

        return self._result(
            "success", phase="P0", data=adapters_info,
            next_action="Run Agent 11 P1 for full source discovery",
        )

    def _run_p1(self, input_data: dict) -> AgentResult:
        """P1: Full discovery via the configured source adapter.

        Workflow:
            1. Connect to source via adapter
            2. Enumerate accounts, containers, platforms
            3. Enumerate applications and audit logs
            4. Normalize all data
            5. Convert to CyberArk-style format for downstream compatibility
            6. Optionally discover cloud secrets (G-06)
            7. Store results for Agent 01 and downstream consumption
        """
        self.logger.log("source_discovery_start", {"phase": "P1"})
        source_type = self.config.get("source", {}).get("type", "cyberark").lower()
        agent_cfg = self.config.get("agent_11_source_adapter", {})
        audit_log_days = agent_cfg.get("audit_log_days", 90)

        all_accounts: List[NormalizedAccount] = []
        all_containers: List[NormalizedContainer] = []
        all_platforms: List[NormalizedPlatform] = []
        all_applications: List[dict] = []
        all_audit_logs: List[dict] = []
        adapter_errors: List[str] = []

        # Primary source adapter
        try:
            with get_source_adapter(self.config) as adapter:
                self.logger.log("primary_adapter_connected", {
                    "vendor": adapter.VENDOR,
                })

                accounts = adapter.get_accounts()
                all_accounts.extend(accounts)
                self.logger.log("accounts_discovered", {
                    "vendor": adapter.VENDOR,
                    "count": len(accounts),
                })

                containers = adapter.get_containers()
                all_containers.extend(containers)

                platforms = adapter.get_platforms()
                all_platforms.extend(platforms)

                applications = adapter.get_applications()
                all_applications.extend(applications)

                audit_logs = adapter.get_audit_logs(days=audit_log_days)
                all_audit_logs.extend(audit_logs)

        except Exception as e:
            self.logger.log_error("primary_adapter_failed", {
                "vendor": source_type,
            }, str(e))
            return self._result(
                "failed", phase="P1",
                errors=[f"Primary source adapter ({source_type}) failed: {e}"],
            )

        # Cloud discovery (G-06) — run additional adapters for unmanaged secrets
        cloud_sources = agent_cfg.get("cloud_discovery", [])
        for cloud_type in cloud_sources:
            try:
                cloud_cfg = dict(self.config)
                cloud_cfg["source"] = {"type": cloud_type}
                cloud_adapter_class = ADAPTER_REGISTRY.get(cloud_type)
                if not cloud_adapter_class:
                    continue

                with cloud_adapter_class(cloud_cfg) as cloud_adapter:
                    cloud_accounts = cloud_adapter.get_accounts()
                    all_accounts.extend(cloud_accounts)
                    self.logger.log("cloud_discovery", {
                        "vendor": cloud_type,
                        "secrets_found": len(cloud_accounts),
                    })

                    cloud_containers = cloud_adapter.get_containers()
                    all_containers.extend(cloud_containers)

            except Exception as e:
                err_msg = f"Cloud adapter '{cloud_type}' failed: {e}"
                adapter_errors.append(err_msg)
                self.logger.log_error("cloud_adapter_failed", {
                    "vendor": cloud_type,
                }, str(e))

        # Convert to CyberArk-style format for downstream agent compatibility
        cyberark_format_accounts = [a.to_cyberark_format() for a in all_accounts]
        container_dicts = [c.to_dict() for c in all_containers]
        platform_dicts = [p.to_dict() for p in all_platforms]

        # Build safe_members dict from normalized containers
        safe_members: Dict[str, list] = {}
        for container in all_containers:
            if container.members:
                safe_members[container.name] = container.members

        # Account classification summary
        by_vendor: Dict[str, int] = {}
        by_type: Dict[str, int] = {}
        by_secret_type: Dict[str, int] = {}
        for acct in all_accounts:
            by_vendor[acct.source_vendor] = by_vendor.get(acct.source_vendor, 0) + 1
            by_type[acct.account_type] = by_type.get(acct.account_type, 0) + 1
            by_secret_type[acct.secret_type] = by_secret_type.get(acct.secret_type, 0) + 1

        # Store raw data for downstream agents (compatible with Agent 01 format)
        self.state.store_raw_data(self.AGENT_ID, "P1", {
            "raw_accounts": cyberark_format_accounts,
            "raw_safes": container_dicts,
            "raw_safe_members": safe_members,
            "raw_platforms": platform_dicts,
            "raw_applications": {
                a.get("AppID", a.get("appID", f"app_{i}")): {"app": a}
                for i, a in enumerate(all_applications)
            },
            "normalized_accounts": [a.to_dict() for a in all_accounts],
        })

        manifest = {
            "source_type": source_type,
            "cloud_sources": cloud_sources,
            "accounts": {
                "total": len(all_accounts),
                "by_vendor": by_vendor,
                "by_type": by_type,
                "by_secret_type": by_secret_type,
            },
            "containers": {"total": len(all_containers)},
            "platforms": {"total": len(all_platforms)},
            "applications": {"total": len(all_applications)},
            "audit_logs": {"total": len(all_audit_logs)},
            "adapter_errors": adapter_errors,
        }

        self.state.store_agent_result(self.AGENT_ID, "P1", manifest)
        self.state.complete_step("P1:source_adapter_discovery")

        self.logger.log("source_discovery_complete", {
            "total_accounts": len(all_accounts),
            "total_containers": len(all_containers),
            "vendors": list(by_vendor.keys()),
            "cloud_sources_run": len(cloud_sources),
            "adapter_errors": len(adapter_errors),
        })

        status = "success" if not adapter_errors else "partial"
        return self._result(
            status, phase="P1", data=manifest,
            metrics={
                "accounts_discovered": len(all_accounts),
                "containers_discovered": len(all_containers),
                "platforms_discovered": len(all_platforms),
                "cloud_secrets_discovered": sum(
                    1 for a in all_accounts if a.source_vendor in ("aws", "azure", "gcp")
                ),
            },
            errors=adapter_errors if adapter_errors else [],
            next_action="Run Agent 01 (Discovery) — will use Agent 11 data "
                        "instead of direct CyberArk connection",
        )

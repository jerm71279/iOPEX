"""CyberArk PAM Migration Agents — 15-Agent Orchestrator."""

from .agent_01_discovery import DiscoveryAgent
from .agent_02_gap_analysis import GapAnalysisAgent
from .agent_03_permissions import PermissionMappingAgent
from .agent_04_etl import ETLOrchestrationAgent
from .agent_05_heartbeat import HeartbeatAgent
from .agent_06_integration import IntegrationRepointingAgent
from .agent_07_compliance import ComplianceAgent
from .agent_08_runbook import RunbookAgent
from .agent_09_dependency_mapper import DependencyMapperAgent
from .agent_10_staging import StagingValidationAgent
from .agent_11_source_adapter import SourceAdapterAgent
from .agent_12_nhi_handler import NHIHandlerAgent
from .agent_13_platform_plugins import PlatformPluginAgent
from .agent_14_onboarding import OnboardingAgent
from .agent_15_hybrid_fleet import HybridFleetAgent

AGENT_REGISTRY = {
    "01-discovery": DiscoveryAgent,
    "02-gap-analysis": GapAnalysisAgent,
    "03-permissions": PermissionMappingAgent,
    "04-etl": ETLOrchestrationAgent,
    "05-heartbeat": HeartbeatAgent,
    "06-integration": IntegrationRepointingAgent,
    "07-compliance": ComplianceAgent,
    "08-runbook": RunbookAgent,
    "09-dependency-mapper": DependencyMapperAgent,
    "10-staging": StagingValidationAgent,
    "11-source-adapter": SourceAdapterAgent,
    "12-nhi-handler": NHIHandlerAgent,
    "13-platform-plugins": PlatformPluginAgent,
    "14-onboarding": OnboardingAgent,
    "15-hybrid-fleet": HybridFleetAgent,
}

__all__ = [
    "DiscoveryAgent", "GapAnalysisAgent", "PermissionMappingAgent",
    "ETLOrchestrationAgent", "HeartbeatAgent", "IntegrationRepointingAgent",
    "ComplianceAgent", "RunbookAgent",
    "DependencyMapperAgent", "StagingValidationAgent", "SourceAdapterAgent",
    "NHIHandlerAgent", "PlatformPluginAgent", "OnboardingAgent",
    "HybridFleetAgent", "AGENT_REGISTRY",
]

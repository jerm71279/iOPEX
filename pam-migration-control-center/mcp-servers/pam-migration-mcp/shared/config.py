"""Centralized configuration for both MCP servers.

Uses pydantic-settings for env-var-backed configuration with sensible
defaults for local development and Docker deployment.
"""

from pathlib import Path
from typing import Optional

from pydantic_settings import BaseSettings


class PamMcpSettings(BaseSettings):
    """Settings for the pam-migration-mcp server."""

    model_config = {"env_prefix": "PAM_MCP_"}

    # MCP server
    host: str = "0.0.0.0"
    port: int = 8100
    server_name: str = "pam-migration-mcp"

    # Migration option: "a" (Privilege Cloud) or "b" (Secret Server)
    migration_option: str = "b"

    # Orchestrator paths (mounted read-only in Docker)
    orchestrator_path_a: str = "/orchestrator-a"
    orchestrator_path_b: str = "/orchestrator-b"

    # Shared output (Docker volume: shared-state)
    output_dir: str = "./output"
    state_dir: str = "./output/state"
    log_dir: str = "./output/logs"

    # Environment
    environment: str = "dev"

    # Watchdog defaults
    watchdog_timeout_minutes: int = 120
    watchdog_check_interval: int = 30

    # CyberArk on-prem PVWA (Condition 4)
    cyberark_base_url: str = ""
    cyberark_auth_type: str = "LDAP"
    cyberark_verify_ssl: bool = True
    cyberark_timeout: int = 30

    # Azure Key Vault (credential loading)
    key_vault_uri: Optional[str] = None

    # Frozen account registry
    frozen_registry_path: str = "./output/state/frozen_accounts.json"

    @property
    def orchestrator_path(self) -> str:
        if self.migration_option == "a":
            return self.orchestrator_path_a
        return self.orchestrator_path_b

    @property
    def state_dir_path(self) -> Path:
        return Path(self.state_dir)

    @property
    def log_dir_path(self) -> Path:
        return Path(self.log_dir)


class ControlCenterMcpSettings(BaseSettings):
    """Settings for the control-center-mcp server."""

    model_config = {"env_prefix": "CC_MCP_"}

    # MCP server
    host: str = "0.0.0.0"
    port: int = 8101
    server_name: str = "control-center-mcp"

    # Control Center FastAPI URL
    control_center_url: str = "http://control-center:8080"

    # Timeout for proxied requests (seconds)
    request_timeout: float = 30.0

"""Configuration for the control-center-mcp server."""

from pydantic_settings import BaseSettings


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

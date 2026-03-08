"""Audit bridge — wraps the orchestrator's AuditLogger.

Creates an AuditLogger that writes to the SAME output/logs/ directory
as the CLI coordinator and agents, but to its own JSONL file
(mcp-server.audit.jsonl).  Cross-correlation with other log files
is via session_id and timestamp.
"""

import logging
import sys
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

_audit_instance: Optional["AuditLogger"] = None  # noqa: F821


def get_audit_logger(
    orchestrator_path: str,
    log_dir: str = "./output/logs",
    environment: str = "dev",
    agent_id: str = "mcp-server",
) -> "AuditLogger":  # noqa: F821
    """Get or create the MCP server's AuditLogger instance.

    Imports AuditLogger from the orchestrator's core/logging.py and
    creates a singleton writing to the shared log directory.

    Args:
        orchestrator_path: Path to the orchestrator root (contains core/).
        log_dir: Shared log directory (same as coordinator uses).
        environment: Current environment (dev/staging/prod).
        agent_id: Logger identity (default: "mcp-server").

    Returns:
        AuditLogger instance writing to {log_dir}/{agent_id}.audit.jsonl.
    """
    global _audit_instance
    if _audit_instance is not None:
        return _audit_instance

    # Ensure orchestrator is importable
    path = str(Path(orchestrator_path).resolve())
    if path not in sys.path:
        sys.path.insert(0, path)

    try:
        from core.logging import AuditLogger
    except ImportError as exc:
        logger.error(
            "Cannot import AuditLogger from %s/core/logging.py: %s",
            orchestrator_path, exc,
        )
        raise RuntimeError(
            f"Orchestrator core not found at {orchestrator_path}. "
            "Ensure the orchestrator directory is mounted correctly."
        ) from exc

    _audit_instance = AuditLogger(
        agent_id=agent_id,
        environment=environment,
        output_dir=log_dir,
    )
    logger.info(
        "AuditLogger initialized — agent_id=%s, log_dir=%s",
        agent_id, log_dir,
    )
    return _audit_instance


def reset_audit_instance():
    """Clear the cached audit instance (for testing)."""
    global _audit_instance
    _audit_instance = None

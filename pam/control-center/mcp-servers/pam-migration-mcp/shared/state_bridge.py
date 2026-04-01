"""State bridge — wraps the orchestrator's MigrationState.

Imports MigrationState from the orchestrator's core/state.py so the
MCP server shares the SAME state file as the CLI coordinator.  Both
processes read/write output/state/migration_state.json with fcntl
exclusive locking, so concurrent access is safe.
"""

import logging
import sys
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

_state_instance: Optional["MigrationState"] = None  # noqa: F821


def _ensure_orchestrator_on_path(orchestrator_path: str):
    """Add the orchestrator directory to sys.path if not present."""
    path = str(Path(orchestrator_path).resolve())
    if path not in sys.path:
        sys.path.insert(0, path)
        logger.info("Added orchestrator to sys.path: %s", path)


def get_migration_state(
    orchestrator_path: str,
    state_dir: str = "./output/state",
) -> "MigrationState":  # noqa: F821
    """Get or create the shared MigrationState instance.

    The first call imports MigrationState from the orchestrator and
    creates a singleton.  Subsequent calls return the same instance.

    Args:
        orchestrator_path: Path to the orchestrator root (contains core/).
        state_dir: Directory for the state JSON file.

    Returns:
        MigrationState instance (shared with CLI coordinator).
    """
    global _state_instance
    if _state_instance is not None:
        return _state_instance

    _ensure_orchestrator_on_path(orchestrator_path)

    try:
        from core.state import MigrationState
    except ImportError as exc:
        logger.error(
            "Cannot import MigrationState from %s/core/state.py: %s",
            orchestrator_path, exc,
        )
        raise RuntimeError(
            f"Orchestrator core not found at {orchestrator_path}. "
            "Ensure the orchestrator directory is mounted correctly."
        ) from exc

    _state_instance = MigrationState(state_dir=state_dir)
    logger.info(
        "MigrationState initialized — state_dir=%s, migration_id=%s",
        state_dir, _state_instance.get_migration_id(),
    )
    return _state_instance


def reset_state_instance():
    """Clear the cached state instance (for testing)."""
    global _state_instance
    _state_instance = None

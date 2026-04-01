"""PAM Migration MCP Server — 10 high-level migration tools.

Wraps the 15-agent orchestrator pipeline as MCP tools with:
  - Crash recovery: watchdog timer, signal handlers, frozen account registry
  - State consistency: shared MigrationState, shared audit logs, phase enforcement
  - PVWA coverage: read-only CyberArk account tools using existing cyberark_client.py

Transport: HTTP/Streamable (NOT STDIO — avoids NeighborJack vulnerability)
"""

import logging
import sys
from contextlib import asynccontextmanager
from pathlib import Path

from mcp.server.fastmcp import FastMCP

from .shared.config import PamMcpSettings
from .shared.credential_loader import load_credentials
from .shared.state_bridge import get_migration_state
from .shared.audit_bridge import get_audit_logger
from .shared.phase_enforcer import PhaseEnforcer
from .crash_recovery.frozen_registry import FrozenAccountRegistry
from .crash_recovery.watchdog import WatchdogManager
from .crash_recovery import signal_handlers

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
)
logger = logging.getLogger(__name__)

settings = PamMcpSettings()

# Shared instances — initialized in lifespan
_state = None
_audit = None
_enforcer = None
_registry = None
_watchdog = None


def _get_state():
    return _state


def _get_audit():
    return _audit


def _get_enforcer():
    return _enforcer


def _get_registry():
    return _registry


def _get_watchdog():
    return _watchdog


@asynccontextmanager
async def lifespan(server):
    """MCP server startup and shutdown lifecycle.

    Startup:
      1. Load credentials from Key Vault (or env vars)
      2. Initialize shared MigrationState + AuditLogger
      3. Check for orphaned frozen accounts → emergency unfreeze
      4. Register signal handlers (SIGTERM/SIGINT)
      5. Initialize watchdog manager

    Shutdown:
      - Cancel watchdog, save state, unfreeze
    """
    global _state, _audit, _enforcer, _registry, _watchdog

    logger.info("=== PAM Migration MCP Server starting ===")
    logger.info("Migration option: %s", settings.migration_option)
    logger.info("Orchestrator path: %s", settings.orchestrator_path)

    # 1. Load credentials
    cred_status = load_credentials(settings.key_vault_uri)
    logger.info("Credentials loaded: %s", {k: v for k, v in cred_status.items() if v})

    # Fail fast in non-dev environments if Key Vault was configured but
    # the minimum required credentials didn't load. Prevents the server
    # from starting in a credential-less state against a live PVWA.
    if settings.environment != "dev" and settings.key_vault_uri:
        required = {"CYBERARK_USERNAME", "CYBERARK_PASSWORD"}
        missing = [k for k in required if not cred_status.get(k)]
        if missing:
            raise RuntimeError(
                f"Key Vault credential load failed — missing: {missing}. "
                "Set PAM_MCP_ENVIRONMENT=dev to override (local only)."
            )

    # 2. Initialize state + audit
    _state = get_migration_state(
        orchestrator_path=settings.orchestrator_path,
        state_dir=settings.state_dir,
    )
    _audit = get_audit_logger(
        orchestrator_path=settings.orchestrator_path,
        log_dir=settings.log_dir,
        environment=settings.environment,
    )
    _enforcer = PhaseEnforcer(_state)

    # 3. Initialize frozen account registry + check for orphans
    _registry = FrozenAccountRegistry(settings.frozen_registry_path)
    if _registry.has_orphaned_freezes():
        logger.warning(
            "ORPHANED FREEZES DETECTED: %d accounts frozen from previous session",
            _registry.count,
        )
        _audit.log("orphaned_freeze_detected", {
            "frozen_count": _registry.count,
            "frozen_accounts": list(_registry.get_frozen_ids())[:50],
        })
        # Attempt PVWA unfreeze
        unfrozen = _recover_orphaned_freezes(_registry)
        _audit.log("orphaned_freeze_recovery", {
            "unfrozen": unfrozen,
            "remaining": _registry.count,
        })

    # 4. Initialize watchdog
    _watchdog = WatchdogManager(
        _registry,
        audit_callback=_audit.log,
    )

    # 5. Register signal handlers
    signal_handlers.register(
        watchdog=_watchdog,
        registry=_registry,
        state=_state,
        audit=_audit,
    )

    _audit.log("mcp_server_started", {
        "migration_option": settings.migration_option,
        "environment": settings.environment,
        "migration_id": _state.get_migration_id(),
    })

    logger.info("=== PAM Migration MCP Server ready ===")
    yield

    # Shutdown
    logger.info("MCP server shutting down...")
    _watchdog.cancel()
    if _registry.count > 0:
        logger.warning("Unfreezing %d accounts on shutdown", _registry.count)
        _registry.unfreeze_all()
    _state.save()
    _audit.log("mcp_server_stopped")


def _recover_orphaned_freezes(registry: FrozenAccountRegistry) -> int:
    """Attempt to unfreeze orphaned accounts via PVWA API."""
    if not settings.cyberark_base_url:
        logger.warning(
            "Cannot recover orphaned freezes — CYBERARK_BASE_URL not set. "
            "Manual unfreeze required for: %s",
            list(registry.get_frozen_ids()),
        )
        return 0

    try:
        # Add orchestrator to path for CyberArkClient import
        orch_path = str(Path(settings.orchestrator_path).resolve())
        if orch_path not in sys.path:
            sys.path.insert(0, orch_path)

        from core.cyberark_client import CyberArkClient

        config = {
            "base_url": settings.cyberark_base_url,
            "auth_type": settings.cyberark_auth_type,
            "verify_ssl": settings.cyberark_verify_ssl,
            "timeout": settings.cyberark_timeout,
        }
        unfrozen = 0
        with CyberArkClient(config) as client:
            for acct_id in list(registry.get_frozen_ids()):
                try:
                    client.enable_account_management(acct_id)
                    registry.unfreeze(acct_id)
                    unfrozen += 1
                except Exception as exc:
                    logger.error("Failed to unfreeze %s: %s", acct_id, exc)
        return unfrozen
    except Exception as exc:
        logger.error("Orphaned freeze recovery failed: %s", exc)
        return 0


# ── Create MCP instance ──────────────────────────────────────────

mcp = FastMCP(
    settings.server_name,
    lifespan=lifespan,
)

# ── Register tools from submodules ────────────────────────────────
# Import tool modules so their @mcp.tool() decorators run

from .tools import migration  # noqa: E402, F401
from .tools import accounts   # noqa: E402, F401
from .tools import preflight  # noqa: E402, F401
from .tools import discovery  # noqa: E402, F401
from .tools import permissions  # noqa: E402, F401
from .tools import validation  # noqa: E402, F401
from .tools import etl  # noqa: E402, F401
from .tools import compliance  # noqa: E402, F401


def main():
    """Run the MCP server with HTTP transport."""
    mcp.run(transport="streamable-http")


if __name__ == "__main__":
    main()

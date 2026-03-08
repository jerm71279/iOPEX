"""Signal handlers — safe shutdown for the MCP server.

Mirrors coordinator.py lines 112-129, plus watchdog cancellation and
emergency unfreeze.  On SIGTERM/SIGINT:
  1. Cancel watchdog timer
  2. Emergency unfreeze all frozen accounts
  3. Save migration state
  4. Log mcp_emergency_shutdown to audit
  5. Exit with 128 + signum

Pattern source: CyberArk migration/coordinator.py lines 116-129
"""

import logging
import signal
import sys
from typing import Optional

logger = logging.getLogger(__name__)

# Module-level references set by register()
_watchdog = None
_registry = None
_state = None
_audit = None


def register(*, watchdog=None, registry=None, state=None, audit=None):
    """Register components for signal-handler cleanup.

    Call this during MCP server startup after all components are
    initialized.  Components are optional — the handler skips any
    that are None.

    Args:
        watchdog: WatchdogManager instance.
        registry: FrozenAccountRegistry instance.
        state: MigrationState instance.
        audit: AuditLogger instance.
    """
    global _watchdog, _registry, _state, _audit
    _watchdog = watchdog
    _registry = registry
    _state = state
    _audit = audit

    signal.signal(signal.SIGTERM, _handler)
    signal.signal(signal.SIGINT, _handler)
    logger.info("Signal handlers registered (SIGTERM, SIGINT)")


def _handler(signum: int, frame):
    """Emergency shutdown handler."""
    sig_name = signal.Signals(signum).name
    logger.warning("Received %s — performing emergency shutdown...", sig_name)

    # 1. Cancel watchdog
    if _watchdog is not None:
        try:
            _watchdog.cancel()
        except Exception:
            pass

    # 2. Emergency unfreeze
    unfrozen = []
    if _registry is not None:
        try:
            unfrozen = _registry.unfreeze_all()
            if unfrozen:
                logger.warning(
                    "Emergency unfroze %d accounts on %s",
                    len(unfrozen), sig_name,
                )
        except Exception:
            logger.error("Emergency unfreeze FAILED — manual intervention required!")

    # 3. Save state
    if _state is not None:
        try:
            _state.save()
        except Exception:
            logger.error("State save failed during shutdown")

    # 4. Audit log
    if _audit is not None:
        try:
            _audit.log("mcp_emergency_shutdown", {
                "signal": sig_name,
                "unfrozen_accounts": len(unfrozen),
                "state_saved": _state is not None,
            })
        except Exception:
            pass

    logger.info("Shutdown complete. Exiting with code %d.", 128 + signum)
    sys.exit(128 + signum)

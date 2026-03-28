"""Watchdog manager — auto-unfreezes accounts on ETL timeout.

Wraps threading.Timer with the FrozenAccountRegistry so that if an
ETL batch hangs or the timer fires, all frozen accounts are unfrozen
and the event is logged to the audit trail.

Pattern source: CyberArk migration/agents/agent_04_etl.py lines 600-631
"""

import logging
import threading
from typing import Callable, Optional

from .frozen_registry import FrozenAccountRegistry

logger = logging.getLogger(__name__)


class WatchdogManager:
    """Manages watchdog timers for ETL batch operations.

    Each ETL batch gets a timer.  If the batch doesn't complete before
    timeout, the watchdog fires: unfreezes all frozen accounts and
    calls the audit callback.
    """

    def __init__(
        self,
        registry: FrozenAccountRegistry,
        *,
        audit_callback: Optional[Callable[[str, dict], None]] = None,
    ):
        """
        Args:
            registry: The shared FrozenAccountRegistry.
            audit_callback: Called on watchdog events with (action, details).
                            Typically bound to AuditLogger.log().
        """
        self._registry = registry
        self._audit = audit_callback
        self._timer: Optional[threading.Timer] = None
        self._lock = threading.Lock()
        self._active_batch: Optional[str] = None

    def start(self, timeout_minutes: int, batch_id: str = "unknown"):
        """Start a watchdog timer for the given batch.

        Cancels any existing timer first (only one batch at a time).
        """
        with self._lock:
            self.cancel()
            self._active_batch = batch_id

            def _trigger():
                logger.error(
                    "WATCHDOG: Timeout after %dm for batch %s. Emergency unfreeze.",
                    timeout_minutes, batch_id,
                )
                frozen_ids = self._registry.unfreeze_all()
                if self._audit:
                    self._audit("watchdog_timeout", {
                        "batch_id": batch_id,
                        "timeout_minutes": timeout_minutes,
                        "unfrozen_count": len(frozen_ids),
                        "unfrozen_accounts": frozen_ids[:50],
                    })

            self._timer = threading.Timer(timeout_minutes * 60, _trigger)
            self._timer.daemon = True
            self._timer.start()
            logger.info(
                "Watchdog started: batch=%s, timeout=%dm",
                batch_id, timeout_minutes,
            )

    def cancel(self):
        """Cancel the active watchdog timer."""
        with self._lock:
            if self._timer is not None:
                self._timer.cancel()
                self._timer = None
                logger.info("Watchdog cancelled for batch %s", self._active_batch)
                self._active_batch = None

    @property
    def is_active(self) -> bool:
        with self._lock:
            return self._timer is not None and self._timer.is_alive()

    @property
    def active_batch(self) -> Optional[str]:
        with self._lock:
            return self._active_batch

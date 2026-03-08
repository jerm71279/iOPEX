"""Persistent frozen account registry.

Tracks which CyberArk accounts have CPM management disabled ("frozen")
during ETL batches.  Persisted to disk so that if the MCP server or
Agent 04 crashes, the accounts can be unfrozen on restart.

Uses the same atomic-write pattern as core/state.py:
  tempfile → fsync → os.replace (POSIX atomic rename)

Thread-safe via threading.Lock (Agent 04's in-memory list has no lock).
"""

import json
import logging
import os
import tempfile
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Set

logger = logging.getLogger(__name__)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class FrozenAccountRegistry:
    """Persistent registry of frozen (CPM-disabled) CyberArk accounts.

    Each entry records the account ID, when it was frozen, which batch
    caused the freeze, and the session that owns it.
    """

    def __init__(self, registry_path: str = "./output/state/frozen_accounts.json"):
        self._path = Path(registry_path)
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self._accounts: Dict[str, dict] = {}
        self._load()

    # ── persistence ──────────────────────────────────────────────

    def _load(self):
        """Load registry from disk."""
        if self._path.exists():
            try:
                with open(self._path, "r") as f:
                    data = json.load(f)
                self._accounts = data.get("frozen_accounts", {})
                logger.info(
                    "Loaded frozen registry: %d accounts", len(self._accounts),
                )
            except (json.JSONDecodeError, IOError) as exc:
                logger.warning("Corrupt frozen registry, starting fresh: %s", exc)
                self._accounts = {}
        else:
            self._accounts = {}

    def _save(self):
        """Atomically write registry to disk."""
        data = {
            "last_updated": _now(),
            "frozen_accounts": self._accounts,
            "count": len(self._accounts),
        }
        fd, tmp_path = tempfile.mkstemp(
            dir=str(self._path.parent), suffix=".tmp", prefix="frozen_",
        )
        try:
            with os.fdopen(fd, "w") as f:
                json.dump(data, f, indent=2)
                f.flush()
                os.fsync(f.fileno())
            os.replace(tmp_path, str(self._path))
        except Exception:
            try:
                os.unlink(tmp_path)
            except OSError:
                pass
            raise

    # ── public API ───────────────────────────────────────────────

    def freeze(
        self,
        account_id: str,
        *,
        wave: Optional[int] = None,
        batch: Optional[int] = None,
        session_id: Optional[str] = None,
    ):
        """Record an account as frozen."""
        with self._lock:
            self._accounts[account_id] = {
                "frozen_at": _now(),
                "wave": wave,
                "batch": batch,
                "session_id": session_id,
            }
            self._save()
            logger.debug("Frozen account %s (wave=%s, batch=%s)", account_id, wave, batch)

    def unfreeze(self, account_id: str):
        """Remove an account from the frozen registry."""
        with self._lock:
            if account_id in self._accounts:
                del self._accounts[account_id]
                self._save()
                logger.debug("Unfrozen account %s", account_id)

    def unfreeze_all(self) -> List[str]:
        """Remove all frozen accounts and return their IDs."""
        with self._lock:
            ids = list(self._accounts.keys())
            self._accounts.clear()
            self._save()
            if ids:
                logger.info("Unfrozen all %d accounts", len(ids))
            return ids

    def get_frozen_ids(self) -> Set[str]:
        """Return the set of currently frozen account IDs."""
        with self._lock:
            return set(self._accounts.keys())

    def get_frozen_details(self) -> Dict[str, dict]:
        """Return full frozen account details (for diagnostics)."""
        with self._lock:
            return dict(self._accounts)

    @property
    def count(self) -> int:
        with self._lock:
            return len(self._accounts)

    def has_orphaned_freezes(self, session_id: Optional[str] = None) -> bool:
        """Check if any freezes are orphaned (from a different session).

        If session_id is provided, freezes owned by OTHER sessions are
        considered orphaned.  If not provided, ALL freezes are orphaned
        (server just started, no prior session).
        """
        with self._lock:
            if not self._accounts:
                return False
            if session_id is None:
                return True  # Server just started — any freeze is orphaned
            return any(
                entry.get("session_id") != session_id
                for entry in self._accounts.values()
            )

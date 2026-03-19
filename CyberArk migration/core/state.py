"""Persistent migration state machine.

Tracks current phase, completed steps, agent results, and human approvals.
State is persisted to a JSON file with atomic writes and file locking
so migrations can be resumed after interruption.
"""

import fcntl
import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional


PHASES = ["P0", "P1", "P2", "P3", "P4", "P5", "P6", "P7"]

PHASE_NAMES = {
    "P0": "Environment Setup",
    "P1": "Discovery & Dependency Mapping",
    "P2": "Infrastructure Preparation",
    "P3": "Safe & Policy Migration",
    "P4": "Pilot Migration",
    "P5": "Production Batches",
    "P6": "Parallel Running & Cutover",
    "P7": "Decommission & Close-Out",
}

# Maximum entries in append-only lists to prevent unbounded growth
MAX_STEPS = 5000
MAX_ERRORS = 1000
MAX_APPROVALS = 500


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class MigrationState:
    """JSON-backed persistent state machine with atomic writes and file locking."""

    def __init__(self, state_dir: str = "./output/state"):
        self._state_dir = Path(state_dir)
        self._state_dir.mkdir(parents=True, exist_ok=True)
        self._state_file = self._state_dir / "migration_state.json"
        self._backup_file = self._state_dir / "migration_state.json.bak"
        self._lock_file = self._state_dir / "migration_state.lock"
        self._data = self._load()

    # ── persistence ──────────────────────────────────────────────

    def _load(self) -> dict:
        """Load state from file, falling back to backup on corruption."""
        if self._state_file.exists():
            try:
                with open(self._state_file, "r") as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError):
                # State file corrupted — try backup
                if self._backup_file.exists():
                    try:
                        with open(self._backup_file, "r") as f:
                            data = json.load(f)
                        # Restore from backup
                        self._atomic_write(data)
                        return data
                    except (json.JSONDecodeError, IOError):
                        pass
        return self._default_state()

    def _atomic_write(self, data: dict):
        """Write state atomically: write to temp file, fsync, rename."""
        data["last_updated"] = _now()

        # Write to temp file in same directory (same filesystem for rename)
        fd, tmp_path = tempfile.mkstemp(
            dir=str(self._state_dir), suffix=".tmp", prefix="state_"
        )
        try:
            with os.fdopen(fd, "w") as f:
                json.dump(data, f, indent=2, default=str)
                f.flush()
                os.fsync(f.fileno())
            # Atomic rename (POSIX guarantees this is atomic on same fs)
            os.replace(tmp_path, str(self._state_file))
        except Exception:
            # Clean up temp file on failure
            try:
                os.unlink(tmp_path)
            except OSError:
                pass
            raise

    def save(self):
        """Save state with file locking and atomic write."""
        # Create backup of current state before writing
        if self._state_file.exists():
            try:
                import shutil
                shutil.copy2(str(self._state_file), str(self._backup_file))
            except IOError:
                pass

        # Acquire exclusive lock
        lock_fd = open(self._lock_file, "w")
        try:
            fcntl.flock(lock_fd, fcntl.LOCK_EX)
            self._atomic_write(self._data)
        finally:
            fcntl.flock(lock_fd, fcntl.LOCK_UN)
            lock_fd.close()

    def _default_state(self) -> dict:
        now = _now()
        return {
            "migration_id": None,
            "created": now,
            "last_updated": now,
            "current_phase": None,
            "phase_status": {p: "pending" for p in PHASES},
            "completed_steps": [],
            "agent_results": {},
            "human_approvals": [],
            "batch_progress": {},
            "errors": [],
        }

    # ── phase management ─────────────────────────────────────────

    @property
    def current_phase(self) -> Optional[str]:
        return self._data.get("current_phase")

    def start_migration(self, migration_id: str):
        self._data = self._default_state()
        self._data["migration_id"] = migration_id
        self._data["current_phase"] = "P0"
        self._data["phase_status"]["P0"] = "in_progress"
        self.save()

    def advance_phase(self) -> Optional[str]:
        current = self.current_phase
        if current is None:
            return None
        idx = PHASES.index(current)
        self._data["phase_status"][current] = "completed"
        if idx + 1 < len(PHASES):
            next_phase = PHASES[idx + 1]
            self._data["current_phase"] = next_phase
            self._data["phase_status"][next_phase] = "in_progress"
            self.save()
            return next_phase
        self._data["current_phase"] = None
        self.save()
        return None

    def get_phase_status(self, phase: str) -> str:
        return self._data["phase_status"].get(phase, "unknown")

    # ── step tracking ────────────────────────────────────────────

    def complete_step(self, step_id: str, details: dict = None):
        entry = {
            "step": step_id,
            "completed_at": _now(),
            "details": details or {},
        }
        self._data["completed_steps"].append(entry)
        # Cap list size
        if len(self._data["completed_steps"]) > MAX_STEPS:
            self._data["completed_steps"] = self._data["completed_steps"][-MAX_STEPS:]
        self.save()

    def is_step_completed(self, step_id: str) -> bool:
        return any(
            s["step"] == step_id for s in self._data["completed_steps"]
        )

    # ── agent results ────────────────────────────────────────────

    def store_agent_result(self, agent_id: str, phase: str, result: dict):
        """Store agent result. Strips raw data to keep state file manageable."""
        # Strip large raw data from results before storing
        clean = {
            k: v for k, v in result.items()
            if not k.startswith("raw_")
        }
        key = f"{agent_id}:{phase}"
        self._data["agent_results"][key] = {
            "stored_at": _now(),
            "result": clean,
        }
        self.save()

    def store_raw_data(self, agent_id: str, phase: str, data: dict):
        """Store large raw data to a separate file (not in state)."""
        raw_dir = self._state_dir / "raw"
        raw_dir.mkdir(exist_ok=True)
        raw_file = raw_dir / f"{agent_id}_{phase}.json"
        with open(raw_file, "w") as f:
            json.dump(data, f, default=str)

    def get_raw_data(self, agent_id: str, phase: str) -> Optional[dict]:
        """Load raw data from separate file."""
        raw_file = self._state_dir / "raw" / f"{agent_id}_{phase}.json"
        if raw_file.exists():
            with open(raw_file, "r") as f:
                return json.load(f)
        return None

    def get_agent_result(self, agent_id: str, phase: str) -> Optional[dict]:
        key = f"{agent_id}:{phase}"
        entry = self._data["agent_results"].get(key)
        return entry["result"] if entry else None

    # ── human approvals ──────────────────────────────────────────

    def record_approval(self, gate: str, approved: bool, reviewer: str = ""):
        self._data["human_approvals"].append({
            "gate": gate,
            "approved": approved,
            "reviewer": reviewer,
            "timestamp": _now(),
        })
        if len(self._data["human_approvals"]) > MAX_APPROVALS:
            self._data["human_approvals"] = self._data["human_approvals"][-MAX_APPROVALS:]
        self.save()

    def get_approvals(self) -> list:
        return self._data.get("human_approvals", [])

    def get_migration_id(self) -> Optional[str]:
        return self._data.get("migration_id")

    # ── batch progress (P5) ──────────────────────────────────────

    def update_batch(self, wave: int, batch: int, status: str, details: dict = None):
        key = f"W{wave}B{batch}"
        self._data["batch_progress"][key] = {
            "status": status,
            "updated": _now(),
            "details": details or {},
        }
        self.save()

    def get_batch_status(self, wave: int, batch: int) -> Optional[str]:
        key = f"W{wave}B{batch}"
        entry = self._data["batch_progress"].get(key)
        return entry["status"] if entry else None

    # ── errors ───────────────────────────────────────────────────

    def record_error(self, agent_id: str, error: str, details: dict = None):
        self._data["errors"].append({
            "agent": agent_id,
            "error": error,
            "details": details or {},
            "timestamp": _now(),
        })
        if len(self._data["errors"]) > MAX_ERRORS:
            self._data["errors"] = self._data["errors"][-MAX_ERRORS:]
        self.save()

    # ── summary ──────────────────────────────────────────────────

    def summary(self) -> dict:
        return {
            "migration_id": self._data.get("migration_id"),
            "current_phase": self.current_phase,
            "phase_name": PHASE_NAMES.get(self.current_phase, "N/A"),
            "phases": {
                p: self._data["phase_status"][p] for p in PHASES
            },
            "steps_completed": len(self._data["completed_steps"]),
            "approvals": len(self._data["human_approvals"]),
            "errors": len(self._data["errors"]),
            "batches_tracked": len(self._data["batch_progress"]),
        }

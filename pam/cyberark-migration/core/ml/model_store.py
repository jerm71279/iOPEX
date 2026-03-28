"""Thread-safe model persistence using joblib.

Models are stored as ``.joblib`` files under ``output/models/``
with JSON sidecar metadata (timestamp, version, metrics).
"""

import fcntl
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional


class ModelStore:
    """Save / load ML models with file-locking safety."""

    def __init__(self, models_dir: str = "./output/models"):
        self._dir = Path(models_dir)
        self._dir.mkdir(parents=True, exist_ok=True)
        self._lock_file = self._dir / "models.lock"

    # ── public API ────────────────────────────────────────────

    def save(self, model_name: str, model_obj: Any, metadata: Optional[Dict] = None):
        """Persist *model_obj* under *model_name* with optional metadata."""
        import joblib

        model_path = self._dir / f"{model_name}.joblib"
        meta_path = self._dir / f"{model_name}.meta.json"

        meta = {
            "model_name": model_name,
            "saved_at": datetime.now(timezone.utc).isoformat(),
            "ml_version": "0.1.0",
            **(metadata or {}),
        }

        with self._lock():
            joblib.dump(model_obj, str(model_path))
            with open(meta_path, "w") as f:
                json.dump(meta, f, indent=2, default=str)

    def load(self, model_name: str) -> Optional[Any]:
        """Return the model object, or ``None`` if not found."""
        import joblib

        model_path = self._dir / f"{model_name}.joblib"
        if not model_path.exists():
            return None
        with self._lock():
            return joblib.load(str(model_path))

    def exists(self, model_name: str) -> bool:
        return (self._dir / f"{model_name}.joblib").exists()

    def list_models(self) -> List[str]:
        return [p.stem for p in self._dir.glob("*.joblib")]

    def get_metadata(self, model_name: str) -> Optional[Dict]:
        meta_path = self._dir / f"{model_name}.meta.json"
        if not meta_path.exists():
            return None
        with open(meta_path, "r") as f:
            return json.load(f)

    # ── internal ──────────────────────────────────────────────

    class _lock:
        """Context manager for file-based locking (fcntl)."""

        def __init__(self):
            self._path = None
            self._fd = None

        def __enter__(self):
            # Reuse the store's lock file path via closure isn't clean,
            # so we fall back to a simple approach: caller creates us.
            return self

        def __exit__(self, *exc):
            if self._fd is not None:
                fcntl.flock(self._fd, fcntl.LOCK_UN)
                os.close(self._fd)

    def _lock(self):
        """Acquire an advisory file lock."""
        fd = os.open(str(self._lock_file), os.O_CREAT | os.O_RDWR)
        fcntl.flock(fd, fcntl.LOCK_EX)

        class _Lock:
            def __enter__(self_inner):
                return self_inner

            def __exit__(self_inner, *exc):
                fcntl.flock(fd, fcntl.LOCK_UN)
                os.close(fd)

        return _Lock()

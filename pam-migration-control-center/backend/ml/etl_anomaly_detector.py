"""ETL step-timing anomaly detection.

Uses EWMA (Exponentially Weighted Moving Average) for cold start
and Isolation Forest for warm operation.  All predictions are
advisory — they never block the migration pipeline.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
import math


ETL_STEPS = [
    "FREEZE", "EXPORT", "TRANSFORM",
    "SAFE_CREATION", "IMPORT", "HEARTBEAT", "UNFREEZE",
]


@dataclass
class AnomalyResult:
    """Result of anomaly check for a single ETL step."""
    is_anomaly: bool
    confidence: float          # 0.0 – 1.0
    explanation: str
    step_name: str
    duration: float            # seconds
    ewma_score: float          # z-score from EWMA (always available)
    if_score: Optional[float] = None  # Isolation Forest score (None when cold)
    blended_score: Optional[float] = None


@dataclass
class StepRecord:
    """One recorded ETL step execution."""
    step_name: str
    duration: float
    account_count: int = 0
    nhi_ratio: float = 0.0
    platform_complexity: float = 0.0
    batch_position: int = 0
    wave: int = 0
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class ETLAnomalyDetector:
    """Detect anomalous ETL step timings using EWMA + Isolation Forest."""

    def __init__(self, config: Optional[Dict] = None):
        cfg = (config or {}).get("ml", {}).get("etl_anomaly", {})
        self._alpha = cfg.get("ewma_alpha", 0.3)
        self._threshold_sigma = cfg.get("ewma_threshold_sigma", 2.0)
        self._contamination = cfg.get("isolation_forest_contamination", 0.1)
        self._min_samples_if = cfg.get("min_samples_for_if", 30)
        self._w_ewma = cfg.get("blend_weight_ewma", 0.4)
        self._w_if = cfg.get("blend_weight_if", 0.6)

        # Per-step EWMA state
        self._ewma_mean: Dict[str, float] = {}
        self._ewma_var: Dict[str, float] = {}
        self._sample_count: Dict[str, int] = {s: 0 for s in ETL_STEPS}

        # Historical records for Isolation Forest training
        self._history: List[StepRecord] = []

        # Isolation Forest model (None until trained)
        self._if_model = None

    # ── public API ────────────────────────────────────────────

    def record_step(self, step_name: str, duration: float,
                    metadata: Optional[Dict] = None) -> Optional[AnomalyResult]:
        """Record a step execution and return anomaly result if anomalous."""
        meta = metadata or {}
        record = StepRecord(
            step_name=step_name,
            duration=duration,
            account_count=meta.get("account_count", 0),
            nhi_ratio=meta.get("nhi_ratio", 0.0),
            platform_complexity=meta.get("platform_complexity", 0.0),
            batch_position=meta.get("batch_position", 0),
            wave=meta.get("wave", 0),
        )
        self._history.append(record)

        # EWMA update
        ewma_z = self._update_ewma(step_name, duration)

        # Isolation Forest score (if model trained)
        if_score = None
        if self._if_model is not None:
            if_score = self._predict_if(record)

        # Blend scores
        if if_score is not None:
            blended = self._w_ewma * min(abs(ewma_z) / 3.0, 1.0) + self._w_if * if_score
        else:
            blended = min(abs(ewma_z) / 3.0, 1.0)

        is_anomaly = False
        explanation = ""

        if blended > 0.5:
            is_anomaly = True
            mean = self._ewma_mean.get(step_name, duration)
            if if_score is not None and if_score > 0.5:
                explanation = (
                    f"{step_name} took {duration:.1f}s (expected ~{mean:.1f}s). "
                    f"Both EWMA (z={ewma_z:.2f}) and Isolation Forest "
                    f"(score={if_score:.2f}) flagged this as anomalous."
                )
            else:
                explanation = (
                    f"{step_name} took {duration:.1f}s (expected ~{mean:.1f}s). "
                    f"EWMA z-score of {ewma_z:.2f} exceeds {self._threshold_sigma} sigma threshold."
                )

        result = AnomalyResult(
            is_anomaly=is_anomaly,
            confidence=min(blended, 1.0),
            explanation=explanation,
            step_name=step_name,
            duration=duration,
            ewma_score=ewma_z,
            if_score=if_score,
            blended_score=blended,
        )

        return result if is_anomaly else None

    def retrain(self) -> Dict[str, Any]:
        """Retrain Isolation Forest if enough samples have accumulated."""
        total = len(self._history)
        if total < self._min_samples_if:
            return {
                "trained": False,
                "reason": f"insufficient samples ({total}/{self._min_samples_if})",
                "total_samples": total,
            }

        from sklearn.ensemble import IsolationForest
        import numpy as np

        X = self._build_feature_matrix(self._history)
        model = IsolationForest(
            contamination=self._contamination,
            random_state=42,
            n_estimators=100,
        )
        model.fit(X)
        self._if_model = model

        return {
            "trained": True,
            "total_samples": total,
            "feature_shape": list(X.shape),
        }

    def get_state(self) -> Dict:
        """Serialisable snapshot for persistence."""
        return {
            "ewma_mean": dict(self._ewma_mean),
            "ewma_var": dict(self._ewma_var),
            "sample_count": dict(self._sample_count),
            "history_len": len(self._history),
            "if_trained": self._if_model is not None,
        }

    # ── EWMA internals ───────────────────────────────────────

    def _update_ewma(self, step_name: str, duration: float) -> float:
        """Update EWMA state and return z-score for this observation."""
        count = self._sample_count.get(step_name, 0)

        if count == 0:
            self._ewma_mean[step_name] = duration
            self._ewma_var[step_name] = 0.0
            self._sample_count[step_name] = 1
            return 0.0

        prev_mean = self._ewma_mean[step_name]
        prev_var = self._ewma_var[step_name]
        alpha = self._alpha

        new_mean = alpha * duration + (1 - alpha) * prev_mean
        new_var = alpha * (duration - new_mean) ** 2 + (1 - alpha) * prev_var

        self._ewma_mean[step_name] = new_mean
        self._ewma_var[step_name] = new_var
        self._sample_count[step_name] = count + 1

        std = math.sqrt(new_var) if new_var > 0 else 1.0
        z = (duration - new_mean) / std if std > 0 else 0.0
        return z

    # ── Isolation Forest internals ────────────────────────────

    def _build_feature_matrix(self, records: List[StepRecord]):
        """Build numpy feature matrix from step records."""
        import numpy as np

        rows = []
        for r in records:
            rows.append([
                r.duration,
                r.account_count,
                r.nhi_ratio,
                r.platform_complexity,
                r.batch_position,
            ])
        return np.array(rows, dtype=np.float64)

    def _predict_if(self, record: StepRecord) -> float:
        """Return anomaly score 0-1 from Isolation Forest."""
        import numpy as np

        X = np.array([[
            record.duration,
            record.account_count,
            record.nhi_ratio,
            record.platform_complexity,
            record.batch_position,
        ]])
        raw = self._if_model.decision_function(X)[0]
        score = max(0.0, min(1.0, 0.5 - raw))
        return score

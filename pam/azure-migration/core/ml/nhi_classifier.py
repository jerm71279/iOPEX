"""NHI classification blending — LightGBM + rule-based scores.

Cold start: returns ``None`` (pure rule-based used at 100 %).
Warm (≥50 labeled samples): LightGBM binary classifier blended
with existing weighted signal scores.  Rules always dominate (60/40).
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


@dataclass
class NHIMLResult:
    """ML classification result for one account."""
    ml_confidence: float       # 0.0 – 1.0, model's P(is_nhi)
    ml_is_nhi: bool            # model's binary decision
    blended_score: float       # 0.6 * rule + 0.4 * ml
    blended_is_nhi: bool       # final blended decision


@dataclass
class LabeledExample:
    """One training example: features + ground truth."""
    features: Dict[str, float]
    is_nhi: bool
    source: str = "rule"       # "rule", "human_correction", "validated"
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class NHIMLClassifier:
    """LightGBM-based NHI classifier with rule-based blending."""

    FEATURE_NAMES = [
        "platform_signal", "name_signal", "container_signal",
        "dependency_signal", "audit_signal",
        "account_name_length", "safe_depth", "has_linked_accounts",
    ]

    def __init__(self, config: Optional[Dict] = None):
        cfg = (config or {}).get("ml", {}).get("nhi_classifier", {})
        self._min_samples = cfg.get("min_samples_for_ml", 50)
        self._w_rules = cfg.get("blend_weight_rules", 0.6)
        self._w_ml = cfg.get("blend_weight_ml", 0.4)
        self._retrain_threshold = cfg.get("retrain_after_corrections", 10)

        self._model = None
        self._training_data: List[LabeledExample] = []
        self._corrections_since_train = 0
        self._is_trained = False

    # ── public API ────────────────────────────────────────────

    def predict(self, features: Dict[str, float],
                rule_score: float = 0.0) -> Optional[NHIMLResult]:
        """Return blended prediction, or ``None`` if model isn't trained yet.

        Args:
            features: dict with keys matching FEATURE_NAMES
            rule_score: existing weighted rule score (0.0 – 1.0)
        """
        if not self._is_trained or self._model is None:
            return None

        import numpy as np

        X = self._features_to_array(features)
        ml_proba = float(self._model.predict_proba(X)[0, 1])
        ml_is_nhi = ml_proba >= 0.5

        blended = self._w_rules * rule_score + self._w_ml * ml_proba
        blended_is_nhi = blended >= 0.5

        return NHIMLResult(
            ml_confidence=ml_proba,
            ml_is_nhi=ml_is_nhi,
            blended_score=blended,
            blended_is_nhi=blended_is_nhi,
        )

    def add_labeled_example(self, features: Dict[str, float],
                            is_nhi: bool, source: str = "rule"):
        """Add a training example.  Call ``retrain()`` after batch additions."""
        self._training_data.append(LabeledExample(
            features=features, is_nhi=is_nhi, source=source,
        ))
        if source == "human_correction":
            self._corrections_since_train += 1

    def should_retrain(self) -> bool:
        """True if enough new data warrants retraining."""
        if len(self._training_data) < self._min_samples:
            return not self._is_trained  # first training
        return self._corrections_since_train >= self._retrain_threshold

    def retrain(self) -> Dict[str, Any]:
        """Train or retrain the LightGBM model.

        Returns training metadata (sample counts, feature importance, etc.).
        """
        n = len(self._training_data)
        if n < self._min_samples:
            return {
                "trained": False,
                "reason": f"insufficient samples ({n}/{self._min_samples})",
                "total_samples": n,
            }

        import lightgbm as lgb
        import numpy as np

        X, y = self._build_training_set()

        # Count class distribution
        n_pos = int(np.sum(y))
        n_neg = n - n_pos

        params = {
            "objective": "binary",
            "metric": "binary_logloss",
            "verbosity": -1,
            "num_leaves": 15,
            "learning_rate": 0.1,
            "n_estimators": 50,
            "min_child_samples": 5,
            "is_unbalance": True,
            "random_state": 42,
        }

        model = lgb.LGBMClassifier(**params)
        model.fit(X, y)

        self._model = model
        self._is_trained = True
        self._corrections_since_train = 0

        # Feature importance
        importance = dict(zip(self.FEATURE_NAMES, model.feature_importances_.tolist()))

        return {
            "trained": True,
            "total_samples": n,
            "positive_samples": n_pos,
            "negative_samples": n_neg,
            "feature_importance": importance,
        }

    def get_state(self) -> Dict:
        """Serialisable snapshot (training data only; model saved via ModelStore)."""
        return {
            "training_samples": len(self._training_data),
            "corrections_since_train": self._corrections_since_train,
            "is_trained": self._is_trained,
        }

    # ── internal ──────────────────────────────────────────────

    def _features_to_array(self, features: Dict[str, float]):
        """Convert feature dict to numpy array in canonical order."""
        import numpy as np
        row = [features.get(name, 0.0) for name in self.FEATURE_NAMES]
        return np.array([row], dtype=np.float64)

    def _build_training_set(self):
        """Build X, y arrays from labeled examples."""
        import numpy as np

        X_rows = []
        y_vals = []
        for ex in self._training_data:
            row = [ex.features.get(name, 0.0) for name in self.FEATURE_NAMES]
            X_rows.append(row)
            y_vals.append(1.0 if ex.is_nhi else 0.0)
        return np.array(X_rows, dtype=np.float64), np.array(y_vals, dtype=np.float64)

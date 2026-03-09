"""Live ML provider — bridges control center to actual ML models.

Seeds both models with synthetic data at startup, trains them, and runs
inference against mock accounts.  Replaces the hardcoded dicts in ml_data.py.
"""

import re
import warnings
from typing import Dict, List, Optional

warnings.filterwarnings("ignore", message="X does not have valid feature names")

from backend.ml.etl_anomaly_detector import ETLAnomalyDetector, ETL_STEPS
from backend.ml.nhi_classifier import NHIMLClassifier
from backend.ml.synthetic_data import generate_etl_timing_data, generate_nhi_labeled_data
from backend.mock_data.accounts_data import ACCOUNTS


# ── NHI signal extraction helpers ─────────────────────────────────────

_NHI_PLATFORMS = {
    "WinServiceAccount", "UnixSSHKeys", "AWSAccessKeys",
    "AzureServicePrincipal", "OracleDB",
}

_NHI_NAME_PATTERNS = re.compile(
    r"^(svc[_-]|app[_-]|bot[_-]|rpa[_-]|api[_-])"
    r"|service.?account|automation|scheduler",
    re.IGNORECASE,
)

_NHI_SAFE_PATTERNS = re.compile(
    r"(appcred|automation|cicd|pipeline|svc|service|nhi)",
    re.IGNORECASE,
)


def _extract_features(account: dict) -> Dict[str, float]:
    """Extract 8-feature vector from a mock account's attributes."""
    platform = account.get("platformId", "")
    name = account.get("name", "")
    safe = account.get("safeName", "")
    deps = account.get("dependencies", [])

    platform_signal = 1.0 if platform in _NHI_PLATFORMS else (
        0.5 if platform in ("MSSql", "Oracle", "MySQL") else 0.0
    )
    name_signal = 1.0 if _NHI_NAME_PATTERNS.search(name) else 0.0
    container_signal = 1.0 if _NHI_SAFE_PATTERNS.search(safe) else 0.0
    dependency_signal = min(len(deps) / 5.0, 1.0)
    audit_signal = 0.7 if account.get("is_nhi") else 0.2
    account_name_length = float(len(name))
    safe_depth = float(safe.count("-") + 1)
    has_linked = 1.0 if deps else 0.0

    return {
        "platform_signal": platform_signal,
        "name_signal": name_signal,
        "container_signal": container_signal,
        "dependency_signal": dependency_signal,
        "audit_signal": audit_signal,
        "account_name_length": account_name_length,
        "safe_depth": safe_depth,
        "has_linked_accounts": has_linked,
    }


class LiveMLProvider:
    """Bridge between control center and actual ML models."""

    def __init__(self):
        self.etl_detector = ETLAnomalyDetector()
        self.nhi_classifier = NHIMLClassifier()
        self.classifications: Dict[str, dict] = {}
        self.etl_anomalies: Dict[str, list] = {}
        self._etl_train_result = {}
        self._nhi_train_result = {}
        self._seed_and_train()
        self._classify_accounts()
        self._compute_wave_anomalies()

    def _seed_and_train(self):
        """Generate synthetic training data and train both models."""
        # ETL: 200 synthetic step records → trains EWMA + IF
        etl_data = generate_etl_timing_data(n=200)
        for rec in etl_data:
            self.etl_detector.record_step(rec["step_name"], rec["duration"], rec)
        self._etl_train_result = self.etl_detector.retrain()

        # NHI: 150 synthetic labeled examples → trains LightGBM
        nhi_data = generate_nhi_labeled_data(n=150)
        for ex in nhi_data:
            features = {k: ex[k] for k in NHIMLClassifier.FEATURE_NAMES}
            self.nhi_classifier.add_labeled_example(features, ex["is_nhi"])
        self._nhi_train_result = self.nhi_classifier.retrain()

    def _classify_accounts(self):
        """Run NHI classifier against all 50 mock accounts."""
        for acct in ACCOUNTS:
            features = _extract_features(acct)
            rule_score = acct.get("nhi_confidence", 0.0)
            result = self.nhi_classifier.predict(features, rule_score)
            self.classifications[acct["id"]] = {
                "rule_score": round(rule_score, 3),
                "ml_confidence": round(result.ml_confidence, 3) if result else None,
                "blended_score": round(result.blended_score, 3) if result else None,
                "source": "blended" if result else "rule_only",
            }

    def _compute_wave_anomalies(self):
        """Compute per-wave ETL anomaly scores using the trained detector."""
        import random
        rng = random.Random(99)

        baselines = {
            "FREEZE":        (5.0, 1.5),
            "EXPORT":        (30.0, 8.0),
            "TRANSFORM":     (10.0, 3.0),
            "SAFE_CREATION": (8.0, 2.0),
            "IMPORT":        (20.0, 5.0),
            "HEARTBEAT":     (15.0, 4.0),
            "UNFREEZE":      (3.0, 1.0),
        }

        # Wave-specific anomaly injection points (same story as mock data)
        wave_anomaly_steps = {
            "1": [],
            "2": ["TRANSFORM"],
            "3": ["IMPORT", "HEARTBEAT"],
            "4": ["EXPORT", "TRANSFORM", "HEARTBEAT"],
            "5": [],
        }

        for wave_id in ["1", "2", "3", "4", "5"]:
            anomaly_steps = wave_anomaly_steps[wave_id]
            wave_results = []

            for step_name in ETL_STEPS:
                base_mean, base_std = baselines[step_name]
                wave_int = int(wave_id)
                wave_factor = 1.4 if wave_int >= 4 else 1.0
                nhi_ratio = rng.uniform(0.3, 0.7) if wave_int >= 4 else rng.uniform(0.0, 0.2)

                duration = max(0.5, rng.gauss(base_mean * wave_factor, base_std))

                if step_name in anomaly_steps:
                    duration *= rng.uniform(2.5, 4.0)

                result = self.etl_detector.record_step(step_name, duration, {
                    "account_count": rng.randint(10, 80),
                    "nhi_ratio": nhi_ratio,
                    "platform_complexity": rng.uniform(1.0, 1.7),
                    "batch_position": rng.randint(1, 5),
                    "wave": wave_int,
                })

                ewma_state = self.etl_detector.get_state()
                ewma_z = abs(ewma_state["ewma_mean"].get(step_name, 0.0) - duration)
                std = (ewma_state["ewma_var"].get(step_name, 1.0)) ** 0.5
                z_score = ewma_z / std if std > 0.01 else 0.0

                entry = {
                    "step": step_name,
                    "ewma_z": round(z_score, 2),
                    "if_score": round(result.if_score, 2) if result and result.if_score is not None else 0.1,
                    "blended": round(result.blended_score, 2) if result else round(z_score / 6.0, 2),
                    "flagged": result is not None,
                    "explanation": result.explanation if result else None,
                }
                wave_results.append(entry)

            self.etl_anomalies[wave_id] = wave_results

    def get_anomalies(self, wave: str) -> dict:
        """Return ETL anomaly data for a wave."""
        steps = self.etl_anomalies.get(wave, [])
        flagged = [s for s in steps if s["flagged"]]
        return {
            "wave": wave,
            "total_anomalies": len(flagged),
            "steps": steps,
        }

    def get_classifications(self) -> dict:
        """Return all account classifications + summary."""
        sources = list(self.classifications.values())
        rule_only = sum(1 for s in sources if s["source"] == "rule_only")
        blended = sum(1 for s in sources if s["source"] == "blended")

        anomaly_by_wave = {}
        for wid, steps in self.etl_anomalies.items():
            anomaly_by_wave[wid] = sum(1 for s in steps if s["flagged"])

        return {
            "classifications": self.classifications,
            "summary": {
                "total_accounts": len(self.classifications),
                "rule_only": rule_only,
                "blended": blended,
                "human_corrected": 0,
                "anomalies_by_wave": anomaly_by_wave,
            },
        }

    def get_status(self) -> dict:
        """Return live model status (training state, sample counts)."""
        etl_state = self.etl_detector.get_state()
        nhi_state = self.nhi_classifier.get_state()

        return {
            "enabled": True,
            "version": "0.1.0",
            "inference": "live",
            "etl_detector": {
                "state": "warm" if etl_state.get("if_trained") else "cold",
                "training_samples": etl_state["history_len"],
                "anomalies_detected": sum(
                    sum(1 for s in steps if s["flagged"])
                    for steps in self.etl_anomalies.values()
                ),
                "model_type": "EWMA + Isolation Forest",
                "ewma_alpha": 0.3,
                "if_contamination": 0.1,
                "blend_weight_ewma": 0.4,
                "blend_weight_if": 0.6,
                "if_trained": self._etl_train_result.get("trained", False),
                "if_feature_shape": self._etl_train_result.get("feature_shape"),
            },
            "nhi_classifier": {
                "state": "warm" if nhi_state["is_trained"] else "cold",
                "training_samples": nhi_state["training_samples"],
                "accuracy": None,
                "model_type": "LightGBM + Rule Blending",
                "blend_weights": {"rules": 0.6, "ml": 0.4},
                "lgb_trained": self._nhi_train_result.get("trained", False),
                "positive_samples": self._nhi_train_result.get("positive_samples"),
                "negative_samples": self._nhi_train_result.get("negative_samples"),
                "feature_importance": self._nhi_train_result.get("feature_importance"),
            },
        }

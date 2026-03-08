"""Wave-level ML lifecycle management.

Coordinates model loading, injection into agents, retraining after
each wave, and wave-level reporting.  Called from ``coordinator.py``
before and after each wave in P5 (Production Batches).
"""

from datetime import datetime, timezone
from typing import Any, Dict, Optional

from core.ml import is_ml_enabled
from core.ml.model_store import ModelStore
from core.ml.etl_anomaly_detector import ETLAnomalyDetector
from core.ml.nhi_classifier import NHIMLClassifier


class WaveLearningCoordinator:
    """Pre/post wave hooks for ML model lifecycle."""

    def __init__(self, state, logger, config: dict):
        self._state = state
        self._logger = logger
        self._config = config
        self._store = ModelStore()

        self._etl_detector: Optional[ETLAnomalyDetector] = None
        self._nhi_classifier: Optional[NHIMLClassifier] = None

    # ── pre-wave ──────────────────────────────────────────────

    def pre_wave(self, wave_num: int) -> Dict[str, Any]:
        """Load or initialise models before wave execution.

        Returns status dict for logging.
        """
        status = {
            "wave": wave_num,
            "ml_enabled": is_ml_enabled(self._config),
            "etl_detector": "disabled",
            "nhi_classifier": "disabled",
        }

        if not is_ml_enabled(self._config):
            self._logger.log("ml_pre_wave", status)
            return status

        # ETL Anomaly Detector
        self._etl_detector = ETLAnomalyDetector(self._config)
        if self._store.exists("etl_anomaly_detector_state"):
            saved = self._store.load("etl_anomaly_detector_state")
            if saved:
                self._etl_detector.load_state(saved)
            status["etl_detector"] = "loaded_from_prior_wave"
        else:
            status["etl_detector"] = "cold_start"

        # NHI Classifier
        self._nhi_classifier = NHIMLClassifier(self._config)
        if self._store.exists("nhi_classifier_model"):
            model = self._store.load("nhi_classifier_model")
            if model:
                self._nhi_classifier._model = model
                self._nhi_classifier._is_trained = True
                status["nhi_classifier"] = "loaded_from_prior_wave"
            else:
                status["nhi_classifier"] = "cold_start"
        else:
            status["nhi_classifier"] = "cold_start"

        self._logger.log("ml_pre_wave", status)
        return status

    # ── accessors for injection ───────────────────────────────

    @property
    def etl_detector(self) -> Optional[ETLAnomalyDetector]:
        return self._etl_detector

    @property
    def nhi_classifier(self) -> Optional[NHIMLClassifier]:
        return self._nhi_classifier

    # ── post-wave ─────────────────────────────────────────────

    def post_wave(self, wave_num: int,
                  wave_results: Optional[Dict] = None) -> Dict[str, Any]:
        """Retrain models and persist after wave completion.

        Args:
            wave_num: completed wave number (1-5)
            wave_results: optional dict with wave outcome data

        Returns status dict for logging.
        """
        report = {
            "wave": wave_num,
            "etl_retrain": None,
            "nhi_retrain": None,
        }

        if not is_ml_enabled(self._config):
            self._logger.log("ml_post_wave", report)
            return report

        # Retrain ETL Anomaly Detector
        if self._etl_detector is not None:
            retrain_result = self._etl_detector.retrain()
            report["etl_retrain"] = retrain_result

            # Save EWMA state (always) and IF model (if trained)
            self._store.save(
                "etl_anomaly_detector_state",
                self._etl_detector.get_state(),
                {"wave": wave_num, "type": "ewma_state"},
            )
            if retrain_result.get("trained"):
                self._store.save(
                    "etl_anomaly_detector_model",
                    self._etl_detector._if_model,
                    {"wave": wave_num, "type": "isolation_forest"},
                )

        # Retrain NHI Classifier
        if self._nhi_classifier is not None:
            if self._nhi_classifier.should_retrain():
                retrain_result = self._nhi_classifier.retrain()
                report["nhi_retrain"] = retrain_result

                if retrain_result.get("trained"):
                    self._store.save(
                        "nhi_classifier_model",
                        self._nhi_classifier._model,
                        {"wave": wave_num, "type": "lightgbm"},
                    )
            else:
                report["nhi_retrain"] = {"trained": False, "reason": "no_retrain_needed"}

        self._logger.log("ml_post_wave", report)
        return report

    # ── reporting ─────────────────────────────────────────────

    def get_wave_report(self) -> Dict[str, Any]:
        """Summary of ML model states for display / audit."""
        report = {
            "ml_enabled": is_ml_enabled(self._config),
            "models_on_disk": self._store.list_models(),
        }

        if self._etl_detector:
            report["etl_detector"] = self._etl_detector.get_state()
        if self._nhi_classifier:
            report["nhi_classifier"] = self._nhi_classifier.get_state()

        return report

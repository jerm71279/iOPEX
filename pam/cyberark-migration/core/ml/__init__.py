"""ML module for adaptive migration intelligence.

Provides ETL anomaly detection (Priority 1) and NHI classification
blending (Priority 3). All ML is advisory-only — never blocks the
migration pipeline. Controlled by the ``ml.enabled`` kill switch
in agent_config.json.
"""

ML_VERSION = "0.1.0"


def is_ml_enabled(config: dict) -> bool:
    """Check the kill switch.  Returns False if scikit-learn is missing."""
    if not config.get("ml", {}).get("enabled", False):
        return False
    try:
        import sklearn  # noqa: F401
        return True
    except ImportError:
        return False

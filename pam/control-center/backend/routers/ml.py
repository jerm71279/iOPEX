"""ML model status, ETL anomaly scores, and NHI classification endpoints.

Uses LiveMLProvider for real model inference. Falls back to hardcoded
mock data if ML dependencies are unavailable or models fail to load.
"""

from fastapi import APIRouter, Query

router = APIRouter()

# Try live ML provider; fall back to static mock data
_provider = None
_provider_error: str | None = None
try:
    from backend.ml_provider import LiveMLProvider
    _provider = LiveMLProvider()
except Exception as e:
    import logging
    logging.getLogger(__name__).warning("ML provider failed to load, using mock data: %s", e)
    _provider_error = str(e)

if _provider is None:
    from backend.mock_data.ml_data import (
        ML_STATUS, ETL_ANOMALIES, ETL_STEP_BASELINES, ACCOUNT_ML, ML_SUMMARY,
    )


@router.get("/status")
async def ml_status():
    """ML model states — ETL anomaly detector + NHI classifier."""
    if _provider:
        return _provider.get_status()
    return {**ML_STATUS, "inference": "mock", "mock_fallback": True, "mock_reason": _provider_error}


@router.get("/anomalies")
async def ml_anomalies(wave: str = Query("1", description="Wave number (1-5)")):
    """Per-step ETL anomaly scores for a given wave."""
    if _provider:
        return _provider.get_anomalies(wave)
    anomalies = ETL_ANOMALIES.get(wave, [])
    steps = []
    for step_name, baseline in ETL_STEP_BASELINES.items():
        match = next((a for a in anomalies if a["step"] == step_name), None)
        steps.append(match if match else {
            "step": step_name, **baseline, "flagged": False, "explanation": None,
        })
    return {"wave": wave, "total_anomalies": len(anomalies), "steps": steps}


@router.get("/classifications")
async def ml_classifications():
    """Per-account ML classification scores."""
    if _provider:
        return _provider.get_classifications()
    return {"classifications": ACCOUNT_ML, "summary": ML_SUMMARY}

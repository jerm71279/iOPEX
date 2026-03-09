"""ML model status, ETL anomaly scores, and NHI classification endpoints.

Uses LiveMLProvider for real model inference instead of hardcoded dicts.
"""

from fastapi import APIRouter, Query
from backend.ml_provider import LiveMLProvider

router = APIRouter()

# Singleton — seeded, trained, and ready at import time
_provider = LiveMLProvider()


@router.get("/status")
async def ml_status():
    """ML model states — ETL anomaly detector + NHI classifier (live)."""
    return _provider.get_status()


@router.get("/anomalies")
async def ml_anomalies(wave: str = Query("1", description="Wave number (1-5)")):
    """Per-step ETL anomaly scores for a given wave (computed by real models)."""
    return _provider.get_anomalies(wave)


@router.get("/classifications")
async def ml_classifications():
    """Per-account ML classification scores (live LightGBM inference)."""
    return _provider.get_classifications()

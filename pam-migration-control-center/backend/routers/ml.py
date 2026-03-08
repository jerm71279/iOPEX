"""ML model status, ETL anomaly scores, and NHI classification endpoints."""

from fastapi import APIRouter, Query
from backend.mock_data.ml_data import (
    ML_STATUS,
    ETL_ANOMALIES,
    ETL_STEP_BASELINES,
    ACCOUNT_ML,
    ML_SUMMARY,
)

router = APIRouter()


@router.get("/status")
async def ml_status():
    """ML model states — ETL anomaly detector + NHI classifier."""
    return ML_STATUS


@router.get("/anomalies")
async def ml_anomalies(wave: str = Query("1", description="Wave number (1-5)")):
    """Per-step ETL anomaly scores for a given wave."""
    anomalies = ETL_ANOMALIES.get(wave, [])
    flagged_steps = {a["step"] for a in anomalies}
    steps = []
    for step_name, baseline in ETL_STEP_BASELINES.items():
        match = next((a for a in anomalies if a["step"] == step_name), None)
        if match:
            steps.append(match)
        else:
            steps.append({
                "step": step_name,
                "ewma_z": baseline["ewma_z"],
                "if_score": baseline["if_score"],
                "blended": baseline["blended"],
                "flagged": False,
                "explanation": None,
            })
    return {
        "wave": wave,
        "total_anomalies": len(anomalies),
        "steps": steps,
    }


@router.get("/classifications")
async def ml_classifications():
    """Per-account ML classification scores."""
    return {
        "classifications": ACCOUNT_ML,
        "summary": ML_SUMMARY,
    }

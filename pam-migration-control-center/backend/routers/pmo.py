"""
PMO Intelligence Router — Mock Implementation
Matches shift_pmo_router.py endpoint signatures exactly.
No ChromaDB required — returns mock data from pmo_data.py.
Swap in the real RAG engine by replacing this file with shift_pmo_router.py
and adding shift_pmo_rag_engine.py.
"""
import uuid
from datetime import datetime, timezone
from typing import Optional, Literal
from fastapi import APIRouter
from pydantic import BaseModel, Field
from backend.mock_data.pmo_data import (
    PMO_EXECUTIVE_SUMMARY, PMO_GATE_PIPELINE, PMO_TEAM_ACCOUNTABILITY,
    PMO_CHECKPOINT_HISTORY, PMO_WEEK_OVER_WEEK, PMO_CORPUS_STATS, PMO_CANNED_ANSWERS,
    CURRENT_PHASE, CURRENT_WEEK,
)

router = APIRouter(tags=["PMO Intelligence"])


# ---------------------------------------------------------------------------
# Health & Corpus
# ---------------------------------------------------------------------------

@router.get("/health")
async def pmo_health():
    return {
        "status": "healthy",
        "mode": "mock",
        "layer": "PMO Intelligence (Layer 0)",
        "total_indexed": PMO_CORPUS_STATS["total_indexed"],
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@router.get("/corpus/stats")
async def pmo_corpus_stats():
    return {
        "trace_id": str(uuid.uuid4()),
        **PMO_CORPUS_STATS,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


# ---------------------------------------------------------------------------
# Metrics panels
# ---------------------------------------------------------------------------

@router.get("/metrics/executive-summary")
async def pmo_executive_summary(phase: str = "P2"):
    data = PMO_EXECUTIVE_SUMMARY.get(phase.upper(), PMO_EXECUTIVE_SUMMARY["P2"])
    return {
        "trace_id": str(uuid.uuid4()),
        "panel": "executive_summary",
        "phase": phase,
        **data,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@router.get("/metrics/gate-pipeline")
async def pmo_gate_pipeline(phase: Optional[str] = None):
    key = phase.upper() if phase else "P2"
    data = PMO_GATE_PIPELINE.get(key, PMO_GATE_PIPELINE["P2"])
    return {
        "trace_id": str(uuid.uuid4()),
        "panel": "gate_pipeline",
        **data,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@router.get("/metrics/team-accountability")
async def pmo_team_accountability(weeks: int = 4):
    return {
        "trace_id": str(uuid.uuid4()),
        "panel": "team_accountability",
        **PMO_TEAM_ACCOUNTABILITY,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@router.get("/metrics/checkpoint-history")
async def pmo_checkpoint_history(phase: Optional[str] = None):
    resolved_phase = phase or CURRENT_PHASE
    data = PMO_CHECKPOINT_HISTORY.get(
        resolved_phase.upper(),
        PMO_CHECKPOINT_HISTORY[CURRENT_PHASE],
    )
    return {
        "trace_id": str(uuid.uuid4()),
        "panel": "checkpoint_history",
        "phase": resolved_phase,
        **data,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@router.get("/metrics/week-over-week")
async def pmo_week_over_week(current_week: int = 14, lookback: int = 3):
    return {
        "trace_id": str(uuid.uuid4()),
        "panel": "week_over_week",
        "trend": PMO_WEEK_OVER_WEEK[-(lookback + 1):],
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


# ---------------------------------------------------------------------------
# RAG Query
# ---------------------------------------------------------------------------

@router.post("/query")
async def pmo_query(request: dict):
    question = request.get("question", "")
    question_lower = question.lower()

    matched_answer = None
    for entry in PMO_CANNED_ANSWERS:
        if any(kw in question_lower for kw in entry["keywords"]):
            matched_answer = entry["answer"]
            break

    if matched_answer is None:
        # Default fallback answer
        matched_answer = (
            "Based on current PMO intelligence, the migration is progressing on schedule. "
            "Please consult the executive summary or gate pipeline panels for detailed status."
        )

    return {
        "trace_id": str(uuid.uuid4()),
        "question": question,
        "answer": matched_answer,
        "citations": [
            "mock_doc_" + str(uuid.uuid4())[:8],
            "mock_doc_" + str(uuid.uuid4())[:8],
        ],
        "sources_used": 3,
        "audience": request.get("audience", "executive"),
        "retrieved_count": 8,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


# ---------------------------------------------------------------------------
# Ingest endpoints (mock acknowledgment only)
# ---------------------------------------------------------------------------

_MOCK_INGEST_RESPONSE = {
    "status": "queued_mock",
    "mode": "mock",
    "note": (
        "Mock mode: ingestion acknowledged but not persisted. "
        "Enable real RAG engine to index events."
    ),
}


@router.post("/ingest/directive")
async def pmo_ingest_directive(request: dict):
    return {"trace_id": str(uuid.uuid4()), **_MOCK_INGEST_RESPONSE}


@router.post("/ingest/execution-result")
async def pmo_ingest_execution_result(request: dict):
    return {"trace_id": str(uuid.uuid4()), **_MOCK_INGEST_RESPONSE}


@router.post("/ingest/gate-event")
async def pmo_ingest_gate_event(request: dict):
    return {"trace_id": str(uuid.uuid4()), **_MOCK_INGEST_RESPONSE}


@router.post("/ingest/checkpoint")
async def pmo_ingest_checkpoint(request: dict):
    return {"trace_id": str(uuid.uuid4()), **_MOCK_INGEST_RESPONSE}

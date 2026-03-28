"""
Yellow Checkpoints API — cross-phase AI contextual awareness layer.

API stubs structured for real orchestrator connections. Endpoints match what
the real coordinator + agents would call. Currently backed by in-memory mock
data, but the contract is production-ready for drop-in replacement.

ServiceNow INC tickets are created for each yellow; escalation to RED
upgrades INC → CHG.
"""
from datetime import datetime, timezone
from typing import Optional
from fastapi import APIRouter, Request
from backend.mock_data.data import YELLOW_CHECKPOINTS

router = APIRouter()

# ── Accumulation thresholds (per-phase) ──────────────────────────────
THRESHOLDS = {"proceed": 2, "notify_lead": 4}  # 5+ = auto-promote armed


@router.get("")
async def list_checkpoints(option: str = "a", phase: str = None, type: str = None, status: str = None):
    """List all yellow checkpoints, optionally filtered."""
    results = [c for c in YELLOW_CHECKPOINTS if c.get("option", "both") in ("both", option)]
    if phase:
        results = [c for c in results if c["phase"] == phase]
    if type:
        results = [c for c in results if c["type"] == type.upper()]
    if status:
        results = [c for c in results if c["status"] == status]
    return results


@router.get("/stats")
async def checkpoint_stats(option: str = "a"):
    """Summary counts for dashboard panels."""
    cps = [c for c in YELLOW_CHECKPOINTS if c.get("option", "both") in ("both", option)]
    total = len(cps)
    by_status = {}
    by_type = {}
    by_phase = {}
    for c in cps:
        by_status[c["status"]] = by_status.get(c["status"], 0) + 1
        by_type[c["type"]] = by_type.get(c["type"], 0) + 1
        by_phase[c["phase"]] = by_phase.get(c["phase"], 0) + 1

    # Per-phase accumulation with threshold status
    accumulation = []
    for phase_id in ["p0", "p1", "p2", "p3", "p4", "p5", "p6", "p7"]:
        count = by_phase.get(phase_id, 0)
        if count == 0:
            level = "clear"
        elif count <= THRESHOLDS["proceed"]:
            level = "proceed"
        elif count <= THRESHOLDS["notify_lead"]:
            level = "notify_lead"
        else:
            level = "auto_promote_armed"
        accumulation.append({"phase": phase_id, "count": count, "level": level})

    return {
        "total": total,
        "resolved": by_status.get("resolved", 0),
        "open": by_status.get("fired", 0) + by_status.get("notified", 0) + by_status.get("snoozed", 0),
        "escalated": by_status.get("escalated", 0),
        "by_status": by_status,
        "by_type": by_type,
        "by_phase": by_phase,
        "accumulation": accumulation,
    }


@router.get("/{checkpoint_id}")
async def get_checkpoint(checkpoint_id: str):
    """Single checkpoint detail with full AI rationale."""
    cp = next((c for c in YELLOW_CHECKPOINTS if c["id"] == checkpoint_id), None)
    if not cp:
        return {"error": f"Checkpoint {checkpoint_id} not found"}
    return cp


@router.post("/{checkpoint_id}/resolve")
async def resolve_checkpoint(checkpoint_id: str, resolution_note: str = "Resolved via Control Center", resolved_by: str = "Control Center User"):
    """Mark checkpoint resolved. In production: closes ServiceNow INC ticket."""
    cp = next((c for c in YELLOW_CHECKPOINTS if c["id"] == checkpoint_id), None)
    if not cp:
        return {"error": f"Checkpoint {checkpoint_id} not found"}
    cp["status"] = "resolved"
    cp["resolved_at"] = datetime.now(timezone.utc).isoformat()
    cp["resolved_by"] = resolved_by
    cp["resolution_note"] = resolution_note
    return {"status": "resolved", "checkpoint": cp, "snow_action": f"INC {cp['snow_ticket']} closed"}


@router.post("/{checkpoint_id}/escalate")
async def escalate_checkpoint(checkpoint_id: str):
    """Promote to RED. In production: upgrades SNOW INC → CHG, triggers gate block."""
    cp = next((c for c in YELLOW_CHECKPOINTS if c["id"] == checkpoint_id), None)
    if not cp:
        return {"error": f"Checkpoint {checkpoint_id} not found"}
    old_ticket = cp["snow_ticket"]
    cp["status"] = "escalated"
    cp["resolved_at"] = datetime.now(timezone.utc).isoformat()
    cp["snow_ticket"] = f"{old_ticket} → CHG{datetime.now().strftime('%07d')}"
    cp["resolution_note"] = "ESCALATED TO RED — pipeline halted"
    return {
        "status": "escalated",
        "checkpoint": cp,
        "snow_action": f"INC {old_ticket} upgraded to CHG",
        "gate_blocked": True,
    }


@router.post("/{checkpoint_id}/snooze")
async def snooze_checkpoint(checkpoint_id: str):
    """Snooze once — resets SLA window. In production: adds SNOW work note."""
    cp = next((c for c in YELLOW_CHECKPOINTS if c["id"] == checkpoint_id), None)
    if not cp:
        return {"error": f"Checkpoint {checkpoint_id} not found"}
    if cp.get("snoozed_once"):
        return {"error": "Cannot snooze twice — second expiry cannot be snoozed"}
    cp["status"] = "snoozed"
    cp["snoozed_once"] = True
    return {
        "status": "snoozed",
        "checkpoint": cp,
        "snow_action": f"Work note added to {cp['snow_ticket']}",
        "new_sla_window": f"{cp['sla_hours']}hr reset",
    }


@router.post("/fire")
async def fire_checkpoint(request: Request):
    """
    Stub: fire a new yellow checkpoint.
    In production, agents call this when they detect an ambiguous condition.
    Flow: create SNOW INC -> log to SIEM -> classify type -> send notification -> start SLA window.
    Accepts JSON body with phase, agent, type, condition, and optional ai_rationale.
    """
    body = {}
    try:
        body = await request.json()
    except Exception:
        pass

    phase = body.get("phase", "p1")
    agent = body.get("agent", "01")
    cp_type = body.get("type", "OPERATIONAL").upper()
    condition = body.get("condition", "Manual checkpoint fired via API")
    rationale = body.get("ai_rationale", None)

    new_id = f"yc-{len(YELLOW_CHECKPOINTS) + 1:03d}"
    ticket = f"INC{(12345 + len(YELLOW_CHECKPOINTS)):07d}"
    sla_map = {"OPERATIONAL": 24, "SECURITY": 2, "COMPLIANCE": 48, "EDGE_CASE": 24}

    if not rationale:
        rationale = {
            "what_fired": condition,
            "root_cause": "Pending AI analysis",
            "cross_system_context": "Pending cross-phase correlation",
            "risk_assessment": f"{cp_type} — Pending risk evaluation",
            "recommended_action": "Awaiting agent reasoning",
        }

    opt = body.get("option", "a")

    checkpoint = {
        "id": new_id,
        "phase": phase,
        "agent": agent,
        "type": cp_type,
        "source": "ai_detected",
        "option": opt,
        "status": "fired",
        "fired_at": datetime.now(timezone.utc).isoformat(),
        "resolved_at": None,
        "sla_hours": sla_map.get(cp_type, 24),
        "snow_ticket": ticket,
        "condition": condition,
        "ai_rationale": rationale,
        "resolved_by": None,
        "resolution_note": None,
    }
    YELLOW_CHECKPOINTS.append(checkpoint)
    return {
        "status": "fired",
        "checkpoint": checkpoint,
        "snow_action": f"Created {ticket}",
        "sla_window": f"{checkpoint['sla_hours']}hr",
    }


@router.post("/reset")
async def reset_checkpoints():
    """Reset all checkpoints to initial demo state."""
    from backend.mock_data.data import YELLOW_CHECKPOINTS as orig
    # Reload from module — clear any mutations
    import importlib
    import backend.mock_data.data as data_module
    importlib.reload(data_module)
    YELLOW_CHECKPOINTS.clear()
    YELLOW_CHECKPOINTS.extend(data_module.YELLOW_CHECKPOINTS)
    return {"status": "reset", "count": len(YELLOW_CHECKPOINTS)}

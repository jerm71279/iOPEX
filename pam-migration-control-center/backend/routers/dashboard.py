from fastapi import APIRouter
from backend.mock_data.data import PHASES, AGENTS, WAVES, GATES, OPTIONS

router = APIRouter()


@router.get("/stats")
async def get_stats(option: str = "a"):
    opt = OPTIONS.get(option, OPTIONS["a"])
    total_accounts = 2847
    agents_complete = sum(1 for a in AGENTS.values() if a["status"] == "complete")
    agents_active = sum(1 for a in AGENTS.values() if a["status"] == "active")
    gates_passed = sum(1 for g in GATES if g["status"] == "passed")
    current_phase = next(
        (p for p in PHASES.values() if any(
            AGENTS.get(str(a), AGENTS.get(a, {})).get("status") == "active"
            for a in p["agents"]
        )),
        PHASES["p7"],
    )
    weeks_key = "weeks_b" if option == "b" else "weeks"
    return {
        "option": option,
        "option_name": opt["short"],
        "target": opt["target"],
        "total_weeks": 50 if option == "b" else 80,
        "total_accounts": total_accounts,
        "nhi_accounts": 412,
        "integrations": 89,
        "total_waves": len(WAVES),
        "total_gates": len(GATES),
        "gates_passed": gates_passed,
        "total_agents": len(AGENTS),
        "agents_complete": agents_complete,
        "agents_active": agents_active,
        "current_phase": {
            "id": current_phase["id"],
            "name": current_phase["name"],
            "weeks": current_phase.get(weeks_key, current_phase["weeks"]),
        },
    }


@router.get("/risks")
async def get_risks(option: str = "a"):
    risks = {
        "critical": {"count": 34, "label": "NHI + CCP/AAM", "desc": "Active application dependencies requiring code changes"},
        "high": {"count": 89, "label": "NHI (no CCP)", "desc": "Service accounts requiring rotation policy migration"},
        "medium": {"count": 178, "label": "Infrastructure", "desc": "Domain admins, DB service accounts, network devices"},
        "low": {"count": 2546, "label": "Standard", "desc": "Human accounts, test/dev, standard credentials"},
    }
    if option == "a":
        risks["high"]["count"] = 101
        risks["high"]["desc"] += " + permission model loss risk (22→4)"
    return risks


@router.get("/timeline")
async def get_timeline(option: str = "a"):
    return [
        {
            "id": p["id"],
            "name": p["name"],
            "weeks": p.get("weeks_b", p["weeks"]) if option == "b" else p["weeks"],
            "week_start": p.get("week_start_b", p["week_start"]) if option == "b" else p["week_start"],
            "week_end": p.get("week_end_b", p["week_end"]) if option == "b" else p["week_end"],
            "risk": p["risk"],
            "color": p["color"],
            "status": _phase_status(p),
        }
        for p in PHASES.values()
    ]


def _phase_status(phase):
    if not phase["agents"]:
        return "complete"
    statuses = [
        AGENTS.get(str(a), AGENTS.get(a, {})).get("status", "pending")
        for a in phase["agents"]
    ]
    if all(s == "complete" for s in statuses):
        return "complete"
    if any(s in ("active", "complete") for s in statuses):
        return "active"
    return "pending"

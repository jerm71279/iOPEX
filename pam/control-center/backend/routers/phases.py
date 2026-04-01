from fastapi import APIRouter
from backend.mock_data.data import PHASES, AGENTS, DELIVERABLES

router = APIRouter()


def _build_deliverables(phase_id):
    """Return deliverables with keys from DELIVERABLES data so frontend can drill down."""
    phase_data = DELIVERABLES.get(phase_id, {})
    return [
        {"key": key, "label": d["name"], "agent": d["agent"], "has_data": bool(d.get("data"))}
        for key, d in phase_data.items()
    ]


@router.get("")
async def list_phases(option: str = "a"):
    result = []
    for p in PHASES.values():
        activities = list(p["activities"].get("both", []))
        activities.extend(p["activities"].get(option, []))
        agent_details = []
        for aid in p["agents"]:
            agent = AGENTS.get(str(aid), {})
            if agent:
                agent_details.append({
                    "num": agent["num"],
                    "name": agent["name"],
                    "status": agent["status"],
                    "weeks": agent.get("weeks_b", agent["weeks"]) if option == "b" else agent["weeks"],
                })
        result.append({
            "id": p["id"],
            "name": p["name"],
            "weeks": p.get("weeks_b", p["weeks"]) if option == "b" else p["weeks"],
            "week_start": p.get("week_start_b", p["week_start"]) if option == "b" else p["week_start"],
            "week_end": p.get("week_end_b", p["week_end"]) if option == "b" else p["week_end"],
            "risk": p["risk"],
            "color": p["color"],
            "summary": p["summary"],
            "activities": activities,
            "deliverables": _build_deliverables(p["id"]),
            "agents": agent_details,
            "gates": p["gates"],
        })
    return result


@router.get("/{phase_id}")
async def get_phase(phase_id: str, option: str = "a"):
    p = PHASES.get(phase_id)
    if not p:
        return {"error": f"Phase {phase_id} not found"}
    activities = list(p["activities"].get("both", []))
    activities.extend(p["activities"].get(option, []))
    agent_details = []
    for aid in p["agents"]:
        agent = AGENTS.get(str(aid), {})
        if agent:
            agent_details.append({
                "num": agent["num"],
                "name": agent["name"],
                "status": agent["status"],
                "weeks": agent.get("weeks_b", agent["weeks"]) if option == "b" else agent["weeks"],
                "desc": agent["desc"],
            })
    base = {k: v for k, v in p.items() if k not in ("activities", "deliverables")}
    if option == "b":
        base["weeks"] = p.get("weeks_b", p["weeks"])
        base["week_start"] = p.get("week_start_b", p["week_start"])
        base["week_end"] = p.get("week_end_b", p["week_end"])
    return {
        **base,
        "activities": activities,
        "deliverables": _build_deliverables(phase_id),
        "agents": agent_details,
    }

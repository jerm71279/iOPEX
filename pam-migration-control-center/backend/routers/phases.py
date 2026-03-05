from fastapi import APIRouter
from backend.mock_data.data import PHASES, AGENTS

router = APIRouter()


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
                    "weeks": agent["weeks"],
                })
        result.append({
            "id": p["id"],
            "name": p["name"],
            "weeks": p["weeks"],
            "week_start": p["week_start"],
            "week_end": p["week_end"],
            "risk": p["risk"],
            "color": p["color"],
            "summary": p["summary"],
            "activities": activities,
            "deliverables": p["deliverables"],
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
                "weeks": agent["weeks"],
                "desc": agent["desc"],
            })
    return {
        **{k: v for k, v in p.items() if k != "activities"},
        "activities": activities,
        "agents": agent_details,
    }

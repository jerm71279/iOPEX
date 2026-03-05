from fastapi import APIRouter
from backend.mock_data.data import AGENTS, DELIVERABLES

router = APIRouter()


@router.get("")
async def list_agents(option: str = "a"):
    return [
        {
            "id": aid,
            "num": a["num"],
            "name": a["name"],
            "phases": a["phases"],
            "weeks": a.get("weeks_b", a["weeks"]) if option == "b" else a["weeks"],
            "status": a["status"],
            "desc": a["desc"],
            "blocked_by": a.get("blocked_by", []),
        }
        for aid, a in AGENTS.items()
    ]


@router.get("/{agent_id}")
async def get_agent(agent_id: str, option: str = "a"):
    a = AGENTS.get(agent_id)
    if not a:
        return {"error": f"Agent {agent_id} not found"}
    result = {"id": agent_id, **a}
    if option == "b":
        result["weeks"] = a.get("weeks_b", a["weeks"])
    return result


@router.get("/{agent_id}/output")
async def get_agent_output(agent_id: str):
    """Return sample agent output in the real format for drill-down."""
    a = AGENTS.get(agent_id)
    if not a:
        return {"error": f"Agent {agent_id} not found"}
    agent_num = a["num"]
    # Find deliverables produced by this agent
    outputs = []
    for phase_id, phase_delivs in DELIVERABLES.items():
        for key, deliv in phase_delivs.items():
            if deliv.get("agent") == agent_num:
                outputs.append({
                    "phase": phase_id,
                    "key": key,
                    "name": deliv["name"],
                    "format": deliv["format"],
                    "data": deliv["data"],
                })
    if not outputs:
        return {
            "agent_id": agent_id,
            "agent_name": a["name"],
            "status": a["status"],
            "message": f"No output available yet — Agent {agent_num} status: {a['status']}",
        }
    return {
        "agent_id": agent_id,
        "agent_name": a["name"],
        "outputs": outputs,
    }

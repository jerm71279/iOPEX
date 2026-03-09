from fastapi import APIRouter
from backend.mock_data.data import GATES
from backend.state import state

router = APIRouter()


@router.get("")
async def list_gates(option: str = "a"):
    return [
        {**g, "week": g.get("week_b", g["week"]) if option == "b" else g["week"]}
        for g in GATES
    ]


@router.get("/{gate_id}")
async def get_gate(gate_id: str, option: str = "a"):
    gate = next((g for g in GATES if g["id"] == gate_id), None)
    if not gate:
        return {"error": f"Gate {gate_id} not found"}
    return {**gate, "week": gate.get("week_b", gate["week"]) if option == "b" else gate["week"]}


@router.post("/{gate_id}/approve")
async def approve_gate(gate_id: str):
    """Approve gate — triggers cascading agent/phase activation via state manager."""
    result = state.approve_gate(gate_id)
    return result


@router.post("/reset")
async def reset_gates():
    """Reset all state (agents, waves, gates) to mid-migration snapshot."""
    state.reset()
    return {"status": "reset", "snapshot": state.snapshot()}

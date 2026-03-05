from fastapi import APIRouter
from backend.mock_data.data import GATES

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
    """Simulate gate approval — advances gate to 'passed' and activates next gate."""
    gate = next((g for g in GATES if g["id"] == gate_id), None)
    if not gate:
        return {"error": f"Gate {gate_id} not found"}
    if gate["status"] == "passed":
        return {"status": "already_passed", "gate": gate}
    gate["status"] = "passed"
    # Activate next pending gate
    gate_idx = GATES.index(gate)
    if gate_idx + 1 < len(GATES):
        next_gate = GATES[gate_idx + 1]
        if next_gate["status"] == "pending":
            next_gate["status"] = "active"
    return {
        "status": "approved",
        "gate": gate,
        "next_gate": GATES[gate_idx + 1]["id"] if gate_idx + 1 < len(GATES) else None,
    }


@router.post("/reset")
async def reset_gates():
    """Reset all gates to their initial state."""
    initial_states = {
        "g1": "passed", "g2": "passed", "g3": "passed", "g4": "active", "g15": "passed",
    }
    for gate in GATES:
        gate["status"] = initial_states.get(gate["id"], "pending")
    return {"status": "reset", "gates": len(GATES)}

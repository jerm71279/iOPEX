"""State control router — reset, advance, snapshot for demo orchestration."""

from fastapi import APIRouter
from backend.state import state

router = APIRouter()


@router.get("/snapshot")
async def get_snapshot():
    """Full state dump for debugging."""
    return state.snapshot()


@router.post("/reset")
async def reset_state():
    """Reset to mid-migration snapshot."""
    state.reset()
    return {"status": "reset", "snapshot": state.snapshot()}


@router.post("/advance-agent/{agent_id}")
async def advance_agent(agent_id: str, status: str = "complete"):
    """Manually advance an agent's status."""
    return state.advance_agent(agent_id, status)


@router.post("/advance-wave/{wave_id}")
async def advance_wave(wave_id: str, status: str = "complete"):
    """Manually advance a wave's status."""
    return state.advance_wave(wave_id, status)

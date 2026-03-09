import asyncio
from fastapi import APIRouter
from backend.mock_data.data import WAVES, AGENTS
from backend.state import state

router = APIRouter()


@router.get("")
async def list_waves(option: str = "a"):
    result = []
    for wid, w in WAVES.items():
        steps_key = "etl_steps_a" if option == "a" else "etl_steps_b"
        agent_details = []
        for aid in w["agents"]:
            agent = AGENTS.get(str(aid), {})
            if agent:
                agent_details.append({"num": agent["num"], "name": agent["name"]})
        result.append({
            "id": wid,
            "name": w["name"],
            "risk": w["risk"],
            "type": w["type"],
            "account_pct": w["account_pct"],
            "account_count": w["account_count"],
            "weeks": w.get("weeks_b", w["weeks"]) if option == "b" else w["weeks"],
            "description": w["description"],
            "gate": w["gate"],
            "status": state.get_wave_status(wid),
            "etl_steps": w.get(steps_key, w.get("etl_steps_a")),
            "agents": agent_details,
        })
    return result


@router.get("/{wave_id}")
async def get_wave(wave_id: str, option: str = "a"):
    w = WAVES.get(wave_id)
    if not w:
        return {"error": f"Wave {wave_id} not found"}
    steps_key = "etl_steps_a" if option == "a" else "etl_steps_b"
    return {
        "id": wave_id,
        **{k: v for k, v in w.items() if k not in ("etl_steps_a", "etl_steps_b")},
        "etl_steps": w.get(steps_key, w.get("etl_steps_a")),
    }


@router.post("/{wave_id}/simulate")
async def simulate_wave(wave_id: str, option: str = "a"):
    """Simulate ETL pipeline execution. Returns step-by-step results."""
    w = WAVES.get(wave_id)
    if not w:
        return {"error": f"Wave {wave_id} not found"}
    steps_key = "etl_steps_a" if option == "a" else "etl_steps_b"
    steps = w.get(steps_key, w.get("etl_steps_a"))
    count = w["account_count"]
    sim_steps = []
    for i, step in enumerate(steps):
        duration = [1200, 8500, 450, 2100, 15600, 45000, 980, 500][i % 8]
        success = count if step != "EXPORT" else count - 2
        sim_steps.append({
            "step": step,
            "status": "done",
            "duration_ms": duration,
            "detail": _step_detail(step, count, success, option),
        })
    return {
        "wave": int(wave_id),
        "status": "simulated",
        "total_accounts": count,
        "migrated": count - 2,
        "failed": 2,
        "steps": sim_steps,
    }


def _step_detail(step, count, success, option):
    details = {
        "FREEZE": f"{count} accounts frozen — CPM management disabled",
        "EXPORT": f"{success} passwords retrieved, {count - success} failed (locked)",
        "TRANSFORM": f"{success} accounts transformed to target format",
        "CREATE FOLDERS": f"Folders created in Secret Server /Imported/ hierarchy",
        "CREATE SAFES": f"Safes created in Privilege Cloud (matching source names)",
        "IMPORT": f"{success} secrets created in target",
        "HEARTBEAT": f"{success - 1}/{success} heartbeat verified ({(success-1)/success*100:.1f}%)",
        "UNFREEZE": f"{count} accounts unfrozen — CPM management re-enabled",
        "RECODE INTEGRATIONS": f"CCP/AAM integration code updated for target API",
        "UPDATE ENDPOINTS": f"CCP/AAM endpoint URLs updated for Privilege Cloud",
    }
    return details.get(step, f"{step} completed")

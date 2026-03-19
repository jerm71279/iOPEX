import asyncio
from fastapi import APIRouter
from backend.mock_data.data import WAVES, AGENTS
from backend.state import state

router = APIRouter()


@router.get("")
async def list_waves(option: str = "a"):
    result = []
    for wid, w in WAVES.items():
        steps_key = "etl_steps_a" if option == "a" else ("etl_steps_b" if option == "b" else "etl_steps_c")
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
            "weeks": w.get("weeks_c", w["weeks"]) if option == "c" else (w.get("weeks_b", w["weeks"]) if option == "b" else w["weeks"]),
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
    steps_key = "etl_steps_a" if option == "a" else ("etl_steps_b" if option == "b" else "etl_steps_c")
    return {
        "id": wave_id,
        **{k: v for k, v in w.items() if k not in ("etl_steps_a", "etl_steps_b", "etl_steps_c")},
        "etl_steps": w.get(steps_key, w.get("etl_steps_a")),
    }


@router.post("/{wave_id}/simulate")
async def simulate_wave(wave_id: str, option: str = "a"):
    """Simulate ETL pipeline execution. Returns step-by-step results."""
    w = WAVES.get(wave_id)
    if not w:
        return {"error": f"Wave {wave_id} not found"}
    steps_key = "etl_steps_a" if option == "a" else ("etl_steps_b" if option == "b" else "etl_steps_c")
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
    if option == "b":
        details = {
            "FREEZE": f"{count} accounts frozen in CyberArk — Keeper import session initiated",
            "EXPORT": f"{success} passwords retrieved, {count - success} failed (locked)",
            "TRANSFORM": f"{success} accounts mapped to pamUser/pamResource 3-tier hierarchy",
            "BUILD HIERARCHY": f"PAM Config → Shared Folder structure created in Keeper Vault",
            "BULK IMPORT": f"{success} records bulk-imported via cyberark-import tool",
            "POST-IMPORT TRANSFORM": f"{success} flat records restructured into pamUser/pamMachine/pamDatabase",
            "RECODE INTEGRATIONS": f"KSM SDK replaces CCP/AAM — {success} integration code packages generated",
            "HEARTBEAT": f"{success - 1}/{success} Keeper secrets verified via Gateway rotation check",
            "INTEGRITY": f"Agent 18: 12 IC checks passed — Keeper 3-tier hierarchy schema confirmed",
            "UNFREEZE": f"{count} accounts unfrozen — CPM management re-enabled in source",
        }
    elif option == "c":
        details = {
            "FREEZE": f"{count} accounts frozen in CyberArk — MiniOrange import session initiated",
            "EXPORT": f"{success} passwords retrieved, {count - success} failed (locked)",
            "TRANSFORM": f"{success} accounts mapped to MiniOrange Resource Group format",
            "CREATE RESOURCE GROUPS": f"Resource Groups created in MiniOrange vault (matching CyberArk Safe names)",
            "UPDATE ENDPOINTS": f"REST API endpoints updated to MiniOrange — {success} integration configs patched",
            "IMPORT": f"{success} credentials created in MiniOrange target vault",
            "HEARTBEAT": f"{success - 1}/{success} MiniOrange credentials verified via agent check ({(success-1)/success*100:.1f}%)",
            "UNFREEZE": f"{count} accounts unfrozen — CPM management re-enabled",
        }
    else:  # option == "a" — Devolutions
        details = {
            "FREEZE": f"{count} accounts frozen in CyberArk — Devolutions import session initiated",
            "EXPORT": f"{success} passwords retrieved, {count - success} failed (locked)",
            "TRANSFORM": f"{success} accounts transformed to Devolutions Entry format",
            "CREATE VAULTS": f"Vaults created in Devolutions Server (matching CyberArk Safe names)",
            "RECODE INTEGRATIONS": f"Devolutions REST replaces CCP/AAM — {success} integration scripts regenerated",
            "IMPORT": f"{success} credential entries created in Devolutions Server",
            "HEARTBEAT": f"{success - 1}/{success} Devolutions entries verified via RDM Agent check ({(success-1)/success*100:.1f}%)",
            "INTEGRITY": f"Agent 18: 12 IC checks passed — Devolutions vault schema confirmed (read-only session)",
            "UNFREEZE": f"{count} accounts unfrozen — CPM management re-enabled",
        }
    return details.get(step, f"{step} completed")

from fastapi import APIRouter
from backend.mock_data.data import DELIVERABLES, COMPARISON_ROWS, PERMISSION_MAPPING, PLATFORM_TEMPLATE_MAP

router = APIRouter()


@router.get("/compare/options")
async def get_comparison():
    return {
        "rows": COMPARISON_ROWS,
        "permission_mapping": PERMISSION_MAPPING,
        "platform_template_map": PLATFORM_TEMPLATE_MAP,
    }


@router.get("/{phase_id}")
async def list_deliverables(phase_id: str):
    phase_delivs = DELIVERABLES.get(phase_id, {})
    return [
        {
            "key": key,
            "name": d["name"],
            "agent": d["agent"],
            "format": d["format"],
            "has_data": bool(d.get("data")),
        }
        for key, d in phase_delivs.items()
    ]


@router.get("/{phase_id}/{deliverable_key}")
async def get_deliverable(phase_id: str, deliverable_key: str):
    phase_delivs = DELIVERABLES.get(phase_id, {})
    d = phase_delivs.get(deliverable_key)
    if not d:
        return {"error": f"Deliverable {deliverable_key} not found in phase {phase_id}"}
    return d

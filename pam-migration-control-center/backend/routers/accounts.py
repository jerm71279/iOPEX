"""
Account Explorer endpoints — list, group, detail, migration-flow.
"""
from collections import defaultdict
from fastapi import APIRouter
from backend.mock_data.accounts_data import ACCOUNTS, WAVE_META, ETL_STEPS

router = APIRouter()

SUMMARY_FIELDS = (
    "id", "name", "userName", "department", "role", "wave", "batch",
    "risk", "status", "is_nhi", "nhi_type", "platformId", "pipeline_step",
    "pipeline_progress",
)


@router.get("")
async def list_accounts(
    option: str = "a",
    wave: int | None = None,
    department: str | None = None,
    role: str | None = None,
    nhi_type: str | None = None,
    risk: str | None = None,
    status: str | None = None,
    search: str | None = None,
):
    """Filtered account list (summary fields only)."""
    results = []
    for a in ACCOUNTS:
        if wave is not None and a["wave"] != wave:
            continue
        if department and a["department"] != department:
            continue
        if role and a["role"] != role:
            continue
        if nhi_type and a.get("nhi_type") != nhi_type:
            continue
        if risk and a["risk"] != risk:
            continue
        if status and a["status"] != status:
            continue
        if search:
            q = search.lower()
            if q not in a["name"].lower() and q not in a["userName"].lower():
                continue
        results.append({k: a[k] for k in SUMMARY_FIELDS})
    return results


@router.get("/groups")
async def account_groups(
    option: str = "a",
    group_by: str = "department",
):
    """Aggregate accounts into groups by a chosen attribute."""
    buckets: dict[str, dict] = defaultdict(lambda: {"count": 0, "nhi_count": 0, "high_risk": 0})
    for a in ACCOUNTS:
        key = _group_key(a, group_by)
        b = buckets[key]
        b["count"] += 1
        if a["is_nhi"]:
            b["nhi_count"] += 1
        if a["risk"] in ("high", "critical"):
            b["high_risk"] += 1
    groups = [{"key": k, **v} for k, v in sorted(buckets.items())]
    return {"groups": groups}


@router.get("/migration-flow")
async def migration_flow(option: str = "a", batch_by: str = "wave"):
    """Batching flow summary — accounts grouped and run through 7-step ETL."""
    # Group accounts by the chosen attribute
    lanes: dict[str, list] = defaultdict(list)
    for a in ACCOUNTS:
        key = _group_key(a, batch_by)
        lanes[key].append(a)

    waves = []
    for lane_key, accts in sorted(lanes.items()):
        # Chunk into batches of 500 (all our mock data fits in one batch per group)
        batches = []
        batch_size = 500
        for i in range(0, len(accts), batch_size):
            chunk = accts[i : i + batch_size]
            batch_id = f"{lane_key}B{i // batch_size}" if batch_by != "wave" else f"W{chunk[0]['wave']}B{i // batch_size}"
            status_bd = defaultdict(int)
            pipeline_counts = {s: 0 for s in ETL_STEPS}
            for c in chunk:
                status_bd[c["status"]] += 1
                for j, step in enumerate(ETL_STEPS):
                    if c["pipeline_progress"] > j:
                        pipeline_counts[step] += 1
            batches.append({
                "batch_id": batch_id,
                "count": len(chunk),
                "status_breakdown": dict(status_bd),
                "pipeline_progress": pipeline_counts,
            })

        # Derive lane metadata
        risk_levels = {a["risk"] for a in accts}
        worst_risk = "critical" if "critical" in risk_levels else (
            "high" if "high" in risk_levels else (
                "medium" if "medium" in risk_levels else "low"
            )
        )

        meta = {}
        if batch_by == "wave":
            w = accts[0]["wave"]
            wm = WAVE_META.get(w, {})
            meta = {
                "wave": w,
                "name": wm.get("name", lane_key),
                "classification_rules": wm.get("classification_rules", []),
                "gate": wm.get("gate", ""),
            }
        else:
            meta = {"name": lane_key, "classification_rules": [], "gate": ""}

        waves.append({
            **meta,
            "risk": worst_risk,
            "total": len(accts),
            "batches": batches,
            "etl_steps": ETL_STEPS,
        })

    return {"waves": waves}


@router.get("/{account_id}")
async def get_account(account_id: str, option: str = "a"):
    """Full account profile with option-specific permission mapping."""
    for a in ACCOUNTS:
        if a["id"] == account_id:
            result = dict(a)
            if option == "a":
                result["permission_mapping"] = {
                    "target_role": a["target_role_a"],
                    "escalation_flag": a["escalation_flag_a"],
                    "model": "22 -> 4 (LOSSY)",
                }
            else:
                result["permission_mapping"] = {
                    "target_permissions": a["target_permissions_b"],
                    "model": "22 -> 22 (1:1)",
                }
            return result
    return {"error": f"Account {account_id} not found"}


def _group_key(account: dict, group_by: str) -> str:
    """Extract grouping key from an account dict."""
    if group_by == "wave":
        return str(account["wave"])
    if group_by == "nhi_type":
        return account.get("nhi_type") or "human"
    return str(account.get(group_by, "unknown"))

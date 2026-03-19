from fastapi import APIRouter
from datetime import datetime, timezone, timedelta

router = APIRouter()

_now = datetime.now(timezone.utc)

_DRIFT_EVENTS = [
    {
        "event_id":     "de-004",
        "category":     "POLICY",
        "severity":     "HIGH",
        "safe_name":    "Finance-Prod-Secrets",
        "description":  "Dual Control flag enabled post-baseline. 12 accounts now require dual approval — migration logic must be updated.",
        "delta":        "dual_control: false → true (12 accounts)",
        "detected_at":  (_now - timedelta(hours=2)).isoformat(),
        "status":       "YELLOW_CHECKPOINT_FIRED",
        "checkpoint_id": "yc-drift-002",
    },
    {
        "event_id":     "de-005",
        "category":     "MEMBERSHIP",
        "severity":     "MEDIUM",
        "safe_name":    "Shared-Services",
        "description":  "4 accounts relocated from 'Shared-Services' to 'Infra-Windows-Legacy' mid-migration. Dependency map stale.",
        "delta":        "4 accounts moved between Safes",
        "detected_at":  (_now - timedelta(minutes=47)).isoformat(),
        "status":       "YELLOW_CHECKPOINT_FIRED",
        "checkpoint_id": "yc-drift-003",
    },
    {
        "event_id":     "de-001",
        "category":     "STRUCTURAL",
        "severity":     "MEDIUM",
        "safe_name":    "DevOps-Pipeline-Prod",
        "description":  "New Safe 'DevOps-Pipeline-Prod' added post-baseline (38 accounts). Not present in P1 discovery manifest.",
        "delta":        "+1 Safe, +38 accounts",
        "detected_at":  (_now - timedelta(hours=6)).isoformat(),
        "status":       "YELLOW_CHECKPOINT_FIRED",
        "checkpoint_id": "yc-drift-001",
    },
    {
        "event_id":     "de-002",
        "category":     "PLATFORM",
        "severity":     "LOW",
        "safe_name":    "Infra-Windows-Legacy",
        "description":  "Platform type changed: WinServerLocal → WinDomain for 3 accounts in 'Infra-Windows-Legacy'.",
        "delta":        "3 accounts platform mutated",
        "detected_at":  (_now - timedelta(hours=18)).isoformat(),
        "status":       "LOGGED",
        "checkpoint_id": None,
    },
    {
        "event_id":     "de-003",
        "category":     "ACCOUNT",
        "severity":     "INFO",
        "safe_name":    "Dev-Sandbox",
        "description":  "Account count delta: 'Dev-Sandbox' had 48 accounts at baseline, now 51 (+3 provisioned since P1).",
        "delta":        "+3 accounts",
        "detected_at":  (_now - timedelta(hours=31)).isoformat(),
        "status":       "LOGGED",
        "checkpoint_id": None,
    },
]


@router.get("/events")
async def get_drift_events():
    return {
        "events": _DRIFT_EVENTS,
        "summary": {
            "total":              len(_DRIFT_EVENTS),
            "critical":           sum(1 for e in _DRIFT_EVENTS if e["severity"] == "CRITICAL"),
            "high":               sum(1 for e in _DRIFT_EVENTS if e["severity"] == "HIGH"),
            "medium":             sum(1 for e in _DRIFT_EVENTS if e["severity"] == "MEDIUM"),
            "low_info":           sum(1 for e in _DRIFT_EVENTS if e["severity"] in ("LOW", "INFO")),
            "checkpoints_fired":  sum(1 for e in _DRIFT_EVENTS if e["status"] == "YELLOW_CHECKPOINT_FIRED"),
        },
        "baseline_snapshot": {
            "captured_at":   (_now - timedelta(weeks=8)).isoformat(),
            "phase":         "P1",
            "total_safes":   142,
            "total_accounts": 2847,
            "schema_hash":   "a3f2b1c9e4d7",
        },
        "current_snapshot": {
            "captured_at":   datetime.now(timezone.utc).isoformat(),
            "total_safes":   143,
            "total_accounts": 2888,
            "schema_hash":   "b7e4c2a1f9d3",
        },
        "last_scan": datetime.now(timezone.utc).isoformat(),
    }

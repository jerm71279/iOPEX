from fastapi import APIRouter
from datetime import datetime, timezone, timedelta

router = APIRouter()

_now = datetime.now(timezone.utc)

_CB_DATA = {
    "cyberark_pvwa": {
        "label":                   "CyberArk PVWA (Source)",
        "state":                   "CLOSED",
        "failure_count":           0,
        "last_trip":               None,
        "recovery_at":             None,
        "fallback_strategy":       "PAUSE_WAVE",
        "call_count_rolling":      3847,
        "error_rate_pct":          0.6,
        "avg_latency_ms":          142,
        "half_open_probes":        0,
    },
    "devolutions_server": {
        "label":                   "Devolutions Server (Option A)",
        "state":                   "CLOSED",
        "failure_count":           0,
        "last_trip":               None,
        "recovery_at":             None,
        "fallback_strategy":       "PAUSE_WAVE",
        "call_count_rolling":      1204,
        "error_rate_pct":          1.2,
        "avg_latency_ms":          198,
        "half_open_probes":        0,
    },
    "keeper_cloud": {
        "label":                   "Keeper Cloud API (Option B)",
        "state":                   "HALF_OPEN",
        "failure_count":           3,
        "last_trip":               (_now - timedelta(minutes=4, seconds=12)).isoformat(),
        "recovery_at":             (_now + timedelta(seconds=48)).isoformat(),
        "fallback_strategy":       "SINGLE_AGENT_MODE",
        "call_count_rolling":      892,
        "error_rate_pct":          8.1,
        "avg_latency_ms":          2140,
        "half_open_probes":        1,
        "notes":                   "HTTP 403 throttle (NOT 429) — cumulative window. Max 50 calls/min. Batch in groups of 10 with 2s pause.",
    },
    "miniorange_pam": {
        "label":                   "MiniOrange PAM API (Option C)",
        "state":                   "CLOSED",
        "failure_count":           0,
        "last_trip":               None,
        "recovery_at":             None,
        "fallback_strategy":       "HUMAN_IN_LOOP",
        "call_count_rolling":      289,
        "error_rate_pct":          0.0,
        "avg_latency_ms":          321,
        "half_open_probes":        0,
    },
}


@router.get("")
async def get_circuit_breaker_status():
    return {
        "targets": _CB_DATA,
        "summary": {
            "closed":    sum(1 for t in _CB_DATA.values() if t["state"] == "CLOSED"),
            "half_open": sum(1 for t in _CB_DATA.values() if t["state"] == "HALF_OPEN"),
            "open":      sum(1 for t in _CB_DATA.values() if t["state"] == "OPEN"),
        },
        "last_updated": datetime.now(timezone.utc).isoformat(),
    }

from fastapi import APIRouter
from backend.mock_data.data import WAVES

router = APIRouter()

INTEGRITY_CHECKS = [
    {"id": "IC_01", "name": "Safe Name Exact Match",       "severity": "CRITICAL", "blocking": True},
    {"id": "IC_02", "name": "Username Preserved",          "severity": "CRITICAL", "blocking": True},
    {"id": "IC_03", "name": "Platform ID Correct",         "severity": "HIGH",     "blocking": True},
    {"id": "IC_04", "name": "Dual Control Flag Match",     "severity": "HIGH",     "blocking": True},
    {"id": "IC_05", "name": "MFA Policy Match",            "severity": "HIGH",     "blocking": True},
    {"id": "IC_06", "name": "CPM Managed Flag",            "severity": "HIGH",     "blocking": False},
    {"id": "IC_07", "name": "Session Recording Match",     "severity": "MEDIUM",   "blocking": False},
    {"id": "IC_08", "name": "No Extra Accounts in Safe",   "severity": "HIGH",     "blocking": False},
    {"id": "IC_09", "name": "No Missing Accounts",         "severity": "CRITICAL", "blocking": True},
    {"id": "IC_10", "name": "Policy Hash Match",           "severity": "HIGH",     "blocking": True},
    {"id": "IC_11", "name": "NHI Account Isolation",       "severity": "MEDIUM",   "blocking": False},
    {"id": "IC_12", "name": "Dependency Order Respected",  "severity": "HIGH",     "blocking": True},
]

# Per-wave mock results — deterministic
_WAVE_RESULTS = {
    "1": {
        "accuracy_pct": 100.0,
        "failures": [],
    },
    "2": {
        "accuracy_pct": 100.0,
        "failures": [
            {"check": "IC_07", "account": "svc-network-mon",
             "detail": "Session recording flag mismatch — non-blocking, logged"},
        ],
    },
    "3": {
        "accuracy_pct": 98.7,
        "failures": [
            {"check": "IC_11", "account": "svc-k8s-deployer",
             "detail": "NHI co-located with human account in Safe — non-blocking"},
            {"check": "IC_08", "account": "svc-api-gateway",
             "detail": "1 unexpected account found in target Safe — non-blocking"},
        ],
    },
    "4": {
        "accuracy_pct": 96.1,
        "failures": [
            {"check": "IC_12", "account": "svc-db-reconcile",
             "detail": "BLOCKING: Reconciliation account migrated before dependents resolved — wave paused"},
            {"check": "IC_10", "account": "svc-db-reconcile",
             "detail": "BLOCKING: Policy hash mismatch after re-sequence detected"},
        ],
    },
    "5": {
        "accuracy_pct": 99.3,
        "failures": [
            {"check": "IC_06", "account": "svc-infra-legacy",
             "detail": "CPM managed flag mismatch — legacy platform, non-blocking"},
        ],
    },
}


@router.get("/{wave_id}")
async def get_wave_integrity(wave_id: str):
    w = WAVES.get(wave_id)
    if not w:
        return {"error": f"Wave {wave_id} not found"}

    wr = _WAVE_RESULTS.get(wave_id, {"accuracy_pct": 100.0, "failures": []})
    fail_map = {f["check"]: f for f in wr["failures"]}
    blocking_ids = {c["id"] for c in INTEGRITY_CHECKS if c["blocking"]}

    checks_out = []
    passed = warned = failed = 0
    for c in INTEGRITY_CHECKS:
        if c["id"] in fail_map:
            fi = fail_map[c["id"]]
            if c["blocking"]:
                status = "fail"
                failed += 1
            else:
                status = "warn"
                warned += 1
            detail = fi["detail"]
        else:
            status = "pass"
            passed += 1
            detail = "No discrepancies detected"
        checks_out.append({
            "id":       c["id"],
            "name":     c["name"],
            "severity": c["severity"],
            "blocking": c["blocking"],
            "status":   status,
            "detail":   detail,
        })

    return {
        "wave":         int(wave_id),
        "wave_name":    w["name"],
        "total_accounts": w["account_count"],
        "checks_run":   12,
        "passed":       passed,
        "failed":       failed,
        "warned":       warned,
        "skipped":      0,
        "accuracy_pct": wr["accuracy_pct"],
        "validated_by": "agent_18_integrity_validator",
        "session":      "read-only — separate API session from Migration Executor",
        "checks":       checks_out,
    }

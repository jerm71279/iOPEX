"""
PMO Intelligence Layer 0 — Mock Data
Powers /api/pmo/* endpoints in demo mode (no ChromaDB required).
All endpoint signatures match shift_pmo_router.py exactly.
"""
from datetime import timezone
import uuid

# Current program state
CURRENT_PHASE = "P2"
CURRENT_WEEK = 14

# ---------------------------------------------------------------------------
# PMO_EXECUTIVE_SUMMARY
# Keyed by phase. Provides AI-synthesized executive narrative per phase.
# ---------------------------------------------------------------------------
PMO_EXECUTIVE_SUMMARY = {
    "P0": {
        "phase": "P0",
        "answer": (
            "Phase 0 (Program Setup) is COMPLETE. All environment setup tasks were "
            "finished in Week 1. Config repositories, CI/CD pipelines, and credential "
            "vaults were provisioned. All gates were GREEN. No blockers recorded."
        ),
        "citations": ["gate_p0_complete_a1b2c3"],
        "gate_summary": {"GREEN": 2, "AMBER": 0, "BLOCKED": 0, "OPEN": 0},
        "checkpoint_summary": {
            "CRITICAL": {"count": 0, "resolve_rate": 0},
            "BLOCK": {"count": 0, "resolve_rate": 0},
            "WARN": {"count": 0, "resolve_rate": 0},
            "INFO": {"count": 2, "resolve_rate": 100},
        },
    },
    "P1": {
        "phase": "P1",
        "answer": (
            "Phase 1 (Discovery & Analysis) is COMPLETE. Discovery manifest produced "
            "847 accounts across 42 Safes. Dependency graph mapped 89 CCP/AAM "
            "integrations. NHI classification identified 554 non-human identities at "
            "97% confidence. Gap analysis and permission audit delivered and accepted. "
            "All gates reached GREEN by Week 10. No open items."
        ),
        "citations": ["gate_p1_complete_b2c3d4", "directive_P1_final_e5f6a7"],
        "gate_summary": {"GREEN": 2, "AMBER": 0, "BLOCKED": 0, "OPEN": 0},
        "checkpoint_summary": {
            "CRITICAL": {"count": 0, "resolve_rate": 0},
            "BLOCK": {"count": 1, "resolve_rate": 100},
            "WARN": {"count": 2, "resolve_rate": 100},
            "INFO": {"count": 6, "resolve_rate": 100},
        },
    },
    "P2": {
        "phase": "P2",
        "answer": (
            "Phase 2 (Baseline & Infrastructure) is on schedule at Week 14. Gate 4 "
            "(Staging Approval) is AMBER with two outstanding IOPEX_DELIVERY items: "
            "schema drift baseline capture and CPM heartbeat confirmation, both due "
            "Week 15. Gate 3 (Discovery Sign-off) is BLOCKED — CLIENT_INFOSEC security "
            "review of the 22\u21924 Keeper permission mapping has been outstanding 4 "
            "days; escalation is due 2026-03-20. No CRITICAL checkpoints are open. "
            "Wave 1 readiness is CONDITIONAL pending Gate 3 and Gate 4 resolution. "
            "Immediate executive attention required: CLIENT_INFOSEC must complete Gate 3 "
            "review before end of week or Wave 1 timeline slips."
        ),
        "citations": [
            "gate_4_AMBER_f3a9b2",
            "directive_P2_w14_cc8d31",
            "blocker_INFOSEC_g3_7e22a1",
        ],
        "gate_summary": {"GREEN": 2, "AMBER": 1, "BLOCKED": 1, "OPEN": 13},
        "checkpoint_summary": {
            "CRITICAL": {"count": 0, "resolve_rate": 0},
            "BLOCK": {"count": 1, "resolve_rate": 100},
            "WARN": {"count": 3, "resolve_rate": 67},
            "INFO": {"count": 8, "resolve_rate": 88},
        },
    },
    "P3": {
        "phase": "P3",
        "answer": (
            "Phase 3 (Safe & Policy Migration) has not started. It is pending completion "
            "of Phase 2 gates. No gates, checkpoints, or directives are recorded yet."
        ),
        "citations": [],
        "gate_summary": {"GREEN": 0, "AMBER": 0, "BLOCKED": 0, "OPEN": 0},
        "checkpoint_summary": {
            "CRITICAL": {"count": 0, "resolve_rate": 0},
            "BLOCK": {"count": 0, "resolve_rate": 0},
            "WARN": {"count": 0, "resolve_rate": 0},
            "INFO": {"count": 0, "resolve_rate": 0},
        },
    },
    "P4": {
        "phase": "P4",
        "answer": (
            "Phase 4 (Pilot Migration) has not started. No data available."
        ),
        "citations": [],
        "gate_summary": {"GREEN": 0, "AMBER": 0, "BLOCKED": 0, "OPEN": 0},
        "checkpoint_summary": {
            "CRITICAL": {"count": 0, "resolve_rate": 0},
            "BLOCK": {"count": 0, "resolve_rate": 0},
            "WARN": {"count": 0, "resolve_rate": 0},
            "INFO": {"count": 0, "resolve_rate": 0},
        },
    },
    "P5": {
        "phase": "P5",
        "answer": (
            "Phase 5 (Production Batches) has not started. No data available."
        ),
        "citations": [],
        "gate_summary": {"GREEN": 0, "AMBER": 0, "BLOCKED": 0, "OPEN": 0},
        "checkpoint_summary": {
            "CRITICAL": {"count": 0, "resolve_rate": 0},
            "BLOCK": {"count": 0, "resolve_rate": 0},
            "WARN": {"count": 0, "resolve_rate": 0},
            "INFO": {"count": 0, "resolve_rate": 0},
        },
    },
    "P6": {
        "phase": "P6",
        "answer": (
            "Phase 6 (Parallel Running & Cutover) has not started. No data available."
        ),
        "citations": [],
        "gate_summary": {"GREEN": 0, "AMBER": 0, "BLOCKED": 0, "OPEN": 0},
        "checkpoint_summary": {
            "CRITICAL": {"count": 0, "resolve_rate": 0},
            "BLOCK": {"count": 0, "resolve_rate": 0},
            "WARN": {"count": 0, "resolve_rate": 0},
            "INFO": {"count": 0, "resolve_rate": 0},
        },
    },
    "P7": {
        "phase": "P7",
        "answer": (
            "Phase 7 (Decommission & Close-Out) has not started. No data available."
        ),
        "citations": [],
        "gate_summary": {"GREEN": 0, "AMBER": 0, "BLOCKED": 0, "OPEN": 0},
        "checkpoint_summary": {
            "CRITICAL": {"count": 0, "resolve_rate": 0},
            "BLOCK": {"count": 0, "resolve_rate": 0},
            "WARN": {"count": 0, "resolve_rate": 0},
            "INFO": {"count": 0, "resolve_rate": 0},
        },
    },
}

# ---------------------------------------------------------------------------
# PMO_GATE_PIPELINE
# Keyed by phase. All 17 gates listed for P2 with status and owner.
# ---------------------------------------------------------------------------
PMO_GATE_PIPELINE = {
    "P0": {
        "phase": "P0",
        "gates": [
            {
                "gate_id": 1,
                "name": "Program Kickoff",
                "status": "GREEN",
                "owner_team": "IOPEX_DELIVERY",
                "last_event": "2026-01-15T00:00:00Z",
            },
            {
                "gate_id": 2,
                "name": "Environment Provisioning",
                "status": "GREEN",
                "owner_team": "IOPEX_DELIVERY",
                "last_event": "2026-01-22T00:00:00Z",
            },
        ],
        "summary": {"GREEN": 2, "AMBER": 0, "BLOCKED": 0, "OPEN": 0},
    },
    "P1": {
        "phase": "P1",
        "gates": [
            {
                "gate_id": 3,
                "name": "Discovery Sign-off",
                "status": "GREEN",
                "owner_team": "CLIENT_INFOSEC",
                "last_event": "2026-02-28T00:00:00Z",
            },
            {
                "gate_id": 4,
                "name": "Gap Analysis Accepted",
                "status": "GREEN",
                "owner_team": "IOPEX_DELIVERY",
                "last_event": "2026-03-05T00:00:00Z",
            },
        ],
        "summary": {"GREEN": 2, "AMBER": 0, "BLOCKED": 0, "OPEN": 0},
    },
    "P2": {
        "phase": "P2",
        "gates": [
            {
                "gate_id": 1,
                "name": "Kickoff & Charter Approved",
                "status": "GREEN",
                "owner_team": "IOPEX_DELIVERY",
                "last_event": "2026-01-15T00:00:00Z",
            },
            {
                "gate_id": 2,
                "name": "Source System Access Verified",
                "status": "GREEN",
                "owner_team": "IOPEX_DELIVERY",
                "last_event": "2026-02-01T00:00:00Z",
            },
            {
                "gate_id": 3,
                "name": "Discovery Sign-off",
                "status": "BLOCKED",
                "owner_team": "CLIENT_INFOSEC",
                "last_event": "2026-03-15T00:00:00Z",
            },
            {
                "gate_id": 4,
                "name": "Staging Approval",
                "status": "AMBER",
                "owner_team": "IOPEX_DELIVERY",
                "last_event": "2026-03-18T00:00:00Z",
            },
            {
                "gate_id": 5,
                "name": "Compliance Framework Accepted",
                "status": "OPEN",
                "owner_team": "CLIENT_INFOSEC",
                "last_event": None,
            },
            {
                "gate_id": 6,
                "name": "Risk Register Signed",
                "status": "OPEN",
                "owner_team": "CLIENT_INFOSEC",
                "last_event": None,
            },
            {
                "gate_id": 7,
                "name": "ETL Pipeline Validated",
                "status": "OPEN",
                "owner_team": "IOPEX_DELIVERY",
                "last_event": None,
            },
            {
                "gate_id": 8,
                "name": "Permission Loss Report Accepted",
                "status": "OPEN",
                "owner_team": "CLIENT_INFOSEC",
                "last_event": None,
            },
            {
                "gate_id": 9,
                "name": "NHI Wave Plan Approved",
                "status": "OPEN",
                "owner_team": "IOPEX_DELIVERY",
                "last_event": None,
            },
            {
                "gate_id": 10,
                "name": "PCI-DSS Control Mapping Accepted",
                "status": "OPEN",
                "owner_team": "CLIENT_INFOSEC",
                "last_event": None,
            },
            {
                "gate_id": 11,
                "name": "Runbook P3 Approved",
                "status": "OPEN",
                "owner_team": "IOPEX_DELIVERY",
                "last_event": None,
            },
            {
                "gate_id": 12,
                "name": "Target Vendor Infrastructure Confirmed",
                "status": "OPEN",
                "owner_team": "DBD_VENDOR",
                "last_event": None,
            },
            {
                "gate_id": 13,
                "name": "Wave 1 Preflight Complete",
                "status": "OPEN",
                "owner_team": "IOPEX_DELIVERY",
                "last_event": None,
            },
            {
                "gate_id": 14,
                "name": "Keeper Gateway Provisioned",
                "status": "OPEN",
                "owner_team": "DBD_VENDOR",
                "last_event": None,
            },
            {
                "gate_id": 15,
                "name": "Template Validation Complete",
                "status": "OPEN",
                "owner_team": "DBD_VENDOR",
                "last_event": None,
            },
            {
                "gate_id": 16,
                "name": "IT Ops Cutover Approval — Pilot",
                "status": "OPEN",
                "owner_team": "CLIENT_IT_OPS",
                "last_event": None,
            },
            {
                "gate_id": 17,
                "name": "IT Ops Cutover Approval — Production",
                "status": "OPEN",
                "owner_team": "CLIENT_IT_OPS",
                "last_event": None,
            },
        ],
        "summary": {"GREEN": 2, "AMBER": 1, "BLOCKED": 1, "OPEN": 13},
    },
    "P3": {"phase": "P3", "gates": [], "summary": {"GREEN": 0, "AMBER": 0, "BLOCKED": 0, "OPEN": 0}},
    "P4": {"phase": "P4", "gates": [], "summary": {"GREEN": 0, "AMBER": 0, "BLOCKED": 0, "OPEN": 0}},
    "P5": {"phase": "P5", "gates": [], "summary": {"GREEN": 0, "AMBER": 0, "BLOCKED": 0, "OPEN": 0}},
    "P6": {"phase": "P6", "gates": [], "summary": {"GREEN": 0, "AMBER": 0, "BLOCKED": 0, "OPEN": 0}},
    "P7": {"phase": "P7", "gates": [], "summary": {"GREEN": 0, "AMBER": 0, "BLOCKED": 0, "OPEN": 0}},
}

# ---------------------------------------------------------------------------
# PMO_TEAM_ACCOUNTABILITY
# Per-team completion metrics for the current analysis window (4 weeks).
# ---------------------------------------------------------------------------
PMO_TEAM_ACCOUNTABILITY = {
    "weeks_analyzed": 4,
    "teams": [
        {
            "team_id": "IOPEX_DELIVERY",
            "display_name": "iOPEX Delivery (Jeremy Smith)",
            "role": "Migration integrator — runs all agents and executes all work",
            "gates": ["g1", "g2", "g4", "g7", "g9", "g11", "g13"],
            "completion_rate": 87,
            "completed": 14,
            "total": 16,
            "blocked": 0,
            "last_items": [
                {
                    "item_id": "AI-2026-047",
                    "description": "Capture P2 schema drift baseline via POST /api/drift/baseline; store results in data/drift_baseline_P2.json",
                    "status": "OPEN",
                    "due_week": 15,
                    "due_date": "2026-03-21",
                    "unblocks": "Gate 4",
                },
                {
                    "item_id": "AI-2026-048",
                    "description": "Confirm CPM heartbeat success rate >95% against staging target (Agent 05)",
                    "status": "OPEN",
                    "due_week": 15,
                    "due_date": "2026-03-21",
                    "unblocks": "Gate 4",
                },
                {
                    "item_id": "AI-2026-046",
                    "description": "Deliver P2 NHI re-classification report for 554 NHI accounts to CLIENT_INFOSEC",
                    "status": "COMPLETE",
                    "due_week": 13,
                    "due_date": "2026-03-14",
                    "unblocks": "Gate 3",
                },
            ],
        },
        {
            "team_id": "CLIENT_INFOSEC",
            "display_name": "Cisco Security & Compliance",
            "role": "Security and compliance sign-offs",
            "gates": ["g3", "g5", "g6", "g8", "g10"],
            "completion_rate": 60,
            "completed": 3,
            "total": 5,
            "blocked": 1,
            "last_items": [
                {
                    "item_id": "AI-2026-039",
                    "description": "Review Keeper 22\u21924 permission mapping loss findings and formally accept or reject risk (PCI-DSS 7.1 dual-control)",
                    "status": "BLOCKED",
                    "due_week": 14,
                    "due_date": "2026-03-19",
                    "unblocks": "Gate 3",
                    "days_outstanding": 4,
                    "escalation_due": "2026-03-20",
                },
                {
                    "item_id": "AI-2026-033",
                    "description": "Sign off on NHI classification report (554 NHI accounts, 97% confidence)",
                    "status": "COMPLETE",
                    "due_week": 13,
                    "due_date": "2026-03-14",
                    "unblocks": None,
                },
                {
                    "item_id": "AI-2026-029",
                    "description": "Approve compliance framework mapping (PCI-DSS, NIST 800-53, SOX) for Keeper target",
                    "status": "COMPLETE",
                    "due_week": 12,
                    "due_date": "2026-03-07",
                    "unblocks": None,
                },
            ],
        },
        {
            "team_id": "CLIENT_IT_OPS",
            "display_name": "Cisco IT Operations",
            "role": "Cutover approvals",
            "gates": ["g16", "g17"],
            "completion_rate": 100,
            "completed": 2,
            "total": 2,
            "blocked": 0,
            "last_items": [
                {
                    "item_id": "AI-2026-011",
                    "description": "Confirm PVWA source system read-only service account provisioned for migration agent",
                    "status": "COMPLETE",
                    "due_week": 11,
                    "due_date": "2026-02-28",
                    "unblocks": "Gate 2",
                },
                {
                    "item_id": "AI-2026-012",
                    "description": "Confirm staging network segment access for IOPEX_DELIVERY agents (DMZ-STAGE-01)",
                    "status": "COMPLETE",
                    "due_week": 11,
                    "due_date": "2026-02-28",
                    "unblocks": "Gate 4 pre-req",
                },
                {
                    "item_id": "AI-2026-031",
                    "description": "Review and approve app owner notification template for Wave 1 service accounts",
                    "status": "COMPLETE",
                    "due_week": 12,
                    "due_date": "2026-03-07",
                    "unblocks": None,
                },
            ],
        },
        {
            "team_id": "DBD_VENDOR",
            "display_name": "Target Vendor Team (Devolutions / Keeper / MiniOrange)",
            "role": "Target platform vendor support",
            "gates": ["g12", "g14", "g15"],
            "completion_rate": 75,
            "completed": 3,
            "total": 4,
            "blocked": 0,
            "last_items": [
                {
                    "item_id": "AI-2026-044",
                    "description": "Confirm Keeper Gateway Docker deployment specification and network zone approval for Cisco DMZ-PROD-02 segment",
                    "status": "OPEN",
                    "due_week": 15,
                    "due_date": "2026-03-21",
                    "unblocks": "Gate 12 / Gate 14",
                },
                {
                    "item_id": "AI-2026-038",
                    "description": "Deliver Keeper Secret Template mapping for Cisco custom platforms (IOS, NX-OS, ASA)",
                    "status": "COMPLETE",
                    "due_week": 13,
                    "due_date": "2026-03-14",
                    "unblocks": "Gate 15",
                },
                {
                    "item_id": "AI-2026-032",
                    "description": "Resolve Keeper Gateway HTTP 403 throttle misclassification — confirmed configuration fix deployed to staging",
                    "status": "COMPLETE",
                    "due_week": 12,
                    "due_date": "2026-03-07",
                    "unblocks": "BLOCK checkpoint",
                },
            ],
        },
    ],
}

# ---------------------------------------------------------------------------
# PMO_CHECKPOINT_HISTORY
# Keyed by phase. Checkpoint counts and resolve rates.
# ---------------------------------------------------------------------------
PMO_CHECKPOINT_HISTORY = {
    "P0": {
        "phase": "P0",
        "CRITICAL": {"count": 0, "resolve_rate": 0, "items": []},
        "BLOCK": {"count": 0, "resolve_rate": 0, "items": []},
        "WARN": {"count": 0, "resolve_rate": 0, "items": []},
        "INFO": {"count": 2, "resolve_rate": 100, "items": [
            {"id": "cp_p0_info_01", "description": "Credential vault provisioning confirmed", "resolved": True},
            {"id": "cp_p0_info_02", "description": "Git repository and CI/CD pipeline initialized", "resolved": True},
        ]},
    },
    "P1": {
        "phase": "P1",
        "CRITICAL": {"count": 0, "resolve_rate": 0, "items": []},
        "BLOCK": {"count": 1, "resolve_rate": 100, "items": [
            {
                "id": "cp_p1_block_01",
                "description": "CyberArk PVWA API pagination returning incomplete account set for Safe 'Infra-Windows-Prod' — missing 47 accounts in export batch",
                "resolved": True,
                "resolution": "Applied X-PVWA-Token refresh and re-paginated with offset correction. All 47 accounts recovered.",
                "resolved_week": 9,
            }
        ]},
        "WARN": {"count": 2, "resolve_rate": 100, "items": [
            {"id": "cp_p1_warn_01", "description": "NHI confidence below 95% threshold for 18 accounts — manual review required", "resolved": True},
            {"id": "cp_p1_warn_02", "description": "3 Safes with no members in source — verify intentional or orphaned", "resolved": True},
        ]},
        "INFO": {"count": 6, "resolve_rate": 100, "items": [
            {"id": "cp_p1_info_01", "description": "Discovery manifest delivered: 847 accounts, 42 Safes", "resolved": True},
            {"id": "cp_p1_info_02", "description": "Dependency graph complete: 89 CCP/AAM integrations mapped", "resolved": True},
            {"id": "cp_p1_info_03", "description": "NHI classification complete: 554 NHI accounts at 97% confidence", "resolved": True},
            {"id": "cp_p1_info_04", "description": "Gap analysis delivered — 10 domains assessed", "resolved": True},
            {"id": "cp_p1_info_05", "description": "Permission audit delivered — 22\u21924 mapping loss report generated", "resolved": True},
            {"id": "cp_p1_info_06", "description": "Wave classification complete — 5 waves defined", "resolved": True},
        ]},
    },
    "P2": {
        "phase": "P2",
        "CRITICAL": {"count": 0, "resolve_rate": 0, "items": []},
        "BLOCK": {
            "count": 1,
            "resolve_rate": 100,
            "items": [
                {
                    "id": "cp_p2_block_01",
                    "description": "Keeper Gateway returned HTTP 403 on heartbeat probe — misclassified as permission error, actual cause was rate-limit header not honoured by Agent 05",
                    "resolved": True,
                    "resolution": "DBD_VENDOR deployed Gateway config fix (rate_limit_per_minute=120); Agent 05 updated to honour Retry-After header. Re-test passed.",
                    "resolved_week": 12,
                }
            ],
        },
        "WARN": {
            "count": 3,
            "resolve_rate": 67,
            "items": [
                {
                    "id": "cp_p2_warn_01",
                    "description": "Schema drift detected in Safe 'Oracle-Prod-Finance' — 3 accountProperties fields renamed since discovery snapshot",
                    "resolved": True,
                    "resolution": "ETL transform map updated to handle legacy field names with fallback. Baseline re-captured.",
                    "resolved_week": 13,
                },
                {
                    "id": "cp_p2_warn_02",
                    "description": "Staging environment CPM heartbeat success rate at 91% — below 95% threshold",
                    "resolved": False,
                    "resolution": None,
                    "resolved_week": None,
                },
                {
                    "id": "cp_p2_warn_03",
                    "description": "P2 schema drift baseline not yet captured — Gate 4 dependency outstanding",
                    "resolved": False,
                    "resolution": None,
                    "resolved_week": None,
                },
            ],
        },
        "INFO": {
            "count": 8,
            "resolve_rate": 88,
            "items": [
                {"id": "cp_p2_info_01", "description": "Staging environment provisioned and reachable from IOPEX_DELIVERY agents", "resolved": True},
                {"id": "cp_p2_info_02", "description": "Agent 10 (Staging Validation) executed — 9/10 assertions passed", "resolved": True},
                {"id": "cp_p2_info_03", "description": "Agent 13 (Platform Plugins) exported 23 custom CyberArk platforms", "resolved": True},
                {"id": "cp_p2_info_04", "description": "Keeper Secret Templates created for 20/23 exported platforms", "resolved": True},
                {"id": "cp_p2_info_05", "description": "Integration repoint analysis complete — 89 integrations require code changes", "resolved": True},
                {"id": "cp_p2_info_06", "description": "Wave 1 account list finalized: 142 standard Windows/Unix accounts", "resolved": True},
                {"id": "cp_p2_info_07", "description": "App owner notification schedule drafted for Wave 1", "resolved": True},
                {"id": "cp_p2_info_08", "description": "Keeper Gateway Docker spec received from DBD_VENDOR — network approval pending", "resolved": False},
            ],
        },
    },
    "P3": {"phase": "P3", "CRITICAL": {"count": 0, "resolve_rate": 0, "items": []}, "BLOCK": {"count": 0, "resolve_rate": 0, "items": []}, "WARN": {"count": 0, "resolve_rate": 0, "items": []}, "INFO": {"count": 0, "resolve_rate": 0, "items": []}},
    "P4": {"phase": "P4", "CRITICAL": {"count": 0, "resolve_rate": 0, "items": []}, "BLOCK": {"count": 0, "resolve_rate": 0, "items": []}, "WARN": {"count": 0, "resolve_rate": 0, "items": []}, "INFO": {"count": 0, "resolve_rate": 0, "items": []}},
    "P5": {"phase": "P5", "CRITICAL": {"count": 0, "resolve_rate": 0, "items": []}, "BLOCK": {"count": 0, "resolve_rate": 0, "items": []}, "WARN": {"count": 0, "resolve_rate": 0, "items": []}, "INFO": {"count": 0, "resolve_rate": 0, "items": []}},
    "P6": {"phase": "P6", "CRITICAL": {"count": 0, "resolve_rate": 0, "items": []}, "BLOCK": {"count": 0, "resolve_rate": 0, "items": []}, "WARN": {"count": 0, "resolve_rate": 0, "items": []}, "INFO": {"count": 0, "resolve_rate": 0, "items": []}},
    "P7": {"phase": "P7", "CRITICAL": {"count": 0, "resolve_rate": 0, "items": []}, "BLOCK": {"count": 0, "resolve_rate": 0, "items": []}, "WARN": {"count": 0, "resolve_rate": 0, "items": []}, "INFO": {"count": 0, "resolve_rate": 0, "items": []}},
}

# ---------------------------------------------------------------------------
# PMO_WEEK_OVER_WEEK
# List of weekly trend snapshots (weeks 11–14).
# ---------------------------------------------------------------------------
PMO_WEEK_OVER_WEEK = [
    {
        "week": 11,
        "gates_closed": 0,
        "exec_success_rate": 100,
        "critical_checkpoints": 0,
        "open_blockers": 0,
        "notes": "Environment validation complete. No incidents. All agents GREEN.",
    },
    {
        "week": 12,
        "gates_closed": 1,
        "exec_success_rate": 95,
        "critical_checkpoints": 0,
        "open_blockers": 1,
        "notes": "Gate 2 closed GREEN. Keeper Gateway HTTP 403 blocker opened and resolved within week by DBD_VENDOR config fix.",
    },
    {
        "week": 13,
        "gates_closed": 1,
        "exec_success_rate": 100,
        "critical_checkpoints": 0,
        "open_blockers": 1,
        "notes": "Agent 13 platform export complete (23 platforms). NHI re-classification report delivered to CLIENT_INFOSEC. Gate 3 blocker opened — CLIENT_INFOSEC review outstanding.",
    },
    {
        "week": 14,
        "gates_closed": 0,
        "exec_success_rate": 87,
        "critical_checkpoints": 0,
        "open_blockers": 1,
        "notes": "Gate 3 remains BLOCKED (4 days). Gate 4 moved to AMBER — 2 IOPEX_DELIVERY action items outstanding. Exec escalation triggered for Gate 3.",
    },
]

# ---------------------------------------------------------------------------
# PMO_CORPUS_STATS
# Describes the indexed event corpus powering the RAG engine.
# ---------------------------------------------------------------------------
PMO_CORPUS_STATS = {
    "total_indexed": 47,
    "by_type": {
        "pmo_directive": 14,
        "execution_result": 14,
        "gate_decision": 7,
        "yellow_checkpoint": 8,
        "blocker_event": 4,
    },
    "phases_covered": ["P0", "P1", "P2"],
    "date_range": {"earliest": "2026-01-15", "latest": "2026-03-18"},
    "embedding_model": "text-embedding-3-small",
    "rag_engine": "mock (demo mode — ChromaDB not required)",
}

# ---------------------------------------------------------------------------
# PMO_CANNED_ANSWERS
# List of keyword-matched Q&A pairs for demo mode PMO chat.
# Matching: lowercase(question) contains ANY keyword in the list.
# ---------------------------------------------------------------------------
PMO_DEFAULT_ANSWER = (
    "This question requires the live RAG corpus to answer accurately. In production, "
    "the PMO Intelligence Layer queries all indexed project events (directives, execution "
    "results, gate decisions, yellow checkpoints) using semantic search and synthesizes "
    "an answer. In this demo, the corpus contains 47 mock events. Enable the real RAG "
    "engine by adding shift_pmo_rag_engine.py and setting ANTHROPIC_API_KEY to get "
    "AI-synthesized answers from actual project history."
)

PMO_CANNED_ANSWERS = [
    {
        "keywords": ["wave 1", "delayed", "wave one"],
        "answer": (
            "Wave 1 is not yet delayed but readiness is CONDITIONAL. Gate 4 (Staging "
            "Approval) is AMBER — two items are outstanding: (1) P2 schema drift baseline "
            "has not been captured (IOPEX_DELIVERY, due Week 15) and (2) CPM heartbeat "
            "confirmation is pending. Gate 3 (Discovery Sign-off) is BLOCKED pending "
            "CLIENT_INFOSEC security review for 4 days (escalation due 2026-03-20). "
            "Wave 1 cannot start until both gates reach GREEN. Projected impact: 1-week "
            "slip if Gate 3 is not resolved by Week 15. "
            "Sources: gate_4_AMBER_f3a9b2, directive_P2_w14_cc8d31, blocker_INFOSEC_g3_7e22a1"
        ),
    },
    {
        "keywords": ["client_infosec", "infosec", "blocking", "blocked"],
        "answer": (
            "CLIENT_INFOSEC is blocking Gate 3 (Discovery Sign-off). The security review "
            "of the permission mapping loss findings has been outstanding since 2026-03-15 "
            "(4 days). The specific item requiring review is the Keeper 22\u21924 boolean "
            "axis mapping where 12 CyberArk permissions have no Keeper equivalent — "
            "CLIENT_INFOSEC must formally accept or reject the risk before Phase 3 "
            "proceeds. PCI-DSS 7.1 dual-control requires this to be an independent Cisco "
            "Security sign-off. Escalation is due 2026-03-20. "
            "Sources: blocker_INFOSEC_g3_7e22a1, directive_P2_w13_aa1b2c"
        ),
    },
    {
        "keywords": ["gate 4", "staging", "gate4"],
        "answer": (
            "Gate 4 (Staging Approval) is AMBER. Two items are missing: (1) P2 schema "
            "drift baseline capture — IOPEX_DELIVERY must run the drift baseline via "
            "POST /api/drift/baseline and store results in data/drift_baseline_P2.json. "
            "(2) CPM heartbeat confirmation — Agent 05 must verify heartbeat success rate "
            ">95% against the staging target. Both items are owned by IOPEX_DELIVERY and "
            "due by Week 15. Gate 4 blocks Wave 1 preflight. "
            "Sources: gate_4_AMBER_f3a9b2, directive_P2_w14_cc8d31"
        ),
    },
    {
        "keywords": ["gate 3", "discovery", "sign-off"],
        "answer": (
            "Gate 3 (Discovery Sign-off) is BLOCKED pending CLIENT_INFOSEC security "
            "review. All P1 discovery deliverables are complete: discovery manifest "
            "(847 accounts, 42 Safes), dependency graph (89 CCP/AAM integrations), NHI "
            "classifications (554 NHI accounts, 97% confidence), gap analysis, and "
            "permission audit. The blocker is specifically the CLIENT_INFOSEC review of "
            "permission mapping risk acceptance — the team must sign off on the 22\u21924 "
            "Keeper mapping loss before Phase 3 proceeds. "
            "Sources: blocker_INFOSEC_g3_7e22a1, gate_3_BLOCKED_d4e5f6"
        ),
    },
    {
        "keywords": ["top risk", "risks", "risk", "attention"],
        "answer": (
            "Top 3 risks requiring attention: (1) IMMEDIATE — Gate 3 CLIENT_INFOSEC "
            "blocker: 4 days outstanding, escalation due 2026-03-20. Unresolved = Wave 1 "
            "timeline slip. Owner: CLIENT_INFOSEC. (2) HIGH — Gate 4 AMBER: schema drift "
            "baseline and CPM heartbeat confirmation outstanding. Both IOPEX_DELIVERY "
            "action items due Week 15. (3) MEDIUM — Keeper Gateway provisioning not yet "
            "confirmed for P3 target infrastructure. DBD_VENDOR must confirm Docker "
            "deployment spec (4 CPU / 16GB per node) for Cisco network segments before P3 "
            "begins. "
            "Sources: gate_3_BLOCKED, gate_4_AMBER, directive_P2_w14"
        ),
    },
    {
        "keywords": ["nhi", "wave 3", "non-human"],
        "answer": (
            "Wave 3 (Non-Human Identities) contains 554 NHI accounts including "
            "Cisco-specific service accounts (IOS/NX-OS/ASA automation, Jenkins CI/CD, "
            "Terraform, Ansible Tower). Execution is owned by IOPEX_DELIVERY. Approval "
            "at Gate G9 requires: (1) App Owner confirmation within 48 hours per NHI "
            "(CLIENT_IT_OPS coordination), (2) Compliance rotation policy verification "
            "(CLIENT_INFOSEC — SOX dual-control), (3) Custom Keeper Gateway scripts for "
            "Cisco network device NHI types. Wave 3 is the highest-risk wave — any "
            "rotation policy misconfiguration will break production automation. "
            "Sources: wave3_plan_nhi, gate_g9_prereqs"
        ),
    },
    {
        "keywords": ["iopex", "action items", "delivery"],
        "answer": (
            "IOPEX_DELIVERY has 2 open action items this week: (1) AI-2026-047: Capture "
            "P2 schema drift baseline via POST /api/drift/baseline. Due 2026-03-21. "
            "Unblocks Gate 4. (2) AI-2026-048: Confirm CPM heartbeat success rate >95% "
            "against staging target. Due 2026-03-21. Unblocks Gate 4. Completion rate "
            "this week: 87% (14/16 items complete). 0 items currently blocked. "
            "Sources: directive_P2_w14_cc8d31"
        ),
    },
    {
        "keywords": ["dbd", "vendor", "devolutions", "keeper", "miniorange"],
        "answer": (
            "DBD_VENDOR (target platform vendor team — Devolutions/Keeper/MiniOrange) "
            "has 3/4 action items complete this week (75% completion rate). Outstanding "
            "item: confirm Keeper Gateway Docker deployment specification and network zone "
            "approval for Cisco DMZ-PROD-02 segment. This is a pre-P3 dependency — "
            "without Gateway in the target network segment, rotation and heartbeat calls "
            "cannot reach managed systems. DBD_VENDOR must coordinate with Cisco Network "
            "Security for firewall rule approval. "
            "Sources: directive_P2_w14, gate_g4_prereqs"
        ),
    },
]

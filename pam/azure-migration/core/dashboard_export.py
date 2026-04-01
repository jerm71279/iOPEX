"""Dashboard Status Exporter.

Reads migration state and agent report files from output/, builds a unified
status.json payload matching the SHIFT Migration Control Center API contract,
and uploads it to Azure Blob Storage for stakeholder visibility.

Called by the coordinator after each agent run and each phase advance.
Falls back to local file write if Azure SDK is not available or upload fails.

Upload destination: https://<dashStorageAccount>.blob.core.windows.net/dashboard/status.json
"""

import json
import logging
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# ── Static SHIFT system schema ─────────────────────────────────────────────
# These match the known project structure and feed the Control Center renderers.
# Dynamic fields (status, counts, pass_rates) are overlaid from output/ files.

_PHASES = [
    {"id": "p0", "label": "P0", "name": "Environment Setup",      "weeks": "1-2",  "color": "cyan",  "status": "pending"},
    {"id": "p1", "label": "P1", "name": "Discovery",              "weeks": "3-6",  "color": "blue",  "status": "pending"},
    {"id": "p2", "label": "P2", "name": "Staging Validation",     "weeks": "7-9",  "color": "teal",  "status": "pending"},
    {"id": "p3", "label": "P3", "name": "Vault & Permissions",    "weeks": "10-12","color": "green", "status": "pending"},
    {"id": "p4", "label": "P4", "name": "Pilot Migration",        "weeks": "13-14","color": "amber", "status": "pending"},
    {"id": "p5", "label": "P5", "name": "Production Waves",       "weeks": "15-20","color": "orange","status": "pending"},
    {"id": "p6", "label": "P6", "name": "Parallel Running",       "weeks": "21-26","color": "red",   "status": "pending"},
    {"id": "p7", "label": "P7", "name": "Decommission",           "weeks": "27-29","color": "purple","status": "pending"},
]

_AGENTS = [
    {"id": "01", "num": "01", "name": "Discovery & Dependency Mapping",    "phases": ["P1"],          "weeks": "3-4",  "desc": "Discovers all CyberArk assets, safes, accounts, and maps dependencies via the Applications API. Multi-signal NHI detection.", "status": "pending"},
    {"id": "02", "num": "02", "name": "Gap Analysis",                      "phases": ["P1"],          "weeks": "5",    "desc": "10-domain gap analysis mapping to PCI-DSS, NIST 800-53, HIPAA, and SOX controls. Identifies migration risk areas.", "status": "pending"},
    {"id": "03", "num": "03", "name": "Permission Mapping",                "phases": ["P1", "P3"],    "weeks": "6,10", "desc": "Maps all 22 CyberArk safe permissions 1:1 to KeeperPAM vaults via Safe Members API. Flags 7 sensitive permissions for review.", "status": "pending"},
    {"id": "04", "num": "04", "name": "ETL Orchestration",                 "phases": ["P4", "P5"],    "weeks": "13-20","desc": "7-step ETL pipeline: FREEZE → EXPORT → TRANSFORM → VAULT CREATION → IMPORT → HEARTBEAT → UNFREEZE. Watchdog auto-recovers on timeout.", "status": "pending"},
    {"id": "05", "num": "05", "name": "Heartbeat Validation",              "phases": ["P4","P5","P6"],"weeks": "13-26","desc": "10-category post-migration validation. Threshold-based pass/fail gate. Blocks next wave if below threshold.", "status": "pending"},
    {"id": "06", "num": "06", "name": "Integration Repointing",            "phases": ["P5", "P6"],    "weeks": "15-26","desc": "Scans application codebases for CyberArk CCP/AAM patterns and generates KeeperPAM replacement code in Python, PowerShell, C#, Java.", "status": "pending"},
    {"id": "07", "num": "07", "name": "Compliance & Audit",                "phases": ["P5","P6","P7"],"weeks": "15-29","desc": "Audit trail with SHA-256 hash chain. Maps every migration action to PCI-DSS, NIST 800-53, HIPAA, and SOX controls.", "status": "pending"},
    {"id": "08", "num": "08", "name": "Runbook Execution",                 "phases": ["P0-P7"],       "weeks": "1-29", "desc": "Phase orchestration engine. Manages human approval gates, phase transitions, and progress tracking across all phases.", "status": "pending"},
    {"id": "09", "num": "09", "name": "Dependency Mapper",                 "phases": ["P1"],          "weeks": "3-4",  "desc": "6-scanner infrastructure crawl: IIS applications, Windows services, scheduled tasks, Jenkins pipelines, scripts, config files.", "status": "pending"},
    {"id": "10", "num": "10", "name": "Staging Validation",                "phases": ["P2"],          "weeks": "7-8",  "desc": "10-assertion staging validation against KeeperPAM staging tenant. HARD BLOCK — prevents production ETL if any assertion fails.", "status": "pending"},
    {"id": "11", "num": "11", "name": "Source Adapter",                    "phases": ["P0", "P1"],    "weeks": "1-4",  "desc": "7-vendor normalizer supporting CyberArk, BeyondTrust, Secret Server, HashiCorp Vault, AWS Secrets Manager, Azure Key Vault, GCP.", "status": "pending"},
    {"id": "12", "num": "12", "name": "NHI Classification",                "phases": ["P1"],          "weeks": "4-5",  "desc": "7-subtype NHI classification with 5-signal weighted scoring. Identifies service accounts, app identities, CI/CD tokens, cloud credentials.", "status": "pending"},
    {"id": "13", "num": "13", "name": "Platform Plugin Validator",         "phases": ["P2", "P4"],    "weeks": "7,13", "desc": "Validates CyberArk CPM platform plugins against KeeperPAM record types. Exports custom platforms and imports to KeeperPAM.", "status": "pending"},
    {"id": "14", "num": "14", "name": "Application Onboarding",            "phases": ["P3", "P5"],    "weeks": "10-20","desc": "10-step app onboarding pipeline: vault creation → permissions → AppID → account creation → CPM rotation setup.", "status": "pending"},
    {"id": "15", "num": "15", "name": "Hybrid Fleet Manager",              "phases": ["P5", "P6"],    "weeks": "15-26","desc": "Manages mixed on-prem CyberArk + KeeperPAM state during parallel running. Detects stuck accounts (no rotation 48h+).", "status": "pending"},
]

_GATES = [
    {"id": "yc-p0", "name": "YC-P0 — Environment Ready",       "phase": "p0", "week": 2,  "status": "pending", "approvers": ["iOPEX Lead", "Client Infra"],      "description": "All preflight checks passing, service accounts created, network paths confirmed.", "inputs": ["preflight_report", "network_test_results"], "unlocks": "P1 Discovery"},
    {"id": "yc-p1", "name": "YC-P1 — Discovery Complete",      "phase": "p1", "week": 6,  "status": "pending", "approvers": ["iOPEX Lead", "Client Security"],    "description": "Full asset inventory, NHI classification complete, permission loss report reviewed and accepted.", "inputs": ["discovery_report", "nhi_report", "permission_loss_report"], "unlocks": "P2 Staging"},
    {"id": "yc-p2", "name": "YC-P2 — Staging Validated",       "phase": "p2", "week": 9,  "status": "pending", "approvers": ["iOPEX Lead", "Client PAM Admin"],   "description": "All 10 staging assertions passed. Zero hard blocks. Platform plugins validated.", "inputs": ["staging_validation_report", "platform_plugin_report"], "unlocks": "P3 Vault Migration"},
    {"id": "yc-p3", "name": "YC-P3 — Vaults & Permissions",    "phase": "p3", "week": 12, "status": "pending", "approvers": ["iOPEX Lead", "Client Security"],    "description": "All vaults created, permissions applied with zero escalations. App onboarding pipeline verified.", "inputs": ["vault_creation_report", "permission_apply_report"], "unlocks": "P4 Pilot"},
    {"id": "yc-p4", "name": "YC-P4 — Pilot Approved",          "phase": "p4", "week": 14, "status": "pending", "approvers": ["iOPEX Lead", "Client Operations"],  "description": "Wave 1 ETL complete, heartbeat ≥ 95%, zero ETL failures.", "inputs": ["etl_pilot_report", "heartbeat_pilot_report"], "unlocks": "P5 Production Waves"},
    {"id": "yc-p5", "name": "YC-P5 — All Waves Complete",      "phase": "p5", "week": 20, "status": "pending", "approvers": ["iOPEX Lead", "App Teams", "CISO"],   "description": "All 5 waves migrated. Integration repointing confirmed by all app teams. Compliance evidence collected.", "inputs": ["etl_production_report", "integration_scan_report", "compliance_report"], "unlocks": "P6 Parallel Running"},
    {"id": "yc-p6", "name": "YC-P6 — Cutover Confirmed",       "phase": "p6", "week": 26, "status": "pending", "approvers": ["CISO", "Client Executive", "iOPEX"], "description": "100% fleet migrated, 100% heartbeat, 0 CyberArk patterns remaining. Cutover completed.", "inputs": ["fleet_report", "final_heartbeat", "final_integration_scan"], "unlocks": "P7 Decommission"},
    {"id": "yc-p7", "name": "YC-P7 — Project Close-Out",       "phase": "p7", "week": 29, "status": "pending", "approvers": ["Client Executive", "iOPEX PMO"],    "description": "Audit log archived, CyberArk decommissioned, knowledge transfer complete, compliance report signed.", "inputs": ["final_compliance_report", "audit_archive_confirmation", "kt_sign_off"], "unlocks": "Project Complete"},
]

_WAVES = [
    {"id": "Wave 1", "name": "Test / Dev", "type": "Low Risk Accounts",       "risk": "low",      "agents": [{"num": "04"}, {"num": "05"}], "account_count": 0, "account_pct": "0%", "etl_steps": ["FREEZE", "EXPORT", "TRANSFORM", "VAULT", "IMPORT", "HEARTBEAT", "UNFREEZE"], "status": "pending", "pass_rate": None},
    {"id": "Wave 2", "name": "Standard Users", "type": "Standard User Accounts", "risk": "medium", "agents": [{"num": "04"}, {"num": "05"}, {"num": "06"}], "account_count": 0, "account_pct": "0%", "etl_steps": ["FREEZE", "EXPORT", "TRANSFORM", "VAULT", "IMPORT", "HEARTBEAT", "UNFREEZE"], "status": "pending", "pass_rate": None},
    {"id": "Wave 3", "name": "Infrastructure", "type": "Infrastructure Accounts", "risk": "high",  "agents": [{"num": "04"}, {"num": "05"}, {"num": "06"}], "account_count": 0, "account_pct": "0%", "etl_steps": ["FREEZE", "EXPORT", "TRANSFORM", "VAULT", "IMPORT", "HEARTBEAT", "UNFREEZE"], "status": "pending", "pass_rate": None},
    {"id": "Wave 4", "name": "NHIs", "type": "Non-Human Identities",          "risk": "high",     "agents": [{"num": "04"}, {"num": "05"}, {"num": "12"}], "account_count": 0, "account_pct": "0%", "etl_steps": ["FREEZE", "EXPORT", "TRANSFORM", "VAULT", "IMPORT", "HEARTBEAT", "UNFREEZE"], "status": "pending", "pass_rate": None},
    {"id": "Wave 5", "name": "Critical Privileged", "type": "Critical / Privileged Accounts", "risk": "critical", "agents": [{"num": "04"}, {"num": "05"}, {"num": "07"}], "account_count": 0, "account_pct": "0%", "etl_steps": ["FREEZE", "EXPORT", "TRANSFORM", "VAULT", "IMPORT", "HEARTBEAT", "UNFREEZE"], "status": "pending", "pass_rate": None},
]


# ── Phase status mapping ────────────────────────────────────────────────────

_PHASE_STATUS_MAP = {
    "completed":   "complete",
    "in_progress": "active",
    "pending":     "pending",
}

_PHASE_ID_MAP = {
    "P0": "p0", "P1": "p1", "P2": "p2", "P3": "p3",
    "P4": "p4", "P5": "p5", "P6": "p6", "P7": "p7",
}


class DashboardExporter:
    """Builds and publishes the live dashboard status blob."""

    BLOB_CONTAINER = "dashboard"
    BLOB_NAME = "status.json"

    def __init__(self, config: dict, state, output_dir: str):
        self.config = config
        self.state = state
        self.output_dir = Path(output_dir)
        self.reports_dir = self.output_dir.parent / "reports"

    # ── Public entry point ─────────────────────────────────────────────────

    def export(self) -> bool:
        """Build status.json and upload to Azure Blob. Returns True on success."""
        try:
            payload = self._build_payload()
            blob_url = self._upload(payload)
            if blob_url:
                logger.info("Dashboard status exported → %s", blob_url)
            else:
                logger.info("Dashboard status written locally (no blob URL configured)")
            return True
        except Exception as e:
            # Non-critical — migration continues even if dashboard export fails
            logger.warning("Dashboard export failed (non-critical): %s", e)
            return False

    # ── Payload builder ────────────────────────────────────────────────────

    def _build_payload(self) -> dict:
        now = datetime.now(timezone.utc).isoformat()
        summary = self.state.summary() if self.state else {}

        current_phase_key = summary.get("current_phase") or "P0"
        current_phase_id  = _PHASE_ID_MAP.get(current_phase_key, "p0")
        phase_statuses    = summary.get("phases", {})

        # Discovery report — account totals, NHI counts
        disc  = self._latest_report("agent_01_discovery")
        gap   = self._latest_report("agent_02_gap_analysis")
        etl   = self._latest_report("agent_04_etl")
        hb    = self._latest_report("agent_05_heartbeat")
        integ = self._latest_report("agent_06_integration")
        comp  = self._latest_report("agent_07_compliance")
        fleet = self._latest_report("agent_15_hybrid_fleet")

        total_accounts  = disc.get("total_accounts", 0)  if disc  else 0
        nhi_accounts    = disc.get("nhi_count", 0)       if disc  else 0
        integrations    = integ.get("integration_count", 0) if integ else 0
        accounts_migrated = etl.get("imported_count", 0) if etl else 0
        accounts_failed   = etl.get("failed_count", 0)   if etl else 0
        hb_pass_rate    = hb.get("pass_rate", None)      if hb   else None
        controls_evidenced = comp.get("total_controls_evidenced", 0) if comp else 0
        open_gaps       = len(comp.get("open_gaps", []))  if comp else 0
        stuck_accounts  = len(fleet.get("stuck_accounts", [])) if fleet else 0

        gates_passed = sum(
            1 for p, s in phase_statuses.items() if s == "completed"
        )

        # Build phases timeline
        phases = []
        for p in _PHASES:
            raw = phase_statuses.get(p["label"], "pending")
            status = _PHASE_STATUS_MAP.get(raw, "pending")
            phases.append({**p, "status": status})

        # Build agents with live status
        agents = self._build_agents(phase_statuses, current_phase_key)

        # Build gates with live status
        gates = self._build_gates(phase_statuses, current_phase_key)

        # Build waves with live ETL data
        waves = self._build_waves(etl, hb)

        # Compliance summary
        comp_frameworks = comp.get("frameworks_evidenced", ["PCI-DSS", "NIST 800-53", "HIPAA", "SOX"]) if comp else []

        # Recent activity from audit log (last 10 entries)
        recent_activity = self._recent_audit_entries(10)

        # Migration progress percentage
        migrated_pct = round(accounts_migrated / total_accounts * 100, 1) if total_accounts > 0 else 0

        return {
            "meta": {
                "migration_id":  summary.get("migration_id", ""),
                "last_updated":  now,
                "current_phase": current_phase_key,
                "export_version": 1,
            },
            "dashboard": {
                "stats": {
                    "total_accounts":  total_accounts,
                    "nhi_accounts":    nhi_accounts,
                    "integrations":    integrations,
                    "total_waves":     5,
                    "gates_passed":    gates_passed,
                    "total_gates":     7,
                    "agents_active":   self._count_active_agents(phase_statuses, current_phase_key),
                    "current_phase":   {"id": current_phase_id, "name": self._phase_name(current_phase_key)},
                    "accounts_migrated": accounts_migrated,
                    "accounts_failed":   accounts_failed,
                    "migration_pct":     migrated_pct,
                    "heartbeat_pass_rate": hb_pass_rate,
                    "controls_evidenced":  controls_evidenced,
                    "open_compliance_gaps": open_gaps,
                    "stuck_accounts":   stuck_accounts,
                },
                "timeline": phases,
                "risks":    self._build_risks(gap),
                "predictions": self._build_predictions(phase_statuses, accounts_migrated, total_accounts),
            },
            "agents":   agents,
            "gates":    gates,
            "waves":    waves,
            "checkpoints": {
                "stats": {
                    "passed":  gates_passed,
                    "pending": 7 - gates_passed,
                    "total":   7,
                },
                "list": gates,
            },
            "accounts": {
                "total":    total_accounts,
                "migrated": accounts_migrated,
                "failed":   accounts_failed,
                "pending":  max(0, total_accounts - accounts_migrated - accounts_failed),
                "nhi":      nhi_accounts,
                "migration_pct": migrated_pct,
            },
            "compliance": {
                "frameworks":         comp_frameworks,
                "controls_evidenced": controls_evidenced,
                "open_gaps":          open_gaps,
            },
            "activity": recent_activity,
        }

    # ── Sub-builders ───────────────────────────────────────────────────────

    def _build_agents(self, phase_statuses: dict, current_phase: str) -> List[dict]:
        completed_phases = {p for p, s in phase_statuses.items() if s == "completed"}
        active_phases    = {p for p, s in phase_statuses.items() if s == "in_progress"}

        agents = []
        for a in _AGENTS:
            agent_phases = a["phases"]
            if any(p in completed_phases for p in agent_phases):
                status = "complete"
            elif any(p in active_phases for p in agent_phases):
                status = "active"
            else:
                status = "pending"
            agents.append({**a, "status": status})
        return agents

    def _build_gates(self, phase_statuses: dict, current_phase: str) -> List[dict]:
        completed_phases = {p for p, s in phase_statuses.items() if s == "completed"}
        active_phases    = {p for p, s in phase_statuses.items() if s == "in_progress"}

        gates = []
        for g in _GATES:
            phase_key = g["phase"].upper()
            if phase_key in completed_phases:
                status = "passed"
            elif phase_key in active_phases:
                status = "active"
            else:
                status = "pending"
            gates.append({**g, "status": status, "context_a": g["description"], "context_b": g["description"]})
        return gates

    def _build_waves(self, etl: Optional[dict], hb: Optional[dict]) -> List[dict]:
        waves = []
        total = (etl.get("accounts_processed", 0) if etl else 0) or 1  # avoid /0

        for i, w in enumerate(_WAVES):
            wave_data = {}
            if etl:
                wave_key = f"wave_{i+1}"
                wave_data = etl.get("waves", {}).get(wave_key, {})
            count    = wave_data.get("imported_count", 0)
            pct      = f"{round(count / total * 100, 1)}%" if total > 0 else "0%"
            passed   = wave_data.get("pass_rate")
            if wave_data.get("status") == "complete":
                status = "complete"
            elif wave_data.get("status") == "in_progress":
                status = "active"
            else:
                status = w["status"]
            waves.append({**w, "account_count": count, "account_pct": pct, "status": status, "pass_rate": passed})
        return waves

    def _build_risks(self, gap: Optional[dict]) -> List[dict]:
        if not gap:
            return [
                {"level": "medium", "title": "Gap analysis pending", "desc": "Run P1 discovery to populate risk register."},
            ]
        risks = []
        for item in gap.get("gaps", [])[:6]:
            risks.append({
                "level": item.get("risk", "medium").lower(),
                "title": item.get("domain", ""),
                "desc":  item.get("finding", ""),
            })
        return risks or [{"level": "low", "title": "No critical risks", "desc": "Gap analysis complete — no critical gaps identified."}]

    def _build_predictions(self, phase_statuses: dict, migrated: int, total: int) -> List[dict]:
        completed_count = sum(1 for s in phase_statuses.values() if s == "completed")
        pct = round(migrated / total * 100, 0) if total > 0 else 0
        return [
            {"label": "Phases Complete",     "value": f"{completed_count}/8"},
            {"label": "Accounts Migrated",   "value": f"{pct:.0f}%"},
        ]

    def _count_active_agents(self, phase_statuses: dict, current_phase: str) -> int:
        if current_phase is None:
            return 0
        from coordinator import PHASE_SEQUENCE
        active_keys = PHASE_SEQUENCE.get(current_phase, [])
        return len(active_keys)

    # ── File readers ───────────────────────────────────────────────────────

    def _latest_report(self, agent_prefix: str) -> Optional[dict]:
        """Return the most recent agent report JSON matching the prefix."""
        pattern = str(self.reports_dir / f"{agent_prefix}_*.json")
        import glob as _glob
        matches = sorted(_glob.glob(pattern))
        if not matches:
            return None
        try:
            with open(matches[-1]) as f:
                return json.load(f)
        except Exception:
            return None

    def _recent_audit_entries(self, n: int) -> List[dict]:
        """Return last N audit log entries as activity feed items."""
        audit_path = self.output_dir.parent / "logs" / "audit.jsonl"
        if not audit_path.exists():
            return []
        entries = []
        try:
            lines = audit_path.read_text().strip().splitlines()
            for line in lines[-n:]:
                try:
                    e = json.loads(line)
                    entries.append({
                        "timestamp": e.get("timestamp", ""),
                        "event":     f"[{e.get('agent_id', '')}] {e.get('event', '')}",
                        "level":     "error" if "error" in e.get("event", "").lower() else "info",
                    })
                except Exception:
                    pass
        except Exception:
            pass
        return list(reversed(entries))

    def _phase_name(self, phase_key: str) -> str:
        names = {p["label"]: p["name"] for p in _PHASES}
        return names.get(phase_key, phase_key)

    # ── Azure Blob upload ──────────────────────────────────────────────────

    def _upload(self, payload: dict) -> Optional[str]:
        """Upload payload to Azure Blob Storage. Returns public URL or None."""
        # Write local fallback regardless
        local_path = self.output_dir.parent / "reports" / "dashboard_status.json"
        try:
            local_path.parent.mkdir(parents=True, exist_ok=True)
            with open(local_path, "w") as f:
                json.dump(payload, f, indent=2)
        except Exception as e:
            logger.debug("Local dashboard write failed: %s", e)

        # Upload to Azure Blob
        dash_url = (
            os.environ.get("DASHBOARD_STORAGE_URL")
            or self.config.get("dashboard", {}).get("storage_url", "")
        )
        if not dash_url:
            return None

        try:
            from azure.storage.blob import BlobClient
            from azure.identity import DefaultAzureCredential

            blob_url = f"{dash_url.rstrip('/')}/{self.BLOB_CONTAINER}/{self.BLOB_NAME}"
            cred = DefaultAzureCredential()
            client = BlobClient.from_blob_url(blob_url, credential=cred)
            data = json.dumps(payload, indent=2).encode()
            client.upload_blob(data, overwrite=True, content_settings=_blob_content_settings())
            return blob_url
        except ImportError:
            logger.debug("azure-storage-blob not installed — skipping blob upload")
            return None
        except Exception as e:
            logger.warning("Blob upload failed: %s", e)
            return None


def _blob_content_settings():
    """Returns ContentSettings for JSON blob with CORS-friendly headers."""
    try:
        from azure.storage.blob import ContentSettings
        return ContentSettings(
            content_type="application/json",
            cache_control="no-cache, max-age=0",
        )
    except ImportError:
        return None

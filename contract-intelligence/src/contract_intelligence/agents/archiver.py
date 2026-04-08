import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from ..clients.gmail_client import GmailClient
from ..models.state import PipelineState, PipelineStep

logger = logging.getLogger(__name__)


class ArchiverAgent:
    def __init__(self, gmail: GmailClient, archive_dir: Path, audit_file: Path,
                 revops_email: str):
        self.gmail = gmail
        self.archive_dir = archive_dir
        self.audit_file = audit_file
        self.revops_email = revops_email

    def send_executed_contract(self, state: PipelineState) -> bool:
        """Email executed PDF to all parties."""
        logger.info("[%s] Archiver: emailing executed contract...", state.contract_id)
        executed_path = state.get("executed_pdf_path")
        if not executed_path or not Path(executed_path).exists():
            logger.warning("[%s] Archiver: no executed PDF — skipping email", state.contract_id)
            state.advance(PipelineStep.EMAIL, "Skipped (no executed PDF)")
            return True

        client_email = state.get("client_email") or state.source_email
        recipients = [r for r in [client_email, self.revops_email] if r]

        quote_data = state.get("extracted_quote") or {}
        client_name = quote_data.get("client_name") or "Client"
        amount = quote_data.get("total_amount")
        currency = quote_data.get("currency", "USD")

        body = f"""Dear {client_name},

Please find the fully executed contract attached.

Contract ID: {state.contract_id}
Amount: {currency} {f'{amount:,.2f}' if amount else '—'}

This contract is now legally binding. A copy has been archived for your records.

Thank you,
Contract Intelligence
"""
        try:
            self.gmail.send_email(
                to=recipients,
                subject=f"Executed Contract — {state.contract_id}",
                body=body,
                attachment_path=Path(executed_path),
            )
            state.advance(PipelineStep.EMAIL, f"Sent to {recipients}")
        except Exception as e:
            logger.error("[%s] Archiver: email failed: %s", state.contract_id, e)
            state.advance(PipelineStep.EMAIL, f"Email failed (non-fatal): {e}")
        return True

    def archive(self, state: PipelineState) -> bool:
        """Write final archive entry and append to audit JSONL."""
        logger.info("[%s] Archiver: writing audit trail...", state.contract_id)
        self.archive_dir.mkdir(parents=True, exist_ok=True)
        self.audit_file.parent.mkdir(parents=True, exist_ok=True)

        audit_record = {
            "contract_id": state.contract_id,
            "ts": datetime.now(timezone.utc).isoformat(),
            "source_email": state.source_email,
            "steps": [s.model_dump() for s in state.steps],
            "risk_flag": (state.get("risk_report") or {}).get("risk_flag"),
            "review_decision": state.get("review_decision"),
            "executed_pdf": state.get("executed_pdf_path"),
            "final_status": state.status,
        }

        with open(self.audit_file, "a") as f:
            f.write(json.dumps(audit_record) + "\n")

        state.advance(PipelineStep.ARCHIVE, "Audit trail written")
        logger.info("[%s] Archiver: audit record appended", state.contract_id)
        return True

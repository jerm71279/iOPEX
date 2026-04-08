import logging
from pathlib import Path
from ..clients.gmail_client import GmailClient
from ..models.state import PipelineState, PipelineStep

logger = logging.getLogger(__name__)


class IntakeAgent:
    def __init__(self, gmail: GmailClient, raw_dir: Path):
        self.gmail = gmail
        self.raw_dir = raw_dir

    def run(self, state: PipelineState) -> bool:
        """Poll Gmail for unread quote email with PDF. Save PDF to raw dir."""
        logger.info("[%s] Intake: polling Gmail...", state.contract_id)
        result = self.gmail.fetch_latest_quote_email()
        if not result:
            state.fail(PipelineStep.INTAKE, "No unread quote email with PDF attachment found")
            return False

        raw_path = self.raw_dir / state.contract_id
        raw_path.mkdir(parents=True, exist_ok=True)
        pdf_path = raw_path / "quote.pdf"
        pdf_path.write_bytes(result["pdf"])

        state.raw_pdf_path = str(pdf_path)
        state.source_email = result["sender"]
        state.set("email_subject", result["subject"])
        state.advance(PipelineStep.INTAKE, f"PDF saved from {result['sender']}")
        logger.info("[%s] Intake: PDF received from %s", state.contract_id, result["sender"])
        return True

    def run_from_file(self, state: PipelineState, pdf_path: Path, sender: str = "manual@trigger") -> bool:
        """Inject a PDF directly (for testing / manual trigger)."""
        raw_path = self.raw_dir / state.contract_id
        raw_path.mkdir(parents=True, exist_ok=True)
        dest = raw_path / "quote.pdf"
        dest.write_bytes(pdf_path.read_bytes())
        state.raw_pdf_path = str(dest)
        state.source_email = sender
        state.advance(PipelineStep.INTAKE, f"PDF injected from {sender}")
        return True

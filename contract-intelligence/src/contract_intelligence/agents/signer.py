import logging
from pathlib import Path
from ..clients.docuseal_client import DocuSealClient
from ..models.contract import ExtractedQuote
from ..models.state import PipelineState, PipelineStep

logger = logging.getLogger(__name__)


class SignerAgent:
    def __init__(self, docuseal: DocuSealClient, app_base_url: str = "http://localhost:8000"):
        self.docuseal = docuseal
        self.app_base_url = app_base_url

    def run(self, state: PipelineState) -> bool:
        logger.info("[%s] Signer: initiating signing workflow...", state.contract_id)

        quote_data = state.get("extracted_quote")
        quote = ExtractedQuote(**quote_data) if quote_data else None
        client_email = (quote.client_email if quote else None) or state.source_email or "client@example.com"
        client_name = (quote.client_name if quote else None) or "Client"

        try:
            submission = self.docuseal.create_submission(
                contract_id=state.contract_id,
                client_email=client_email,
                client_name=client_name,
                app_base_url=self.app_base_url,
            )
        except Exception as e:
            state.fail(PipelineStep.SIGN, f"Signing submission failed: {e}")
            return False

        submission_id = submission.get("id")
        signing_url = submission.get("signing_url", "")
        mode = submission.get("mode", "demo")

        state.set("docuseal_submission_id", submission_id)
        state.set("signing_url", signing_url)
        state.set("signing_mode", mode)
        state.set("client_email", client_email)

        mode_label = "demo signing page" if mode == "demo" else "DocuSeal"
        state.advance(PipelineStep.SIGN,
                      f"Submission {submission_id} → {mode_label} — {signing_url}")
        logger.info("[%s] Signer: submission %s (%s) — signing URL: %s",
                    state.contract_id, submission_id, mode, signing_url)
        return True

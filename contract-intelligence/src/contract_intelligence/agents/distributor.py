import logging
import shutil
from pathlib import Path
from ..clients.docuseal_client import DocuSealClient
from ..models.state import PipelineState, PipelineStep

logger = logging.getLogger(__name__)


class DistributorAgent:
    def __init__(self, docuseal: DocuSealClient, archive_dir: Path,
                 revops_email: str, app_base_url: str = "http://localhost:8000",
                 poll_interval: int = 30):
        self.docuseal = docuseal
        self.archive_dir = archive_dir
        self.revops_email = revops_email
        self.app_base_url = app_base_url
        self.poll_interval = poll_interval

    def download_signed(self, state: PipelineState) -> bool:
        """Download (or copy) client-signed PDF."""
        logger.info("[%s] Distributor: retrieving signed PDF...", state.contract_id)
        submission_id = state.get("docuseal_submission_id")
        if not submission_id:
            state.fail(PipelineStep.DOWNLOAD, "No submission ID")
            return False

        self.archive_dir.mkdir(parents=True, exist_ok=True)
        signed_path = self.archive_dir / f"{state.contract_id}_signed.pdf"

        if self.docuseal.is_demo_submission(str(submission_id)):
            # Demo mode: copy generated contract PDF as "signed"
            generated_path = state.get("contract_pdf_path")
            if generated_path and Path(generated_path).exists():
                shutil.copy2(generated_path, signed_path)
                logger.info("[%s] Distributor: demo mode — using generated PDF as signed",
                            state.contract_id)
            else:
                state.fail(PipelineStep.DOWNLOAD, "Generated PDF not found for demo copy")
                return False
        else:
            try:
                pdf_bytes = self.docuseal.download_document(submission_id)
                signed_path.write_bytes(pdf_bytes)
            except Exception as e:
                state.fail(PipelineStep.DOWNLOAD, f"Download failed: {e}")
                return False

        state.set("signed_pdf_path", str(signed_path))
        state.advance(PipelineStep.DOWNLOAD, f"Signed PDF: {signed_path.name}")
        logger.info("[%s] Distributor: signed PDF at %s", state.contract_id, signed_path)
        return True

    def create_counter_sign(self, state: PipelineState) -> bool:
        """Create RevOps counter-signature submission."""
        logger.info("[%s] Distributor: initiating counter-sign...", state.contract_id)

        try:
            submission = self.docuseal.create_submission(
                contract_id=f"{state.contract_id}-countersign",
                client_email=self.revops_email,
                client_name="RevOps",
                app_base_url=self.app_base_url,
            )
        except Exception as e:
            state.fail(PipelineStep.COUNTER_SIGN, f"Counter-sign submission failed: {e}")
            return False

        sub_id = submission.get("id")
        signing_url = submission.get("signing_url", "")
        mode = submission.get("mode", "demo")

        state.set("docuseal_counter_submission_id", sub_id)
        state.set("counter_sign_url", signing_url)
        state.advance(PipelineStep.COUNTER_SIGN,
                      f"Counter-sign → {self.revops_email} | {signing_url}")
        logger.info("[%s] Distributor: counter-sign submission %s (%s)",
                    state.contract_id, sub_id, mode)
        return True

    def wait_for_counter_sign_and_download(self, state: PipelineState) -> bool:
        """Wait for RevOps counter-sign and produce executed PDF."""
        sub_id = state.get("docuseal_counter_submission_id")
        signed_path = state.get("signed_pdf_path")
        executed_path = self.archive_dir / f"{state.contract_id}_executed.pdf"

        if self.docuseal.is_demo_submission(str(sub_id)):
            # Demo mode: counter-sign auto-completes — copy signed PDF as executed
            if signed_path and Path(signed_path).exists():
                shutil.copy2(signed_path, executed_path)
                logger.info("[%s] Distributor: demo mode — counter-sign auto-completed",
                            state.contract_id)
            else:
                state.fail(PipelineStep.COUNTER_SIGN, "Signed PDF missing for demo counter-sign")
                return False
        else:
            try:
                self.docuseal.poll_until_complete(sub_id, poll_interval=self.poll_interval)
                pdf_bytes = self.docuseal.download_document(sub_id)
                executed_path.write_bytes(pdf_bytes)
            except Exception as e:
                state.fail(PipelineStep.COUNTER_SIGN, f"Counter-sign failed: {e}")
                return False

        state.set("executed_pdf_path", str(executed_path))
        state.advance(PipelineStep.COUNTER_SIGN, f"Executed contract: {executed_path.name}")
        logger.info("[%s] Distributor: executed PDF at %s", state.contract_id, executed_path)
        return True

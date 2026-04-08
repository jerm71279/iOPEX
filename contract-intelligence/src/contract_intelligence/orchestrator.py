import asyncio
import logging
import uuid
from pathlib import Path
from typing import Optional

from .config import Settings
from .models.state import PipelineState, PipelineStep
from .models.contract import RiskFlag, ReviewDecision
from .clients.gmail_client import GmailClient
from .clients.anthropic_client import AnthropicClient
from .clients.pdfshift_client import PDFShiftClient
from .clients.docuseal_client import DocuSealClient
from .agents.intake import IntakeAgent
from .agents.extractor import ExtractorAgent
from .agents.risk import RiskAgent
from .agents.generator import GeneratorAgent
from .agents.signer import SignerAgent
from .agents.monitor import MonitorAgent
from .agents.distributor import DistributorAgent
from .agents.archiver import ArchiverAgent
from .agents.obligation import ObligationAgent

logger = logging.getLogger(__name__)


class Orchestrator:
    def __init__(self, settings: Settings):
        self.settings = settings
        settings.ensure_dirs()

        self.gmail = GmailClient(
            user=settings.gmail_user,
            app_password=settings.gmail_app_password,
            imap_host=settings.gmail_imap_host,
        )
        self.claude = AnthropicClient(api_key=settings.anthropic_api_key, model=settings.claude_model)
        self.pdfshift = PDFShiftClient(api_key=settings.pdfshift_api_key)
        demo_mode = settings.demo_signing_mode or not settings.docuseal_template_id
        self.docuseal = DocuSealClient(
            base_url=settings.docuseal_base_url,
            api_key=settings.docuseal_api_key,
            webhook_secret=settings.docuseal_webhook_secret,
            template_id=settings.docuseal_template_id,
            demo_mode=demo_mode,
        )

        template_dir = Path(__file__).parent / "templates"
        self.intake = IntakeAgent(self.gmail, settings.state_dir / "raw")
        self.extractor = ExtractorAgent(self.claude)
        self.risk = RiskAgent(self.claude)
        self.generator = GeneratorAgent(self.pdfshift, template_dir, settings.archive_dir)
        self.signer = SignerAgent(self.docuseal, settings.app_base_url)
        self.monitor = MonitorAgent(
            self.docuseal,
            use_polling=settings.docuseal_use_polling,
            poll_interval=settings.docuseal_poll_interval,
        )
        self.distributor = DistributorAgent(
            self.docuseal, settings.archive_dir, settings.revops_email,
            app_base_url=settings.app_base_url,
        )
        self.archiver = ArchiverAgent(
            self.gmail, settings.archive_dir, settings.audit_file, settings.revops_email,
        )
        self.obligation = ObligationAgent(self.claude)

        # pending review futures: contract_id -> asyncio.Future
        self._review_futures: dict[str, asyncio.Future] = {}

    def new_contract_id(self) -> str:
        return f"CNT-{uuid.uuid4().hex[:8].upper()}"

    def load_state(self, contract_id: str) -> PipelineState:
        return PipelineState.load(contract_id, self.settings.state_dir)

    def save_state(self, state: PipelineState):
        state.save(self.settings.state_dir)

    async def run(self, contract_id: Optional[str] = None,
                  pdf_path: Optional[Path] = None,
                  sender: str = "trigger@manual") -> PipelineState:
        """Run the full pipeline from intake to completion."""
        contract_id = contract_id or self.new_contract_id()
        state = PipelineState.new(contract_id, source_email=sender)
        self.save_state(state)
        logger.info("[%s] Pipeline started", contract_id)

        try:
            # --- BOT A: Intelligence ---
            # Step 1: Intake
            state.current_step = PipelineStep.INTAKE
            if pdf_path:
                ok = self.intake.run_from_file(state, pdf_path, sender)
            else:
                ok = self.intake.run(state)
            self.save_state(state)
            if not ok:
                return state

            # Step 2: Extract
            if not self.extractor.run(state):
                self.save_state(state)
                return state
            self.save_state(state)

            # Step 3: Risk
            if not self.risk.run(state):
                self.save_state(state)
                return state
            self.save_state(state)

            # Step 4: Gateway
            risk_data = state.get("risk_report") or {}
            risk_flag = risk_data.get("risk_flag", RiskFlag.MEDIUM)
            state.advance(PipelineStep.GATEWAY, f"Risk flag: {risk_flag}")
            self.save_state(state)

            if risk_flag == RiskFlag.HIGH:
                await self._reject(state, "HIGH risk — automated rejection")
                self.save_state(state)
                return state

            if risk_flag == RiskFlag.MEDIUM:
                ok = await self._human_review(state)
                self.save_state(state)
                if not ok:
                    return state

            # Step 5: Generate PDF
            if not self.generator.run(state):
                self.save_state(state)
                return state
            self.save_state(state)

            # Step 6: Sign
            if not self.signer.run(state):
                self.save_state(state)
                return state
            self.save_state(state)

            # --- BOT B: Distribution ---
            # Step 7: Monitor
            if not await self.monitor.wait_for_signature(state):
                self.save_state(state)
                return state
            self.save_state(state)

            # Step 8: Download signed PDF
            if not self.distributor.download_signed(state):
                self.save_state(state)
                return state
            self.save_state(state)

            # Step 9: Counter-sign
            if not self.distributor.create_counter_sign(state):
                self.save_state(state)
                return state
            if not self.distributor.wait_for_counter_sign_and_download(state):
                self.save_state(state)
                return state
            self.save_state(state)

            # Step 10: Email + Archive
            self.archiver.send_executed_contract(state)
            self.archiver.archive(state)
            self.save_state(state)

            # Step 11: Obligations (non-blocking)
            self.obligation.run(state)
            self.save_state(state)

            state.status = "complete"
            state.current_step = PipelineStep.COMPLETE
            self.save_state(state)
            logger.info("[%s] Pipeline COMPLETE", contract_id)

        except Exception as e:
            logger.exception("[%s] Pipeline error: %s", contract_id, e)
            state.fail(state.current_step, str(e))
            self.save_state(state)

        return state

    async def _reject(self, state: PipelineState, reason: str):
        state.current_step = PipelineStep.REJECTED
        state.status = "rejected"
        state.advance(PipelineStep.REJECTED, reason)
        client_email = state.get("client_email") or state.source_email
        if client_email:
            try:
                self.gmail.send_email(
                    to=[client_email],
                    subject=f"Contract Not Approved — {state.contract_id}",
                    body=f"Your submitted contract ({state.contract_id}) could not be approved at this time.\n\nReason: {reason}\n\nPlease contact RevOps for assistance.",
                )
            except Exception as e:
                logger.error("[%s] Rejection email failed: %s", state.contract_id, e)
        logger.info("[%s] Pipeline REJECTED: %s", state.contract_id, reason)

    async def _human_review(self, state: PipelineState) -> bool:
        """Pause pipeline, notify RevOps, wait for review decision."""
        state.current_step = PipelineStep.HUMAN_REVIEW
        state.advance(PipelineStep.HUMAN_REVIEW, "Awaiting RevOps review")
        self.save_state(state)

        review_url = f"{self.settings.app_base_url}/review/{state.contract_id}"
        risk_data = state.get("risk_report") or {}
        try:
            self.gmail.send_review_notification(
                revops_email=self.settings.revops_email,
                contract_id=state.contract_id,
                review_url=review_url,
                risk_summary=risk_data.get("summary", ""),
            )
        except Exception as e:
            logger.error("[%s] Review notification failed: %s", state.contract_id, e)

        # Register future — will be resolved by POST /review/{id}
        loop = asyncio.get_event_loop()
        future: asyncio.Future = loop.create_future()
        self._review_futures[state.contract_id] = future

        try:
            decision_data = await asyncio.wait_for(future, timeout=172800)  # 48h
        except asyncio.TimeoutError:
            state.fail(PipelineStep.HUMAN_REVIEW, "Review timed out after 48h")
            return False
        finally:
            self._review_futures.pop(state.contract_id, None)

        decision = decision_data.get("decision")
        notes = decision_data.get("notes", "")
        state.set("review_decision", decision)
        state.set("review_notes", notes)

        if decision == ReviewDecision.DECLINE:
            await self._reject(state, f"Declined by RevOps: {notes}")
            return False

        state.advance(PipelineStep.HUMAN_REVIEW, f"Approved by RevOps ({decision}): {notes}")
        return True

    def submit_review(self, contract_id: str, decision: str, notes: str = ""):
        """Called by POST /review/{id} to resolve the pending review future."""
        future = self._review_futures.get(contract_id)
        if not future or future.done():
            raise ValueError(f"No pending review for contract {contract_id}")
        future.set_result({"decision": decision, "notes": notes})

    def notify_docuseal_complete(self, contract_id: str, submission_id: int):
        """Called by POST /webhooks/docuseal to unblock the monitor agent."""
        self.monitor.notify_complete(contract_id, submission_id)

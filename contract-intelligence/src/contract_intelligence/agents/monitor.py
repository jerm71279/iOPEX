import asyncio
import logging
from ..clients.docuseal_client import DocuSealClient
from ..models.state import PipelineState, PipelineStep

logger = logging.getLogger(__name__)


class MonitorAgent:
    """Waits for DocuSeal client signature — either via webhook event or polling."""

    def __init__(self, docuseal: DocuSealClient, use_polling: bool = False,
                 poll_interval: int = 30):
        self.docuseal = docuseal
        self.use_polling = use_polling
        self.poll_interval = poll_interval
        # webhook_events: contract_id -> asyncio.Event (set when webhook fires)
        self._events: dict[str, asyncio.Event] = {}

    def register_contract(self, contract_id: str) -> asyncio.Event:
        event = asyncio.Event()
        self._events[contract_id] = event
        return event

    def notify_complete(self, contract_id: str, submission_id: int):
        """Called by the webhook handler when DocuSeal fires a completion event."""
        if contract_id in self._events:
            self._events[contract_id].set()
            logger.info("[%s] Monitor: webhook received — submission %s complete",
                        contract_id, submission_id)

    async def wait_for_signature(self, state: PipelineState, timeout: int = 172800) -> bool:
        """Async wait: webhook/event mode or polling fallback."""
        state.advance(PipelineStep.MONITOR, "Waiting for client signature")
        submission_id = state.get("docuseal_submission_id")
        if not submission_id:
            state.fail(PipelineStep.MONITOR, "No submission ID in state")
            return False

        # Demo submissions can't be polled — always use event-based wait
        is_demo = str(submission_id).startswith("demo-")
        if self.use_polling and not is_demo:
            return await self._poll(state, submission_id, timeout)
        else:
            return await self._wait_webhook(state, submission_id, timeout)

    async def _wait_webhook(self, state: PipelineState, submission_id: int,
                            timeout: int) -> bool:
        event = self.register_contract(state.contract_id)
        try:
            await asyncio.wait_for(event.wait(), timeout=timeout)
            state.advance(PipelineStep.MONITOR, f"Webhook: submission {submission_id} signed")
            return True
        except asyncio.TimeoutError:
            state.fail(PipelineStep.MONITOR, f"Signature timeout after {timeout}s")
            return False
        finally:
            self._events.pop(state.contract_id, None)

    async def _poll(self, state: PipelineState, submission_id: int, timeout: int) -> bool:
        import time
        start = time.time()
        while time.time() - start < timeout:
            try:
                data = self.docuseal.get_submission(submission_id)
                if data.get("status") == "completed":
                    state.advance(PipelineStep.MONITOR, f"Poll: submission {submission_id} signed")
                    return True
                if data.get("status") in ("expired", "declined"):
                    state.fail(PipelineStep.MONITOR, f"Submission ended: {data.get('status')}")
                    return False
            except Exception as e:
                logger.warning("[%s] Monitor poll error: %s", state.contract_id, e)
            await asyncio.sleep(self.poll_interval)
        state.fail(PipelineStep.MONITOR, "Signature timeout (polling)")
        return False

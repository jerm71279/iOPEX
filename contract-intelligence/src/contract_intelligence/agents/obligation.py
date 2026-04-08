import logging
from pathlib import Path
from ..clients.anthropic_client import AnthropicClient
from ..models.state import PipelineState, PipelineStep

logger = logging.getLogger(__name__)


class ObligationAgent:
    def __init__(self, openai: AnthropicClient):
        self.openai = openai

    def run(self, state: PipelineState) -> bool:
        """GPT-4o post-execution parse: extract renewal dates, SLAs, termination terms."""
        logger.info("[%s] Obligation: extracting obligations from executed contract...",
                    state.contract_id)
        executed_path = state.get("executed_pdf_path")
        if not executed_path or not Path(executed_path).exists():
            logger.warning("[%s] Obligation: no executed PDF — skipping", state.contract_id)
            state.advance(PipelineStep.OBLIGATION, "Skipped (no executed PDF)")
            return True

        # Extract text from PDF via simple read (PDFs with embedded text)
        # For scanned PDFs, OCR would be needed — out of scope for Phase 1
        try:
            import pypdf
            reader = pypdf.PdfReader(executed_path)
            text = "\n".join(page.extract_text() or "" for page in reader.pages)
        except Exception as e:
            logger.warning("[%s] Obligation: PDF text extraction failed: %s", state.contract_id, e)
            state.advance(PipelineStep.OBLIGATION, f"Skipped (PDF text extraction failed: {e})")
            return True

        try:
            obligations = self.openai.extract_obligations(text)
        except Exception as e:
            logger.warning("[%s] Obligation: GPT-4o extraction failed: %s", state.contract_id, e)
            state.advance(PipelineStep.OBLIGATION, f"Partial (GPT-4o failed: {e})")
            return True

        state.set("obligations", obligations.model_dump())
        state.advance(PipelineStep.OBLIGATION,
                      f"Renewal: {obligations.renewal_date} | SLAs: {len(obligations.sla_clauses)}")
        logger.info("[%s] Obligation: renewal=%s, notice=%sd, slas=%d",
                    state.contract_id, obligations.renewal_date,
                    obligations.termination_notice_days, len(obligations.sla_clauses))
        return True

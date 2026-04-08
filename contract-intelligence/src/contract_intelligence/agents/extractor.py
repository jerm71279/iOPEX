import logging
from pathlib import Path
from ..clients.anthropic_client import AnthropicClient
from ..models.state import PipelineState, PipelineStep

logger = logging.getLogger(__name__)


class ExtractorAgent:
    def __init__(self, openai: AnthropicClient):
        self.openai = openai

    def run(self, state: PipelineState) -> bool:
        logger.info("[%s] Extractor: running GPT-4o vision extraction...", state.contract_id)
        pdf_path = Path(state.raw_pdf_path)
        if not pdf_path.exists():
            state.fail(PipelineStep.EXTRACT, f"PDF not found: {pdf_path}")
            return False

        try:
            quote = self.openai.extract_quote(pdf_path)
        except Exception as e:
            state.fail(PipelineStep.EXTRACT, f"GPT-4o extraction failed: {e}")
            return False

        state.set("extracted_quote", quote.model_dump())
        state.advance(PipelineStep.EXTRACT,
                      f"Extracted: {quote.client_name} / {quote.total_amount} {quote.currency}")
        logger.info("[%s] Extractor: %s — %s %s",
                    state.contract_id, quote.client_name, quote.total_amount, quote.currency)
        return True

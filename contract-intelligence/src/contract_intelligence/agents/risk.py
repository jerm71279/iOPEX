import logging
from ..clients.anthropic_client import AnthropicClient
from ..models.contract import ExtractedQuote, RiskFlag
from ..models.state import PipelineState, PipelineStep

logger = logging.getLogger(__name__)


class RiskAgent:
    def __init__(self, openai: AnthropicClient):
        self.openai = openai

    def run(self, state: PipelineState) -> bool:
        logger.info("[%s] Risk: assessing contract risk...", state.contract_id)
        quote_data = state.get("extracted_quote")
        if not quote_data:
            state.fail(PipelineStep.RISK, "No extracted quote in state")
            return False

        try:
            quote = ExtractedQuote(**quote_data)
            report = self.openai.assess_risk(quote)
        except Exception as e:
            # Default to MEDIUM on failure — safer than auto-approving
            logger.warning("[%s] Risk assessment failed, defaulting to MEDIUM: %s",
                           state.contract_id, e)
            from ..models.contract import RiskReport, Recommendation
            report = RiskReport(
                risk_flag=RiskFlag.MEDIUM,
                recommendation=Recommendation.REVIEW,
                tax_valid=False,
                summary=f"Risk assessment failed ({e}). Defaulting to MEDIUM for manual review.",
            )

        state.set("risk_report", report.model_dump())
        state.advance(PipelineStep.RISK,
                      f"Risk: {report.risk_flag} — {report.recommendation}")
        logger.info("[%s] Risk: %s (%s) — %s",
                    state.contract_id, report.risk_flag, report.recommendation, report.summary)
        return True

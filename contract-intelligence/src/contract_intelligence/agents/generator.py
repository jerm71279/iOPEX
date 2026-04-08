import logging
from pathlib import Path
from jinja2 import Environment, FileSystemLoader
from ..clients.pdfshift_client import PDFShiftClient
from ..models.contract import ExtractedQuote
from ..models.state import PipelineState, PipelineStep

logger = logging.getLogger(__name__)


class GeneratorAgent:
    def __init__(self, pdfshift: PDFShiftClient, template_dir: Path, output_dir: Path):
        self.pdfshift = pdfshift
        self.template_dir = template_dir
        self.output_dir = output_dir
        self.jinja = Environment(loader=FileSystemLoader(str(template_dir)))

    def run(self, state: PipelineState) -> bool:
        logger.info("[%s] Generator: building contract PDF...", state.contract_id)
        quote_data = state.get("extracted_quote")
        risk_data = state.get("risk_report")
        if not quote_data:
            state.fail(PipelineStep.GENERATE, "No extracted quote for PDF generation")
            return False

        quote = ExtractedQuote(**quote_data)
        try:
            template = self.jinja.get_template("contract.html")
            from ..config import settings as _settings
            html = template.render(
                contract_id=state.contract_id,
                client_name=quote.client_name or "—",
                client_email=quote.client_email or "—",
                client_tax_id=quote.client_tax_id or "—",
                total_amount=f"{quote.total_amount:,.2f}" if quote.total_amount else "—",
                currency=quote.currency,
                service_description=quote.service_description or "—",
                quote_date=quote.quote_date or "—",
                payment_terms=quote.payment_terms or "—",
                risk_flag=risk_data.get("risk_flag", "LOW") if risk_data else "LOW",
                risk_summary=risk_data.get("summary", "") if risk_data else "",
                review_notes=state.get("review_notes") or "",
                provider_name=_settings.provider_name,
                provider_email=_settings.provider_email or _settings.revops_email,
                provider_signatory=_settings.provider_signatory,
            )
        except Exception as e:
            state.fail(PipelineStep.GENERATE, f"Template render failed: {e}")
            return False

        try:
            pdf_bytes = self.pdfshift.html_to_pdf(html)
        except Exception as e:
            state.fail(PipelineStep.GENERATE, f"PDFShift failed: {e}")
            return False

        self.output_dir.mkdir(parents=True, exist_ok=True)
        contract_path = self.output_dir / f"{state.contract_id}_contract.pdf"
        contract_path.write_bytes(pdf_bytes)

        state.set("contract_pdf_path", str(contract_path))
        state.advance(PipelineStep.GENERATE, f"Contract PDF: {contract_path.name}")
        logger.info("[%s] Generator: PDF saved to %s", state.contract_id, contract_path)
        return True

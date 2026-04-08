import base64
import json
import logging
from pathlib import Path

import anthropic

from ..models.contract import ExtractedQuote, RiskReport, RiskFlag, Recommendation, ObligationExtract

logger = logging.getLogger(__name__)


class AnthropicClient:
    def __init__(self, api_key: str, model: str = "claude-sonnet-4-6"):
        self.client = anthropic.Anthropic(api_key=api_key)
        self.model = model

    def extract_quote(self, pdf_path: Path) -> ExtractedQuote:
        """Claude vision: extract structured data from a PDF quote using tool use."""
        pdf_b64 = base64.standard_b64encode(pdf_path.read_bytes()).decode()

        tools = [{
            "name": "extract_quote_data",
            "description": "Extract structured contract quote data from the document",
            "input_schema": {
                "type": "object",
                "properties": {
                    "client_name":        {"type": "string", "description": "Full legal name of the client"},
                    "client_email":       {"type": "string", "description": "Client contact email address"},
                    "client_tax_id":      {"type": "string", "description": "Tax ID, VAT number, or EIN"},
                    "total_amount":       {"type": "number", "description": "Total contract value as a number"},
                    "currency":           {"type": "string", "description": "3-letter ISO currency code (USD, EUR, INR...)"},
                    "service_description":{"type": "string", "description": "Description of services being provided"},
                    "quote_date":         {"type": "string", "description": "Quote date in YYYY-MM-DD format"},
                    "payment_terms":      {"type": "string", "description": "Payment terms (e.g. Net 30)"},
                },
                "required": ["client_name", "total_amount", "currency"],
            },
        }]

        response = self.client.messages.create(
            model=self.model,
            max_tokens=1024,
            tools=tools,
            tool_choice={"type": "tool", "name": "extract_quote_data"},
            messages=[{
                "role": "user",
                "content": [
                    {
                        "type": "document",
                        "source": {
                            "type": "base64",
                            "media_type": "application/pdf",
                            "data": pdf_b64,
                        },
                    },
                    {
                        "type": "text",
                        "text": "Extract all contract quote fields from this document.",
                    },
                ],
            }],
        )

        tool_block = next(b for b in response.content if b.type == "tool_use")
        data = tool_block.input
        return ExtractedQuote(**{k: v for k, v in data.items() if v is not None})

    def assess_risk(self, quote: ExtractedQuote) -> RiskReport:
        """Claude: risk assessment on extracted quote data using tool use."""
        tools = [{
            "name": "report_risk",
            "description": "Report the risk assessment result for a contract quote",
            "input_schema": {
                "type": "object",
                "properties": {
                    "risk_flag":     {"type": "string", "enum": ["LOW", "MEDIUM", "HIGH"]},
                    "recommendation":{"type": "string", "enum": ["APPROVE", "REVIEW", "REJECT"]},
                    "tax_valid":     {"type": "boolean"},
                    "summary":       {"type": "string", "description": "1-2 sentence risk explanation"},
                    "redline_notes": {"type": "string", "description": "Specific clause concerns, or null"},
                },
                "required": ["risk_flag", "recommendation", "tax_valid", "summary"],
            },
        }]

        response = self.client.messages.create(
            model=self.model,
            max_tokens=512,
            tools=tools,
            tool_choice={"type": "tool", "name": "report_risk"},
            system=(
                "You are a contract risk analyst. "
                "HIGH risk: missing critical fields, amount >$500K without detail, invalid tax ID, net 120+ days. "
                "MEDIUM risk: minor concerns, ambiguous description, unverified tax ID, net 90 days. "
                "LOW risk: all fields present, amount reasonable, valid tax ID, net 30-60. "
                "Default to MEDIUM if uncertain — never auto-approve ambiguous contracts."
            ),
            messages=[{
                "role": "user",
                "content": f"Assess this contract quote:\n{quote.model_dump_json(indent=2)}",
            }],
        )

        tool_block = next(b for b in response.content if b.type == "tool_use")
        data = tool_block.input
        return RiskReport(
            risk_flag=RiskFlag(data["risk_flag"]),
            recommendation=Recommendation(data["recommendation"]),
            tax_valid=bool(data.get("tax_valid", True)),
            summary=data.get("summary", ""),
            redline_notes=data.get("redline_notes"),
        )

    def extract_obligations(self, contract_text: str) -> ObligationExtract:
        """Claude: extract obligation metadata from executed contract text."""
        tools = [{
            "name": "report_obligations",
            "description": "Report extracted obligation metadata from an executed contract",
            "input_schema": {
                "type": "object",
                "properties": {
                    "renewal_date":            {"type": "string", "description": "Renewal date YYYY-MM-DD or null"},
                    "termination_notice_days": {"type": "integer", "description": "Notice period in days"},
                    "sla_clauses":             {"type": "array", "items": {"type": "string"}},
                    "payment_terms":           {"type": "string"},
                    "raw_obligations":         {"type": "string", "description": "Brief obligations summary"},
                },
                "required": [],
            },
        }]

        response = self.client.messages.create(
            model=self.model,
            max_tokens=512,
            tools=tools,
            tool_choice={"type": "tool", "name": "report_obligations"},
            messages=[{
                "role": "user",
                "content": f"Extract obligation metadata from this contract:\n{contract_text[:8000]}",
            }],
        )

        tool_block = next(b for b in response.content if b.type == "tool_use")
        data = tool_block.input
        return ObligationExtract(**{k: v for k, v in data.items() if v is not None})

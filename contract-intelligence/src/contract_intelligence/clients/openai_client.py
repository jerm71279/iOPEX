import base64
import json
import logging
from pathlib import Path
from openai import OpenAI
from ..models.contract import ExtractedQuote, RiskReport, RiskFlag, Recommendation, ObligationExtract

logger = logging.getLogger(__name__)


class OpenAIClient:
    def __init__(self, api_key: str, model: str = "gpt-4o"):
        self.client = OpenAI(api_key=api_key)
        self.model = model

    def extract_quote(self, pdf_path: Path) -> ExtractedQuote:
        """GPT-4o vision: extract structured data from a PDF quote."""
        pdf_b64 = base64.standard_b64encode(pdf_path.read_bytes()).decode()

        response = self.client.chat.completions.create(
            model=self.model,
            response_format={"type": "json_object"},
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are a contract data extraction specialist. "
                        "Extract structured data from the provided PDF quote. "
                        "Return a JSON object with these fields: "
                        "client_name, client_email, client_tax_id, total_amount (number), "
                        "currency (3-letter ISO), service_description, quote_date (YYYY-MM-DD), "
                        "payment_terms. Use null for missing fields."
                    ),
                },
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:application/pdf;base64,{pdf_b64}",
                                "detail": "high",
                            },
                        },
                        {"type": "text", "text": "Extract all contract fields from this quote PDF."},
                    ],
                },
            ],
        )
        raw = response.choices[0].message.content
        data = json.loads(raw)
        return ExtractedQuote(**data)

    def assess_risk(self, quote: ExtractedQuote) -> RiskReport:
        """GPT-4o: risk assessment on extracted quote data."""
        response = self.client.chat.completions.create(
            model=self.model,
            response_format={"type": "json_object"},
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are a contract risk analyst. Assess the provided quote data. "
                        "Return JSON with: risk_flag (LOW|MEDIUM|HIGH), "
                        "recommendation (APPROVE|REVIEW|REJECT), tax_valid (boolean), "
                        "summary (1–2 sentence explanation), "
                        "redline_notes (specific clause concerns or null). "
                        "HIGH risk = missing critical data, suspicious amounts, or invalid tax ID. "
                        "MEDIUM risk = minor concerns requiring human review. "
                        "LOW risk = all fields present, amounts reasonable, tax valid."
                    ),
                },
                {
                    "role": "user",
                    "content": f"Assess this contract quote:\n{quote.model_dump_json(indent=2)}",
                },
            ],
        )
        raw = response.choices[0].message.content
        data = json.loads(raw)
        return RiskReport(
            risk_flag=RiskFlag(data["risk_flag"]),
            recommendation=Recommendation(data["recommendation"]),
            tax_valid=bool(data.get("tax_valid", True)),
            summary=data.get("summary", ""),
            redline_notes=data.get("redline_notes"),
        )

    def extract_obligations(self, contract_text: str) -> ObligationExtract:
        """GPT-4o: extract obligation metadata from executed contract text."""
        response = self.client.chat.completions.create(
            model=self.model,
            response_format={"type": "json_object"},
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are a contract obligation specialist. "
                        "Extract key obligation metadata from the executed contract. "
                        "Return JSON with: renewal_date (YYYY-MM-DD or null), "
                        "termination_notice_days (integer or null), "
                        "sla_clauses (array of strings), payment_terms (string or null), "
                        "raw_obligations (brief summary)."
                    ),
                },
                {
                    "role": "user",
                    "content": f"Extract obligations from:\n{contract_text[:8000]}",
                },
            ],
        )
        raw = response.choices[0].message.content
        data = json.loads(raw)
        return ObligationExtract(**data)

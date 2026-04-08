from pydantic import BaseModel, Field
from typing import Optional
from enum import Enum


class RiskFlag(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


class Recommendation(str, Enum):
    APPROVE = "APPROVE"
    REVIEW = "REVIEW"
    REJECT = "REJECT"


class ReviewDecision(str, Enum):
    ACCEPT = "ACCEPT"
    MODIFY = "MODIFY"
    DECLINE = "DECLINE"


class ExtractedQuote(BaseModel):
    client_name: Optional[str] = None
    client_email: Optional[str] = None
    client_tax_id: Optional[str] = None
    total_amount: Optional[float] = None
    currency: str = "USD"
    service_description: Optional[str] = None
    quote_date: Optional[str] = None
    payment_terms: Optional[str] = None
    raw_text: Optional[str] = None


class RiskReport(BaseModel):
    risk_flag: RiskFlag
    recommendation: Recommendation
    tax_valid: bool
    summary: str
    redline_notes: Optional[str] = None


class ObligationExtract(BaseModel):
    renewal_date: Optional[str] = None
    termination_notice_days: Optional[int] = None
    sla_clauses: list[str] = Field(default_factory=list)
    payment_terms: Optional[str] = None
    raw_obligations: Optional[str] = None


class ContractRecord(BaseModel):
    contract_id: str
    source_email: Optional[str] = None
    pdf_path: Optional[str] = None
    extracted: Optional[ExtractedQuote] = None
    risk: Optional[RiskReport] = None
    review_decision: Optional[ReviewDecision] = None
    review_notes: Optional[str] = None
    contract_pdf_path: Optional[str] = None
    docuseal_submission_id: Optional[str] = None
    docuseal_counter_submission_id: Optional[str] = None
    signed_pdf_path: Optional[str] = None
    executed_pdf_path: Optional[str] = None
    obligations: Optional[ObligationExtract] = None

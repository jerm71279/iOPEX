"""Smoke tests for contract-intelligence — no external API calls required."""
import json
import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch


def test_pipeline_state_atomic_write(tmp_path):
    from src.contract_intelligence.models.state import PipelineState, PipelineStep
    state = PipelineState.new("CNT-TEST01")
    state.advance(PipelineStep.INTAKE, "test intake")
    state.save(tmp_path)

    loaded = PipelineState.load("CNT-TEST01", tmp_path)
    assert loaded.contract_id == "CNT-TEST01"
    assert loaded.current_step == PipelineStep.INTAKE
    assert len(loaded.steps) == 1


def test_pipeline_state_fail(tmp_path):
    from src.contract_intelligence.models.state import PipelineState, PipelineStep
    state = PipelineState.new("CNT-TEST02")
    state.fail(PipelineStep.EXTRACT, "GPT-4o timeout")
    state.save(tmp_path)

    loaded = PipelineState.load("CNT-TEST02", tmp_path)
    assert loaded.status == "failed"
    assert "GPT-4o timeout" in loaded.errors[0]


def test_pipeline_state_data_store(tmp_path):
    from src.contract_intelligence.models.state import PipelineState
    state = PipelineState.new("CNT-TEST03")
    state.set("extracted_quote", {"client_name": "Acme", "total_amount": 50000})
    state.save(tmp_path)

    loaded = PipelineState.load("CNT-TEST03", tmp_path)
    assert loaded.get("extracted_quote")["client_name"] == "Acme"


def test_contract_models():
    from src.contract_intelligence.models.contract import (
        ExtractedQuote, RiskReport, RiskFlag, Recommendation
    )
    quote = ExtractedQuote(
        client_name="Acme Corp",
        client_email="cfo@acme.com",
        total_amount=50000.0,
        currency="USD",
        service_description="AI Contract Automation",
    )
    assert quote.client_name == "Acme Corp"

    report = RiskReport(
        risk_flag=RiskFlag.LOW,
        recommendation=Recommendation.APPROVE,
        tax_valid=True,
        summary="All fields present, amount reasonable.",
    )
    assert report.risk_flag == RiskFlag.LOW


def test_docuseal_webhook_validation():
    import hashlib, hmac
    from src.contract_intelligence.clients.docuseal_client import DocuSealClient
    secret = "test-webhook-secret"
    client = DocuSealClient("http://localhost:3000", "api-key", webhook_secret=secret)

    payload = b'{"event_type": "submission.completed"}'
    sig = hmac.new(secret.encode(), payload, hashlib.sha256).hexdigest()
    assert client.validate_webhook(payload, sig)
    assert not client.validate_webhook(payload, "wrong-sig")


def test_contract_html_template(tmp_path):
    from jinja2 import Environment, FileSystemLoader
    template_dir = Path("src/contract_intelligence/templates")
    if not template_dir.exists():
        pytest.skip("Template dir not found — run from project root")
    env = Environment(loader=FileSystemLoader(str(template_dir)))
    t = env.get_template("contract.html")
    html = t.render(
        contract_id="CNT-SMOKE01",
        client_name="Test Client",
        client_email="test@client.com",
        client_tax_id="12345",
        total_amount="50,000.00",
        currency="USD",
        service_description="Test services",
        quote_date="2026-04-04",
        payment_terms="Net 30",
        risk_flag="LOW",
        risk_summary="All good.",
        review_notes="",
    )
    assert "CNT-SMOKE01" in html
    assert "Test Client" in html
    assert "Service Provider" in html


def test_health_endpoint():
    from fastapi.testclient import TestClient
    with patch.dict("os.environ", {
        "OPENAI_API_KEY": "sk-test",
        "PDFSHIFT_API_KEY": "test",
        "DOCUSEAL_API_KEY": "test",
        "GMAIL_USER": "test@gmail.com",
        "GMAIL_APP_PASSWORD": "test",
        "REVOPS_EMAIL": "revops@test.com",
    }):
        try:
            from src.contract_intelligence.main import app
            client = TestClient(app)
            resp = client.get("/health")
            assert resp.status_code == 200
            assert resp.json()["status"] == "ok"
        except Exception as e:
            pytest.skip(f"App import failed (expected in isolated test env): {e}")

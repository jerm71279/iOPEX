import asyncio
import logging
from pathlib import Path

from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import JSONResponse, FileResponse, HTMLResponse

from .config import settings
from .orchestrator import Orchestrator
from .human_review.review_router import router as review_router

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s — %(message)s",
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="contract-intelligence",
    description="Autonomous contract lifecycle automation",
    version="0.1.0",
)
app.include_router(review_router)


@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request):
    """Serve the human-friendly Mission Control dashboard."""
    path = Path(__file__).parent / "templates" / "dashboard.html"
    return HTMLResponse(content=path.read_text())


@app.get("/status/list")
async def list_pipelines(request: Request):
    """List all active pipelines for the dashboard."""
    orchestrator: Orchestrator = request.app.state.orchestrator
    state_dir = settings.state_dir
    results = []
    for f in state_dir.glob("*.json"):
        if f.name.endswith(".bak") or f.name.endswith(".tmp"):
            continue
        try:
            from .models.state import PipelineState
            state = PipelineState.load(f.stem, state_dir)
            risk_data = state.get("risk_report") or {}
            results.append({
                "contract_id": state.contract_id,
                "status": state.status,
                "current_step": state.current_step,
                "risk_flag": risk_data.get("risk_flag"),
                "updated_at": state.updated_at,
            })
        except Exception:
            continue
    # Sort by newest first
    results.sort(key=lambda x: x["updated_at"], reverse=True)
    return results[:20]


@app.on_event("startup")
async def startup():
    settings.ensure_dirs()
    app.state.orchestrator = Orchestrator(settings)
    logger.info("contract-intelligence started — DocuSeal: %s", settings.docuseal_base_url)


# ---------------------------------------------------------------------------
# Webhook — DocuSeal fires this when a submission is completed
# ---------------------------------------------------------------------------

@app.post("/webhooks/docuseal")
async def docuseal_webhook(request: Request):
    body = await request.body()
    sig = request.headers.get("x-docuseal-signature", "")

    orchestrator: Orchestrator = request.app.state.orchestrator
    if not orchestrator.docuseal.validate_webhook(body, sig):
        raise HTTPException(status_code=401, detail="Invalid webhook signature")

    data = await request.json()
    event_type = data.get("event_type", "")
    submission = data.get("data", {})
    submission_id = submission.get("id")
    # Map submission_id back to contract_id via state scan
    contract_id = _find_contract_by_submission(orchestrator, submission_id)

    if event_type == "submission.completed" and contract_id:
        orchestrator.notify_docuseal_complete(contract_id, submission_id)
        return {"ok": True, "contract_id": contract_id}

    return {"ok": True, "ignored": True, "event": event_type}


def _find_contract_by_submission(orchestrator: Orchestrator, submission_id: int) -> str | None:
    """Scan state files to find contract_id matching a submission_id."""
    state_dir = settings.state_dir
    for f in state_dir.glob("*.json"):
        if f.name.endswith(".bak") or f.name.endswith(".tmp"):
            continue
        try:
            from .models.state import PipelineState
            state = PipelineState.load(f.stem, state_dir)
            if state.get("docuseal_submission_id") == submission_id or \
               state.get("docuseal_counter_submission_id") == submission_id:
                return state.contract_id
        except Exception:
            continue
    return None


# ---------------------------------------------------------------------------
# Trigger — manually inject a PDF to start a pipeline run
# ---------------------------------------------------------------------------

@app.post("/trigger")
async def trigger(
    pdf: UploadFile = File(...),
    sender: str = Form("manual@trigger"),
):
    """Start a contract pipeline by uploading a quote PDF directly."""
    orchestrator: Orchestrator = request.app.state.orchestrator if False else None

    # Need request context — use dependency instead
    raise HTTPException(status_code=500, detail="Use /trigger via the request context endpoint below")


@app.post("/trigger/upload")
async def trigger_upload(request: Request, pdf: UploadFile = File(...),
                         sender: str = Form("manual@trigger")):
    """Upload a quote PDF to start a new contract pipeline run."""
    orchestrator: Orchestrator = request.app.state.orchestrator
    contract_id = orchestrator.new_contract_id()

    tmp_path = settings.output_dir / "state" / "raw" / f"{contract_id}_upload.pdf"
    tmp_path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path.write_bytes(await pdf.read())

    asyncio.create_task(orchestrator.run(
        contract_id=contract_id,
        pdf_path=tmp_path,
        sender=sender,
    ))
    return {"contract_id": contract_id, "status_url": f"/status/{contract_id}"}


# ---------------------------------------------------------------------------
# Status + Audit
# ---------------------------------------------------------------------------

@app.get("/status/{contract_id}")
async def status(contract_id: str, request: Request):
    orchestrator: Orchestrator = request.app.state.orchestrator
    try:
        state = orchestrator.load_state(contract_id)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"Contract {contract_id} not found")
    return {
        "contract_id": contract_id,
        "status": state.status,
        "current_step": state.current_step,
        "steps": [s.model_dump() for s in state.steps[-10:]],
        "errors": state.errors[-5:],
        "risk_flag": (state.get("risk_report") or {}).get("risk_flag"),
        "executed_pdf": state.get("executed_pdf_path"),
    }


@app.get("/audit/{contract_id}")
async def audit(contract_id: str, request: Request):
    orchestrator: Orchestrator = request.app.state.orchestrator
    try:
        state = orchestrator.load_state(contract_id)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"Contract {contract_id} not found")
    return {
        "contract_id": contract_id,
        "created_at": state.created_at,
        "updated_at": state.updated_at,
        "source_email": state.source_email,
        "steps": [s.model_dump() for s in state.steps],
        "risk_report": state.get("risk_report"),
        "review_decision": state.get("review_decision"),
        "obligations": state.get("obligations"),
        "final_status": state.status,
    }


@app.get("/download/{contract_id}")
async def download_executed(contract_id: str, request: Request):
    orchestrator: Orchestrator = request.app.state.orchestrator
    try:
        state = orchestrator.load_state(contract_id)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"Contract {contract_id} not found")
    # Try executed first, then signed, then generated contract
    for key, label in [("executed_pdf_path", "executed"), ("signed_pdf_path", "signed"),
                        ("contract_pdf_path", "contract")]:
        path = state.get(key)
        if path and Path(path).exists():
            return FileResponse(path, media_type="application/pdf",
                                filename=f"{label}_{contract_id}.pdf")
    raise HTTPException(status_code=404, detail="No PDF available yet")


@app.get("/health")
async def health():
    return {"status": "ok", "service": "contract-intelligence"}


# ---------------------------------------------------------------------------
# Demo Signing Page — used when DocuSeal template is not configured
# ---------------------------------------------------------------------------

@app.get("/sign/{contract_id}", response_class=HTMLResponse)
async def demo_sign_page(contract_id: str, request: Request):
    orchestrator: Orchestrator = request.app.state.orchestrator
    try:
        state = orchestrator.load_state(contract_id)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"Contract {contract_id} not found")

    pdf_path = state.get("contract_pdf_path") or ""
    quote_data = state.get("extracted_quote") or {}
    client_name = quote_data.get("client_name", "Client")
    risk_data = state.get("risk_report") or {}
    risk_flag = risk_data.get("risk_flag", "")

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Sign Contract — {contract_id}</title>
  <style>
    * {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
            background: #f0f4f8; min-height: 100vh; }}
    .header {{ background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
               color: #fff; padding: 20px 32px; display: flex;
               align-items: center; justify-content: space-between; }}
    .header h1 {{ font-size: 20px; font-weight: 600; }}
    .badge {{ background: rgba(255,255,255,0.15); border-radius: 20px;
              padding: 4px 12px; font-size: 12px; }}
    .container {{ max-width: 960px; margin: 32px auto; padding: 0 24px; }}
    .card {{ background: #fff; border-radius: 12px; padding: 28px;
             box-shadow: 0 2px 12px rgba(0,0,0,0.08); margin-bottom: 20px; }}
    .card h2 {{ font-size: 16px; font-weight: 600; color: #1a1a2e; margin-bottom: 16px;
                border-bottom: 2px solid #e8ecf0; padding-bottom: 12px; }}
    .meta {{ display: grid; grid-template-columns: repeat(3, 1fr); gap: 16px; margin-bottom: 20px; }}
    .meta-item label {{ font-size: 11px; text-transform: uppercase; letter-spacing: 0.5px;
                        color: #64748b; }}
    .meta-item p {{ font-size: 15px; font-weight: 600; color: #1e293b; margin-top: 2px; }}
    .pdf-frame {{ width: 100%; height: 600px; border: 1px solid #e2e8f0;
                  border-radius: 8px; }}
    .sign-section {{ text-align: center; padding: 32px; }}
    .sign-section p {{ color: #64748b; margin-bottom: 24px; font-size: 14px; }}
    .sign-btn {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                 color: white; border: none; padding: 16px 48px; font-size: 16px;
                 font-weight: 600; border-radius: 8px; cursor: pointer;
                 letter-spacing: 0.5px; transition: opacity 0.2s; }}
    .sign-btn:hover {{ opacity: 0.9; }}
    .sign-btn:disabled {{ opacity: 0.5; cursor: not-allowed; }}
    .success {{ background: #f0fdf4; border: 1px solid #86efac; border-radius: 8px;
                padding: 20px; text-align: center; display: none; }}
    .success h3 {{ color: #16a34a; font-size: 18px; }}
    .success p {{ color: #15803d; margin-top: 8px; }}
    .risk-badge {{ display: inline-block; padding: 3px 10px; border-radius: 12px;
                   font-size: 12px; font-weight: 600; margin-left: 8px; }}
    .risk-LOW {{ background: #dcfce7; color: #16a34a; }}
    .risk-MEDIUM {{ background: #fef9c3; color: #ca8a04; }}
    .risk-HIGH {{ background: #fee2e2; color: #dc2626; }}
  </style>
</head>
<body>
  <div class="header">
    <div>
      <h1>Electronic Signature Request</h1>
      <div style="font-size:13px;color:rgba(255,255,255,0.6);margin-top:4px;">
        Contract Intelligence Platform — Autonomous Contract Lifecycle
      </div>
    </div>
    <span class="badge">{contract_id}</span>
  </div>
  <div class="container">
    <div class="card">
      <h2>Contract Details
        <span class="risk-badge risk-{risk_flag}">{risk_flag} RISK</span>
      </h2>
      <div class="meta">
        <div class="meta-item">
          <label>Client</label>
          <p>{client_name}</p>
        </div>
        <div class="meta-item">
          <label>Contract ID</label>
          <p>{contract_id}</p>
        </div>
        <div class="meta-item">
          <label>Status</label>
          <p>Pending Signature</p>
        </div>
      </div>
      <p style="font-size:13px;color:#64748b;">
        Review the contract document below before signing. By clicking "Sign Contract" you
        agree to be legally bound by the terms contained herein.
      </p>
    </div>

    <div class="card">
      <h2>Contract Document</h2>
      <iframe class="pdf-frame" src="/download/{contract_id}"
              title="Contract Document"></iframe>
    </div>

    <div class="card">
      <div class="sign-section">
        <p>I have read and agree to the terms of this Service Agreement.</p>
        <button class="sign-btn" id="signBtn" onclick="signContract()">
          ✍ Sign Contract
        </button>
        <div class="success" id="successMsg">
          <h3>✓ Signature Captured</h3>
          <p>Your signature has been recorded. The contract is now being processed.
             You will receive a copy via email once fully executed.</p>
        </div>
      </div>
    </div>
  </div>
  <script>
    async function signContract() {{
      const btn = document.getElementById('signBtn');
      btn.disabled = true;
      btn.textContent = 'Processing...';
      try {{
        const res = await fetch('/sign/{contract_id}', {{method: 'POST'}});
        const data = await res.json();
        if (data.ok) {{
          btn.style.display = 'none';
          document.getElementById('successMsg').style.display = 'block';
        }} else {{
          btn.disabled = false;
          btn.textContent = '✍ Sign Contract';
          alert('Error: ' + (data.detail || 'Unknown error'));
        }}
      }} catch(e) {{
        btn.disabled = false;
        btn.textContent = '✍ Sign Contract';
        alert('Network error — please try again.');
      }}
    }}
  </script>
</body>
</html>"""
    return HTMLResponse(content=html)


@app.post("/sign/{contract_id}")
async def demo_sign_submit(contract_id: str, request: Request):
    """Demo signing endpoint — triggers the pipeline to continue after 'signature'."""
    orchestrator: Orchestrator = request.app.state.orchestrator
    try:
        state = orchestrator.load_state(contract_id)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"Contract {contract_id} not found")

    submission_id = state.get("docuseal_submission_id")
    if not submission_id:
        raise HTTPException(status_code=400, detail="No active signing submission")

    # Fire the same event as a real DocuSeal webhook would
    orchestrator.notify_docuseal_complete(contract_id, submission_id)
    return {"ok": True, "contract_id": contract_id, "message": "Signature recorded"}

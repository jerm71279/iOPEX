from fastapi import APIRouter, HTTPException, Form, Request
from fastapi.responses import HTMLResponse
from typing import Optional

router = APIRouter()


def get_review_html(contract_id: str, state_data: dict) -> str:
    extracted = state_data.get("contract_data", {}).get("extracted_quote") or {}
    risk = state_data.get("contract_data", {}).get("risk_report") or {}
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>Contract Review — {contract_id}</title>
<style>
  body {{ font-family: Inter, sans-serif; max-width: 800px; margin: 40px auto; padding: 0 20px; background: #f8faff; color: #1a1a2e; }}
  h1 {{ font-size: 28px; font-weight: 800; color: #0a1628; }}
  .badge {{ display: inline-block; padding: 4px 12px; border-radius: 12px; font-weight: 700; font-size: 13px; }}
  .LOW {{ background: #d1fae5; color: #065f46; }}
  .MEDIUM {{ background: #fef3c7; color: #92400e; }}
  .HIGH {{ background: #fee2e2; color: #991b1b; }}
  table {{ width: 100%; border-collapse: collapse; background: white; border-radius: 12px; overflow: hidden; box-shadow: 0 1px 3px rgba(0,0,0,0.1); margin: 20px 0; }}
  th, td {{ padding: 12px 16px; text-align: left; border-bottom: 1px solid #e5e7eb; }}
  th {{ background: #f3f4f6; font-weight: 600; font-size: 13px; color: #6b7280; }}
  .risk-box {{ background: white; border-radius: 12px; padding: 20px; margin: 20px 0; border-left: 4px solid #f0a500; }}
  .redlines {{ background: #fefce8; border: 1px solid #fde68a; border-radius: 8px; padding: 16px; margin: 12px 0; font-size: 14px; }}
  .actions {{ background: white; border-radius: 12px; padding: 24px; margin: 20px 0; box-shadow: 0 1px 3px rgba(0,0,0,0.1); }}
  select, textarea {{ width: 100%; padding: 10px; border: 1px solid #d1d5db; border-radius: 8px; font-size: 14px; margin-top: 8px; }}
  button {{ padding: 12px 32px; border-radius: 8px; border: none; font-weight: 700; font-size: 14px; cursor: pointer; margin-right: 8px; }}
  .btn-approve {{ background: #10b981; color: white; }}
  .btn-decline {{ background: #ef4444; color: white; }}
</style>
</head>
<body>
<h1>Contract Review</h1>
<p><strong>Contract ID:</strong> {contract_id} &nbsp;
   <span class="badge {risk.get('risk_flag', 'MEDIUM')}">{risk.get('risk_flag', 'MEDIUM')} RISK</span></p>

<h2>Extracted Data</h2>
<table>
  <tr><th>Field</th><th>Value</th></tr>
  <tr><td>Client Name</td><td>{extracted.get('client_name') or '—'}</td></tr>
  <tr><td>Client Email</td><td>{extracted.get('client_email') or '—'}</td></tr>
  <tr><td>Tax ID</td><td>{extracted.get('client_tax_id') or '—'}</td></tr>
  <tr><td>Amount</td><td>{extracted.get('currency', 'USD')} {extracted.get('total_amount') or '—'}</td></tr>
  <tr><td>Service</td><td>{extracted.get('service_description') or '—'}</td></tr>
  <tr><td>Quote Date</td><td>{extracted.get('quote_date') or '—'}</td></tr>
  <tr><td>Payment Terms</td><td>{extracted.get('payment_terms') or '—'}</td></tr>
</table>

<div class="risk-box">
  <strong>AI Risk Assessment:</strong> {risk.get('summary') or '—'}
  {f'<div class="redlines"><strong>Redline Notes:</strong><br>{risk.get("redline_notes")}</div>' if risk.get('redline_notes') else ''}
</div>

<div class="actions">
  <h2>Your Decision</h2>
  <form method="POST">
    <label><strong>Decision</strong></label>
    <select name="decision">
      <option value="ACCEPT">ACCEPT — Approve as-is</option>
      <option value="MODIFY">MODIFY — Approve with notes</option>
      <option value="DECLINE">DECLINE — Reject contract</option>
    </select>
    <br><br>
    <label><strong>Notes (required for MODIFY or DECLINE)</strong></label>
    <textarea name="notes" rows="4" placeholder="Enter your review notes here..."></textarea>
    <br><br>
    <button type="submit" class="btn-approve">Submit Decision</button>
  </form>
</div>
</body>
</html>"""


@router.get("/review/{contract_id}", response_class=HTMLResponse)
async def get_review(contract_id: str, request: Request):
    orchestrator = request.app.state.orchestrator
    try:
        state = orchestrator.load_state(contract_id)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"Contract {contract_id} not found")
    return get_review_html(contract_id, state.model_dump())


@router.post("/review/{contract_id}", response_class=HTMLResponse)
async def post_review(
    contract_id: str,
    request: Request,
    decision: str = Form(...),
    notes: Optional[str] = Form(""),
):
    orchestrator = request.app.state.orchestrator
    try:
        orchestrator.submit_review(contract_id, decision, notes or "")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return f"""<!DOCTYPE html><html><body style="font-family:Inter,sans-serif;max-width:600px;margin:60px auto;text-align:center;">
<h1 style="color:#10b981;">Decision Submitted</h1>
<p>Contract <strong>{contract_id}</strong> — Decision: <strong>{decision}</strong></p>
<p>The pipeline has been notified. You can close this window.</p>
</body></html>"""

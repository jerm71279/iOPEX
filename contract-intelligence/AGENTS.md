# contract-intelligence — Agent Roster

## Overview

10-stage pipeline split across two logical bots. Bot A handles the intelligence and generation
phases. Bot B handles distribution and archiving after the client signs.

| # | Agent | Bot | Role | Approval Gate | Reversible |
|---|-------|-----|------|---------------|-----------|
| 1 | Intake | A | Gmail IMAP → PDF attachment download | No | Yes |
| 2 | Extractor | A | GPT-4o vision → structured JSON | No | Yes |
| 3 | Risk | A | GPT-4o risk scoring (LOW/MEDIUM/HIGH) | No | Yes |
| 4 | Generator | A | Jinja2 + PDFShift → contract PDF | No | Yes |
| 5 | Signer | A | DocuSeal submission → send to client | **Yes (MEDIUM risk)** | No |
| 6 | Monitor | B | DocuSeal webhook / poll → signature event | No | Yes |
| 7 | Distributor | B | Download signed PDF + RevOps counter-sign | No | No |
| 8 | Emailer | B | Gmail SMTP → executed PDF to all parties | No | No |
| 9 | Archiver | B | Write to output/archive/ + audit JSONL | No | Yes |
| 10 | Obligation | B | GPT-4o post-execution clause extraction | No | Yes |

---

## Agent Details

### Agent 1 — Intake
**File:** `agents/intake.py`
**Role:** Monitors Gmail inbox via IMAP. Detects emails with PDF attachments matching quote pattern. Downloads attachment and stores in `output/state/raw/{contract_id}/quote.pdf`.
**Failure Mode:** IMAP connection drops or no PDF found.
**Remediation:** Retry with exponential backoff (max 3 attempts). Fallback: `/trigger` endpoint accepts manual PDF upload.

### Agent 2 — Extractor
**File:** `agents/extractor.py`
**Role:** Sends PDF as base64 image to GPT-4o vision. Returns structured `ExtractedQuote` JSON: `total_amount`, `client_name`, `client_email`, `client_tax_id`, `service_description`, `currency`, `quote_date`.
**Failure Mode:** GPT-4o returns malformed JSON or misses required fields.
**Remediation:** Retry with stricter system prompt. Flag missing fields as null — pipeline continues but human review is forced.

### Agent 3 — Risk
**File:** `agents/risk.py`
**Role:** Sends `ExtractedQuote` to GPT-4o for risk assessment. Returns `RiskReport`: `risk_flag` (LOW/MEDIUM/HIGH), `recommendation` (APPROVE/REVIEW/REJECT), `tax_valid` (bool), `summary` (str).
**Failure Mode:** Ambiguous risk classification or GPT-4o timeout.
**Remediation:** Default to MEDIUM risk on failure (forces human review rather than auto-approving).

### Agent 4 — Generator
**File:** `agents/generator.py`
**Role:** Populates `templates/contract.html` with `ExtractedQuote` data via Jinja2. Sends HTML body to PDFShift API. Returns PDF bytes.
**Failure Mode:** PDFShift API error or template rendering fails.
**Remediation:** Retry once. If still failing, raise `GenerationError` — pipeline halts, state set to FAILED.

### Agent 5 — Signer
**File:** `agents/signer.py`
**Role:** Creates DocuSeal submission with contract PDF. Adds client as submitter. Returns `submission_id` and `signing_url`.
**Failure Mode:** DocuSeal API down or PDF upload fails.
**Remediation:** Retry with backoff. DocuSeal runs locally in Docker — check container health.
**Human gate:** On MEDIUM risk, human review happens BEFORE this agent runs.

### Agent 6 — Monitor
**File:** `agents/monitor.py`
**Role:** Waits for DocuSeal `submission.completed` webhook event. Validates HMAC-SHA256 signature. Extracts `submission_id`. Triggers Bot B.
**Failure Mode:** Webhook delivery fails (e.g., ngrok tunnel not configured).
**Remediation:** Fallback to polling mode (`DOCUSEAL_USE_POLLING=true`). `make tunnel` auto-configures ngrok URL.

### Agent 7 — Distributor
**File:** `agents/distributor.py`
**Role:** Downloads signed PDF from DocuSeal. Creates second DocuSeal submission for RevOps counter-signature. Waits for completion.
**Failure Mode:** RevOps doesn't sign within timeout.
**Remediation:** Send reminder email at 24h. Configurable timeout (default: 48h).

### Agent 8 — Emailer
**File:** `agents/archiver.py` (email step within archiver)
**Role:** Sends fully executed PDF (both signatures) to `CUSTOMER_EMAIL` and `REVOPS_EMAIL` via Gmail SMTP.
**Failure Mode:** SMTP auth failure.
**Remediation:** Retry once. Log failure but don't block archive step.

### Agent 9 — Archiver
**File:** `agents/archiver.py`
**Role:** Writes executed PDF to `output/archive/{contract_id}.pdf`. Appends audit record to `output/audit/audit.jsonl` (timestamp, all step outcomes, submitter IDs).
**Failure Mode:** Disk write error.
**Remediation:** Retry with fsync. If still failing, log error — pipeline marked ARCHIVE_FAILED but not FAILED.

### Agent 10 — Obligation
**File:** `agents/obligation.py`
**Role:** GPT-4o parses executed contract text. Extracts: `renewal_date`, `termination_notice_days`, `sla_clauses`, `payment_terms`. Appended to contract state record.
**Failure Mode:** GPT-4o extraction misses fields.
**Remediation:** Partial results are acceptable. Log what was found, skip what wasn't.

---

## Orchestration

Managed by `orchestrator.py`. Each step:
1. Updates `PipelineState.current_step`
2. Calls the agent
3. On success: advances state, logs to audit
4. On failure: sets `PipelineState.status = FAILED`, records error, stops pipeline

Human review suspends the pipeline at `GATEWAY` step. FastAPI `/review/{id}` endpoint
resumes it by calling `orchestrator.resume(contract_id, decision)`.

---

## Human Review Flow

```
Risk Agent → MEDIUM → orchestrator pauses → sends email to REVOPS_EMAIL
  → RevOps opens GET /review/{id} → sees extracted data + AI redline diff
  → submits POST /review/{id} with decision: ACCEPT | MODIFY | DECLINE
  → orchestrator.resume() → pipeline continues (or terminates on DECLINE)
```

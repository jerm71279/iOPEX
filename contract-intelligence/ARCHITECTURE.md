# contract-intelligence — Architecture

## System Overview

Python-native autonomous contract lifecycle pipeline. Replaces UiPath Maestro + DocuSign
with a FastAPI orchestrator + DocuSeal (self-hosted). No external account setup required
beyond OpenAI and PDFShift API keys.

```
┌─────────────────────────────────────────────────────────────────┐
│                        ORCHESTRATOR                              │
│              (async state machine — orchestrator.py)            │
└────────────────┬──────────────────────────────┬─────────────────┘
                 │                              │
    ┌────────────▼────────────┐    ┌────────────▼────────────┐
    │       BOT A             │    │       BOT B             │
    │   Intelligence Engine   │    │  Distribution Engine    │
    │  steps 1–4 + gateway    │    │      steps 5–10         │
    └────────────┬────────────┘    └────────────┬────────────┘
                 │                              │
    ┌────────────▼────────────────────────────────────────────┐
    │                    API CLIENTS                          │
    │  GmailClient │ OpenAIClient │ PDFShiftClient │ DocuSeal │
    └─────────────────────────────────────────────────────────┘
```

## Component Map

| Component | File | Responsibility |
|-----------|------|---------------|
| FastAPI app | `main.py` | HTTP routes, webhook receiver, review UI |
| Orchestrator | `orchestrator.py` | State machine, step sequencing, error handling |
| Bot A | `pipeline/bot_a.py` | Intake → Extract → Risk → Gateway → Generate → Sign |
| Bot B | `pipeline/bot_b.py` | Monitor → Download → Counter-sign → Email → Archive |
| Intake agent | `agents/intake.py` | Gmail IMAP poll, PDF attachment download |
| Extractor agent | `agents/extractor.py` | GPT-4o vision → structured JSON |
| Risk agent | `agents/risk.py` | GPT-4o risk scoring (LOW/MEDIUM/HIGH) |
| Generator agent | `agents/generator.py` | Jinja2 → HTML → PDFShift → PDF bytes |
| Signer agent | `agents/signer.py` | DocuSeal submission create + send to client |
| Monitor agent | `agents/monitor.py` | DocuSeal webhook handler or polling |
| Distributor agent | `agents/distributor.py` | Download signed PDF + RevOps counter-sign |
| Archiver agent | `agents/archiver.py` | Write to output/archive/ + append audit JSONL |
| Obligation agent | `agents/obligation.py` | GPT-4o post-execution clause extraction |
| Gmail client | `clients/gmail_client.py` | imaplib (receive) + smtplib (send) |
| OpenAI client | `clients/openai_client.py` | GPT-4o chat + vision, JSON mode |
| PDFShift client | `clients/pdfshift_client.py` | HTML → PDF via REST |
| DocuSeal client | `clients/docuseal_client.py` | Submissions API, HMAC webhook validation |
| State model | `models/state.py` | PipelineState, atomic JSON writes, .bak backup |
| Contract model | `models/contract.py` | ExtractedQuote, RiskReport, ContractRecord |
| Review router | `human_review/review_router.py` | FastAPI router for /review/{id} |
| Contract template | `templates/contract.html` | Jinja2 HTML → PDFShift |

## Data Flow

```
Gmail IMAP
    │  quote email + PDF attachment
    ▼
Extractor (GPT-4o vision)
    │  ExtractedQuote JSON
    ▼
Risk Agent (GPT-4o)
    │  RiskReport {flag, recommendation, tax_valid, summary}
    ▼
Gateway
    ├─ LOW  ──────────────────────────► Generator
    ├─ MEDIUM ──► Human Review UI ──► Generator (or Reject)
    └─ HIGH ────────────────────────► Rejection Email
                                          │
Generator (Jinja2 + PDFShift)            │
    │  contract.pdf bytes                 │
    ▼                                     │
DocuSeal Submission (client sign)        │
    │                                     │
    ▼  [webhook: completed]               │
Bot B activated                          │
    │                                     │
Download signed PDF                      │
    │                                     │
RevOps counter-sign submission           │
    │                                     │
Gmail SMTP → all parties                 │
    │                                     │
Archive (output/archive/ + audit JSONL)  │
    │                                     │
Obligation extract (GPT-4o) ◄────────────┘
    │
Renewal dates / SLAs extracted
```

## State Machine

States: `PENDING → INTAKE → EXTRACT → RISK → [HUMAN_REVIEW] → GENERATE → SIGN → MONITOR → DOWNLOAD → COUNTER_SIGN → EMAIL → ARCHIVE → [OBLIGATION] → COMPLETE`

Error states: `FAILED`, `REJECTED`

State stored in `output/state/{contract_id}.json` with atomic writes.

## Security

- All credentials in `.env` — never in code or logs
- DocuSeal webhook HMAC-SHA256 validation (rejects spoofed events)
- Secrets stripped from all log/error output
- DocuSeal runs in isolated Docker container (no external data egress)
- Output directory gitignored — no contract data ever committed

## Webhook Setup (ngrok)

DocuSeal webhooks require a public URL. With ngrok running:

```bash
make tunnel    # reads ngrok :4040 API, updates DocuSeal webhook URL automatically
```

Fallback: `DOCUSEAL_USE_POLLING=true` in .env → Bot B polls every 30s instead.

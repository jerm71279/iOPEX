# contract-intelligence

## Overview
End-to-end autonomous contract automation. A quote PDF arrives by email → GPT-4o extracts and risk-scores it → contract PDF is generated → client signs via DocuSeal → RevOps counter-signs → executed contract is archived. Python-native, no UiPath dependency.

**Customer:** Internal demo
**Deployment:** Docker (DocuSeal self-hosted + FastAPI app)
**Repo:** jerm71279/contract-intelligence (private)

## Stack
| Layer | Technology |
|-------|-----------|
| Language | Python 3.12 |
| Framework | FastAPI |
| Orchestration | Async state machine (orchestrator.py) |
| AI / LLM | OpenAI GPT-4o (vision + JSON mode) |
| PDF Generation | PDFShift API |
| eSignature | DocuSeal (self-hosted Docker) |
| Email | Gmail IMAP (trigger) + SMTP (delivery) |
| State | JSON-backed atomic writes (output/state/) |
| Audit | JSONL append-only trail (output/audit/) |

## Entry Points
- `make run` — start FastAPI on :8000
- `docker compose up` — start DocuSeal on :3000 + app
- `make tunnel` — configure ngrok webhook URL in DocuSeal
- `make test-trigger PDF=<path>` — inject a quote PDF to start a pipeline run
- `GET /status/{id}` — pipeline state
- `GET /audit/{id}` — full audit trail
- `POST /webhooks/docuseal` — DocuSeal event webhook (HMAC validated)
- `GET/POST /review/{id}` — human review task UI

## Pipeline Stages (10 steps)
```
Bot A: INTAKE → EXTRACT → RISK → GATEWAY → GENERATE → SIGN
Bot B: MONITOR → DOWNLOAD → COUNTER_SIGN → EMAIL → ARCHIVE
Optional: OBLIGATION_TRACK (Phase 3)
```

## Current Milestones
**Done:** Project scaffold, directory structure, all modules stubbed

**Next:**
1. POC happy path live (Gmail → GPT-4o → PDF → DocuSeal → archive)
2. Human review path (medium-risk → RevOps redline → resume)
3. DocuSeal webhooks with HMAC validation
4. Obligation tracking (GPT-4o post-execution parse)

## Key Files
| File | Purpose |
|------|---------|
| `src/contract_intelligence/main.py` | FastAPI app — all HTTP routes |
| `src/contract_intelligence/orchestrator.py` | State machine — drives pipeline |
| `src/contract_intelligence/pipeline/bot_a.py` | Intelligence pipeline (steps 1–4) |
| `src/contract_intelligence/pipeline/bot_b.py` | Distribution pipeline (steps 5–10) |
| `src/contract_intelligence/config.py` | Pydantic settings (reads .env) |
| `src/contract_intelligence/models/state.py` | PipelineState + atomic writes |
| `src/contract_intelligence/templates/contract.html` | Jinja2 contract template |

## Notes
- DocuSeal webhook requires public URL — use `make tunnel` to configure ngrok
- Set `DOCUSEAL_USE_POLLING=true` in .env for offline demo (no webhook needed)
- All secrets via .env — never hardcoded
- output/ directory is gitignored — all runtime state stays local

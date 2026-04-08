# contract-intelligence

AI-powered end-to-end contract automation — Gmail trigger to fully executed, archived contract using GPT-4o, DocuSeal, and PDFShift.

**Stack:** Python 3.12 · FastAPI · GPT-4o · DocuSeal · PDFShift · Gmail

---

## What It Does

Converts a raw quote email (PDF attachment) into a fully executed, archived contract — autonomously.

| Step | Who | What |
|------|-----|------|
| 1 | Bot A | Gmail IMAP detects quote email, downloads PDF |
| 2 | Bot A | GPT-4o extracts structured data (amount, client, terms) |
| 3 | Bot A | Risk assessment → LOW / MEDIUM / HIGH |
| 4 | Bot A | Gateway: approve / human review / reject |
| 5 | Bot A | PDFShift generates contract PDF from HTML template |
| 6 | Bot A | DocuSeal sends contract to client for signature |
| 7 | Bot B | Webhook fires on client signature |
| 8 | Bot B | Download signed PDF, route RevOps counter-sign |
| 9 | Bot B | Email executed contract to all parties |
| 10 | Bot B | Archive to storage + write audit trail |

---

## Quick Start

```bash
cp .env.example .env
# Fill in your API keys in .env

docker compose up -d          # Start DocuSeal on :3000
make run                      # Start app on :8000
make tunnel                   # Configure ngrok webhook URL in DocuSeal
```

Then trigger a test run:

```bash
make test-trigger PDF=sample/quote.pdf
```

Watch progress at `http://localhost:8000/status/{contract_id}`.

---

## Human Review Path

Medium-risk contracts pause the pipeline and POST a task to `REVOPS_EMAIL`.
RevOps opens `http://localhost:8000/review/{contract_id}`, reviews the AI redline diff,
and submits ACCEPT / MODIFY / DECLINE. The pipeline resumes automatically.

---

## Environment Variables

See `.env.example` for all required variables.

---

## Architecture

See [ARCHITECTURE.md](ARCHITECTURE.md) for system design and component map.

---

## Deployment

See [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md) for Docker and production setup.

---

*contract-intelligence — demo build*

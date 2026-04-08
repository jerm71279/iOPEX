# Changelog

## [0.1.0] — 2026-04-04
### Added
- Initial scaffold: project structure, all documentation files
- Full Python package: config, models, clients, agents, orchestrator, FastAPI app
- DocuSeal (self-hosted) integration replacing DocuSign
- GPT-4o vision extraction + risk assessment pipeline
- PDFShift HTML→PDF contract generation
- Gmail IMAP trigger + SMTP delivery
- Human review path for MEDIUM risk contracts
- HMAC-validated DocuSeal webhooks + polling fallback
- Obligation tracking agent (renewal dates, SLAs, termination terms)
- docker-compose.yml (DocuSeal + app)
- Makefile with run / tunnel / test-trigger targets
- Audit trail (JSONL, append-only)

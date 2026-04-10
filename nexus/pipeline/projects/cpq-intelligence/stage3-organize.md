# Stage 3 — Organize: cpq-intelligence
Date: 2026-04-09
Tool: Claude Code (new-project onboarding)
Status: [x] Complete

---

## Architecture Decisions

- Supabase PostgreSQL + Deno Edge Functions + Retool — low-code stack delivers in 8–10 weeks at $15–50K
- RLS via session variable `app.current_tenant_id` — cannot be bypassed at application layer
- Consent bound to `quote_id` (GDPR purpose limitation)
- Mock telemetry first — validate configurator logic before live XDR integration
- Separate repo from iOPEX — client deliverable, IP boundary protection

## Build Order

1. Schema + RLS + seed data (Wave 1) ✅
2. Edge Functions: device-activate, consent-revoke, telemetry-summary (Wave 2) ✅
3. Retool queries + JS transformers (Wave 3) ✅
4. Retool UI pages + modules (Wave 4) ✅
5. Wave 5 validation sign-off (in progress)
6. Admin UI — Manufacturer page (Weeks 7–8)
7. Live XDR telemetry swap (post-validation)

## Dependencies

| Dependency | Status | Notes |
|------------|--------|-------|
| Supabase project | ✅ Active | `ahrctpwydlldccoatpxk`, us-east-1 |
| Retool workspace | ✅ Active | — |
| CPQ_API_KEY | ✅ Set | In Supabase secrets |
| Cortex XDR / FortiTelemetry | ⏳ TBD | Post-validation live swap |

## AI Council Review (2026-04-09)

**Verdict:** CONDITIONAL APPROVE — 7.9/10

All 6 non-negotiable fixes resolved before Stage 4:
- [x] consent_version column added
- [x] normalizeTelemetry defensive fallback
- [x] device-activate DIY SKU rejection (422)
- [x] .env.example complete
- [x] Test 7 RLS automated baseline
- [x] Admin UI data flow spec

## Linked Artifacts

- **Repo:** https://github.com/jerm71279/cpq-intelligence
- **Runbook:** OneDrive/iOPEX/CPQ Intelligence/CPQ Intelligence - Delivery Runbook.docx
- **Supabase:** https://app.supabase.com/project/ahrctpwydlldccoatpxk

## Handoff to Stage 4

### Context for Code Session

**Project:** cpq-intelligence
**Goal this session:** Wave 5 sign-off + Admin UI build

**Files to create/modify:**
- `wave5_validation_tests.sh` — run and sign off
- `phase2_edge_functions/` — Admin UI edge functions (if needed)
- Retool Admin page — per `phase5_admin_ui_dataflow.md`

**Key constraints:**
- No GenAI layer — prototype scope only
- Telemetry stays mocked until explicit live swap instruction
- All writes must include `tenant_id` — no cross-tenant operations

**Do not:**
- Touch consent_version logic — it's correct as implemented
- Add features beyond the 100-SKU prototype scope
- Commit `.env` or any secrets

**Definition of done:**
- All Wave 5 automated tests PASS
- Manual RLS check documented
- Admin UI Weeks 7–8 delivered
- nexus_checkpoint run → project marked DELIVERED

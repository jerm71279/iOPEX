# Runbook 04 — Roles & Responsibilities
## CyberArk → KeeperPAM Migration | SHIFT System

**Scope:** Separation of duties between Lead Engineer (Accountable) and Migration Engineer (Responsible) for the full P0–P7 engagement.
**Applies to:** All migration phases from environment setup through decommission.
**Who holds this:** iOPEX delivery team — not shared externally without Lead Engineer approval.

---

## Role Definitions

| Role | Person | RACI | Mandate |
|------|--------|------|---------|
| Lead Engineer | Jeremy Smith (iOPEX) | **Accountable** | Owns all outcomes. Approves every live action. Signs all gates. Single point of authority for the engagement. |
| Migration Engineer | [TBD] (iOPEX) | **Responsible** | Prepares, monitors, troubleshoots, and recommends. Does not execute live actions without Lead Engineer sign-off. |
| Cisco InfoSec | CLIENT_INFOSEC team | Consulted | Security gate input, compliance review, permission sign-offs. |
| Cisco Stakeholders | Sponsor + IT Lead | Informed | Notified of phase completions, gate outcomes, and milestone reports. |

---

## Core Principle

> **Engineer 2 prepares. Jeremy decides and approves.**

No live phase run, gate advancement, client communication, or emergency action is initiated without Jeremy's explicit sign-off. This is not a workflow preference — it is the engagement's accountability model. All audit trail entries attributable to live execution must trace to Jeremy's approval.

---

## What Engineer 2 Can Do Independently

The following activities do not require explicit sign-off and can be initiated by Engineer 2:

- Start OpenClaw `shift-pmo` sessions
- Run **dry runs** for any phase (`python3 cli.py run P{N} --dry-run`)
- Check migration status (`python3 cli.py status`)
- Pull and review agent output reports
- Review audit logs (`output/logs/audit.jsonl`)
- Prepare gate readiness assessments (check criteria, draft summary — do not submit)
- Draft stakeholder reports (prepare content — do not send)
- Monitor dashboard for in-progress phases
- Troubleshoot and diagnose failures (do not re-run without sign-off)
- Update internal working notes and progress tracking

---

## What Requires Jeremy's Sign-Off

Every item below requires Jeremy's explicit approval before proceeding:

| Action | Why |
|--------|-----|
| Run any **live** phase (`cli.py run P{N}`) | Irreversible changes to live PAM data |
| Advance to next phase (`cli.py advance`) | Gate progression — Jeremy is the named approver |
| Sign off any Yellow Checkpoint gate | YC gates require named human approver per runbook |
| Re-run a failed agent after a failure | Root cause must be reviewed before retry |
| Trigger emergency unfreeze | Vault state change — high blast radius |
| Any rollback or remediation action | Requires assessment and decision authority |
| Submit any report to Cisco stakeholders | All external communications owned by Jeremy |
| Update the change management ticket | Formal project record — Jeremy accountable |
| Any deviation from the approved runbook | Must be reviewed and documented before acting |
| Modify `config.json` or Key Vault secrets | Production credential changes |
| Approve DP-01 or DP-02 decision records | Architecture decisions — Jeremy accountable |

---

## RACI Matrix by Phase

**Key:** R = Responsible (Engineer 2 prepares/executes) | A = Accountable (Jeremy signs off) | C = Consulted | I = Informed

### P0 — Environment Setup

| Activity | Eng 2 | Jeremy | Cisco InfoSec | Cisco Stakeholders |
|----------|-------|--------|---------------|--------------------|
| Azure infra deployment review | R | A | | |
| config.json preparation | R | A | | |
| Key Vault secret entry | R | A | | |
| Network connectivity tests | R | A | | |
| Preflight checks (15/15) | R | A | | |
| DP-01 decision (trigger method) | R | A | | |
| DP-02 decision (LLM provider) | R | A | | |
| Migration state initialisation | R | A | | |
| P0 sign-off | | A | C | |

### P1 — Discovery

| Activity | Eng 2 | Jeremy | Cisco InfoSec | Cisco Stakeholders |
|----------|-------|--------|---------------|--------------------|
| P1 dry run | R | A | | |
| P1 live execution | R | A | | |
| Discovery output review | R | A | | |
| NHI classification review | R | A | C | |
| Gap analysis review | R | A | C | |
| Permission loss report review | R | A | C | |
| YC-P1 gate assessment (draft) | R | | | |
| YC-P1 gate sign-off | | A | C | |
| Advance to P2 | | A | | I |

### P2 — Staging Validation

| Activity | Eng 2 | Jeremy | Cisco InfoSec | Cisco Stakeholders |
|----------|-------|--------|---------------|--------------------|
| P2 dry run | R | A | | |
| P2 live execution | R | A | | |
| Staging assertion review (10/10) | R | A | | |
| Platform plugin validation review | R | A | | |
| YC-P2 gate assessment (draft) | R | | | |
| YC-P2 gate sign-off | | A | | |
| Advance to P3 | | A | | I |

### P3 — Vault Creation & Permissions

| Activity | Eng 2 | Jeremy | Cisco InfoSec | Cisco Stakeholders |
|----------|-------|--------|---------------|--------------------|
| P3 dry run | R | A | | |
| P3 live execution | R | A | | |
| Permission application review | R | A | C | |
| Vault structure validation | R | A | | |
| App onboarding setup review | R | A | | |
| YC-P3 gate assessment (draft) | R | | | |
| YC-P3 gate sign-off | | A | C | |
| Advance to P4 | | A | | I |

### P4 — Pilot Migration

| Activity | Eng 2 | Jeremy | Cisco InfoSec | Cisco Stakeholders |
|----------|-------|--------|---------------|--------------------|
| P4 dry run | R | A | | |
| P4 live ETL execution | R | A | | |
| Heartbeat results review | R | A | | |
| Failure diagnosis (if any) | R | A | | |
| Agent re-run (after failure) | R | A | | |
| YC-P4 gate assessment (draft) | R | | | |
| YC-P4 gate sign-off | | A | C | I |
| Advance to P5 | | A | | I |

### P5 — Production Migration (Waves 1–5)

| Activity | Eng 2 | Jeremy | Cisco InfoSec | Cisco Stakeholders |
|----------|-------|--------|---------------|--------------------|
| Per-wave dry run | R | A | | |
| Per-wave live ETL execution | R | A | | |
| Per-wave heartbeat review | R | A | | |
| Integration repointing review | R | A | C | |
| Compliance evidence collection | R | A | C | |
| Per-wave YC-P5 gate assessment | R | | | |
| Per-wave YC-P5 gate sign-off | | A | C | I |
| Advance wave / advance to P6 | | A | | I |
| Stakeholder progress report (draft) | R | | | |
| Stakeholder progress report (send) | | A | | I |

### P6 — Parallel Running & Cutover

| Activity | Eng 2 | Jeremy | Cisco InfoSec | Cisco Stakeholders |
|----------|-------|--------|---------------|--------------------|
| Hybrid fleet monitoring | R | A | | |
| Weekly heartbeat review | R | A | | |
| Stuck account diagnosis | R | A | | |
| Integration repointing confirmation | R | A | C | |
| Cutover preparation review | R | A | C | |
| YC-P6 weekly gate assessment (draft) | R | | | |
| YC-P6 gate sign-off | | A | C | I |
| Cutover execution authorisation | | A | C | I |
| Advance to P7 | | A | | I |

### P7 — Decommission & Close-Out

| Activity | Eng 2 | Jeremy | Cisco InfoSec | Cisco Stakeholders |
|----------|-------|--------|---------------|--------------------|
| Audit trail compilation | R | A | | |
| Compliance evidence finalisation | R | A | C | |
| CyberArk decommission preparation | R | A | C | |
| CyberArk decommission execution | R | A | C | I |
| Service account revocation (`svc-iopex-migration`) | R | A | C | |
| KeeperPAM OAuth2 client revocation | R | A | C | |
| Final audit report (draft) | R | | | |
| Final audit report sign-off | | A | C | I |
| YC-P7 gate sign-off | | A | C | I |
| Knowledge transfer to client | R | A | | I |
| Engagement close-out | | A | | I |

---

## OpenClaw Operations — Split

| OpenClaw Action | Engineer 2 | Jeremy |
|-----------------|-----------|--------|
| Start shift-pmo session | ✓ | ✓ |
| Run dry run (`P{N} dry run`) | ✓ | ✓ |
| Check migration status | ✓ | ✓ |
| Review agent output reports | ✓ | ✓ |
| Check gate readiness | ✓ (draft only) | ✓ |
| Run live phase (`Run P{N} live`) | Prepare + request | **Sign-off required** |
| Advance phase (`Advance to P{N}`) | Prepare + request | **Sign-off required** |
| Generate stakeholder report | Prepare draft | **Sign-off required to send** |
| Emergency unfreeze | Diagnose + request | **Sign-off required** |

---

## Escalation Rules

Engineer 2 must stop and notify Jeremy immediately when:

- Any Yellow Checkpoint gate reaches **BLOCK** or **CRITICAL** status
- Any agent fails unexpectedly mid-phase
- A heartbeat result falls below threshold (< 95% for P4, < 100% for P6)
- Any Cisco stakeholder contacts Engineer 2 directly
- Any runbook deviation is required
- An emergency unfreeze or rollback may be needed

**Rule:** Engineer 2 documents the situation and waits. Jeremy decides the path forward.

---

## Communication Boundaries

| Channel | Engineer 2 | Jeremy |
|---------|-----------|--------|
| iOPEX internal Slack / Teams | ✓ | ✓ |
| OpenClaw shift-pmo sessions | ✓ | ✓ |
| Cisco stakeholder email / Teams | Draft only | **Sends** |
| Change management ticket | Update working notes | **Formal entries** |
| Gate sign-off documents | Prepare | **Signs** |
| Executive status reports | Prepare content | **Approves + delivers** |

---

## Next Step

→ **[P0_environment_setup.md](P0_environment_setup.md)** — Begin environment setup with roles confirmed.

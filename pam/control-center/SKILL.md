---
name: pam-dev-oversight
description: >
  Development oversight and SWOT analysis skill for the iOPEX AI-powered PAM
  migration and identity lifecycle tool. Use this skill whenever Maverick asks
  to evaluate a new feature, agent, integration, flow, or tool addition to the
  PAM system — or when reviewing development direction, identifying gaps,
  prioritizing roadmap items, or conducting competitive analysis against firms
  like KeyData Cyber. Trigger on any of: "should I build", "is this worth adding",
  "evaluate this feature", "what's missing", "SWOT", "review this idea",
  "roadmap", "what should I build next", "gap analysis", or any new capability
  proposed for the PAM agent system or identity lifecycle automation flows.
---

# PAM Tool Development Oversight

Oversight framework for the iOPEX AI-powered PAM migration tool and identity
lifecycle automation system. Every evaluation runs through two lenses:

1. **5-Layer AI OS Scoring** — from `council.py:review_tool_5layer()`
2. **SWOT + Gap Gate** — checked against known functional gaps and competitive position

---

## The 5-Layer AI OS Model

Sourced from `core/Secondbrain/multi-ai-orchestrator/council.py`.

| Layer | Name | Scope |
|-------|------|-------|
| 1 | **Interface** | API/CLI design, authentication, input validation, data formats |
| 2 | **Intelligence** | Query processing, intent classification, NLP, context awareness |
| 3 | **Orchestration** | Workflow management, pipeline execution, state, error recovery |
| 4 | **Agents** | Specialized execution units, tool integrations, safety guardrails |
| 5 | **Resources** | External services, data stores, MCP servers, caching, rate limiting |

### Infrastructure Mapping (DOCKER.md — 13 services)

| Layer | Name | Services |
|-------|------|----------|
| 1 | Models | Ollama (local LLM, GPU) |
| 2 | Persistence | PostgreSQL, Qdrant (vector DB) |
| 3 | Services | data-processing, rag-engine, engineering-api, call-flow, agents |
| 4 | Orchestration | Nginx gateway (path-based routing) |
| 5 | UI/Interface | n8n, Open WebUI, nginx-ssl |

---

## Evaluation Protocol

When any new feature, agent, flow, or tool is proposed, run both methods from
`council.py` in sequence.

---

### METHOD 1 — `review_tool_5layer()`

Score the proposed addition **1–10 on each layer**. A score of 1 means the
layer is completely unaddressed; 10 means fully implemented and hardened.

```
LAYER 1 — INTERFACE        [score /10]
  - Does it have a clean API or CLI surface?
  - Is input validated before processing?
  - Are auth requirements defined?
  - Are data formats standardized (JSON schema, typed payloads)?

LAYER 2 — INTELLIGENCE     [score /10]
  - Does it use an LLM or ML component meaningfully?
  - Does it classify intent or context before acting?
  - Does it handle ambiguous or edge-case inputs intelligently?
  - Is there NLP-driven decision making vs. pure rule execution?

LAYER 3 — ORCHESTRATION    [score /10]
  - Does it integrate into the existing gate-based pipeline?
  - Does it handle state between steps?
  - Does it have defined error recovery and rollback paths?
  - Does it support parallel vs. sequential execution correctly?

LAYER 4 — AGENTS           [score /10]
  - Is this a discrete, single-responsibility agent?
  - Does it have safety guardrails (no unchecked destructive actions)?
  - Does it integrate with existing Agent 01-15 + DX-01, DX-02 framework?
  - Are tool integrations sandboxed and auditable?

LAYER 5 — RESOURCES        [score /10]
  - What external services does it depend on?
  - Are rate limits and caching considered?
  - Is it MCP-server compatible or portable?
  - Are data stores (PostgreSQL, Qdrant) used appropriately vs. in-memory?
```

**Minimum bar to approve development:** Total score >= 30/50.
**Layers that must score >= 5 before any other:** Layer 3 (Orchestration) and Layer 4 (Agents).
**Reason:** The PAM tool lives and dies on reliable orchestration and safe agent execution. A brilliant Layer 2 Intelligence feature that isn't gate-gated (Layer 3) is a risk, not an asset.

---

### METHOD 2 — `review_idea_5layer()`

Evaluate the **integration fit** — how the proposed idea slots into the existing
system without breaking existing layers.

Ask and answer each question explicitly:

```
1. INTERFACE FIT
   Does it reuse existing auth patterns (Managed Identity, CyberArk REST,
   Conjur JWT)? Or does it introduce a new auth model that needs new credentials?

2. INTELLIGENCE FIT
   Does it need its own LLM prompt/context, or can it reuse existing agent
   prompts? Will it increase Azure OpenAI token usage significantly?

3. ORCHESTRATION FIT
   Can it be inserted as a gate in the existing 8-phase, 15-agent pipeline
   (P0-P7), or does it require restructuring? Does it respect the FREEZE →
   EXECUTE → VERIFY → UNFREEZE pattern? Does it respect the Yellow Checkpoint
   state machine (FIRE → CLASSIFY → NOTIFY → WINDOW → BOUNDARY → RESOLVE)?

4. AGENT FIT
   Which of the 15+2 agents does this enhance, or is it Agent 16+?
   New Splunk SIEM log schema?

5. RESOURCE FIT
   New external service dependency? New Safe in CyberArk? New Qdrant collection?
   New PostgreSQL table? Does it fit the Docker service layer without a new container?
```

**Red flags that block development:**
- Introduces stored credentials (violates Managed Identity design)
- Bypasses gate approval (violates rollback architecture)
- Sends PAM data to a public API endpoint (violates data sovereignty)
- Adds on-prem infrastructure (contradicts cloud-native direction)
- Creates a new external dependency with no rate limit handling

---

## Known Functional Gaps (Gap Registry)

These are confirmed development debts identified through competitive analysis
against KeyData Cyber and functional review. Every new feature should be checked:
does it **close a gap** or **add net-new capability**?

| Gap ID | Gap | Priority | Status |
|--------|-----|----------|--------|
| G-01 | Multi-vendor PAM adapter (BeyondTrust, Delinea, HashiCorp, AWS, Azure, GCP) | HIGH | **CLOSED** — Agent 11 (Source Adapter) supports CyberArk, BeyondTrust, Secret Server, HashiCorp, AWS, Azure, GCP |
| G-02 | Application onboarding automation (CPM plugin mgmt) | HIGH | **CLOSED** — Agent 14 (Onboarding) implements 10-step pipeline |
| G-03 | Non-human identity handling (service accounts, API keys) | HIGH | **CLOSED** — Agent 12 (NHI Handler) classifies 7 NHI subtypes with weighted multi-signal scoring |
| G-04 | Dependency mapping before migration (consumers of credentials) | CRITICAL | **CLOSED** — Agent 09 (Dependency Mapper) scans IIS, Windows services, scheduled tasks, Jenkins, scripts, configs |
| G-05 | Hybrid environment state (mixed on-prem/cloud fleet mgmt) | MEDIUM | **CLOSED** — Agent 15 (Hybrid Fleet) implements parallel-run with gradual traffic shift 10%→50%→90%→100% |
| G-06 | IaaS/SaaS connector layer (AWS Secrets Manager, Azure KV, GCP) | MEDIUM | **OPEN** — AWS Secrets Manager, Azure Key Vault, GCP Secret Manager not yet built |
| G-07 | Platform plugin validation and migration | MEDIUM | **CLOSED** — Agent 13 (Platform Plugins) validates/creates templates, deploys connection components |
| G-08 | Staging environment test harness (pre-production validation) | HIGH | **CLOSED** — Agent 10 (Staging Validation) runs 10-assertion mini-ETL pipeline, hard-blocks production on failure |

**When evaluating any new feature:**
- If it closes G-06 → high commercial value (unlocks multi-cloud PAM governance)
- If it enhances an existing closed gap → evaluate via METHOD 1 + METHOD 2

---

## SWOT Framework

Run this SWOT whenever:
- Evaluating a significant new capability
- Preparing for a new client engagement
- Comparing against a competitor's offering
- Quarterly development review

### Current SWOT Snapshot (as of March 2026)

**STRENGTHS**
- 15-agent + 2 DX agent autonomous migration system with gate-gated rollback
- Dual-option migration: CyberArk → Privilege Cloud (same-vendor) OR CyberArk → Delinea Secret Server + StrongDM (cross-vendor)
- Multi-vendor source adapter (BeyondTrust, HashiCorp, cloud vaults) — G-01 closed
- Dependency mapping before migration prevents production outages — G-04 closed
- 10-assertion staging validation hard-blocks production on failure — G-08 closed
- Non-human identity classification with 7 subtypes and rotation strategies — G-03 closed
- Yellow Checkpoint state machine for cross-phase AI contextual awareness
- Auto-generated compliance artifacts (audit trail as byproduct, not deliverable)
- Identity lifecycle automation: 3 flows (onboard / offboard / weekly sync)
- Azure-native architecture with Managed Identity — zero stored credentials
- 5-Layer AI OS model provides structured evaluation framework for all additions
- Cost-per-migration scales with compute, not headcount
- ServiceNow change management integrated (INC for yellows, CHG for reds)

**WEAKNESSES**
- Single engagement reference (Cisco/iOPEX) — limited proof-of-concept breadth
- No cloud secrets connector layer (G-06) — AWS/Azure/GCP discovery not yet built
- Flow 3 weekly sync uses rule-based logic, not true AI agent reasoning
- DX Portal not yet in production (DX-01 and DX-02 in active development)

**OPPORTUNITIES**
- G-06 cloud secrets connectors position for multi-cloud PAM governance
- Packaging as PAM-Migration-as-a-Service (dual-option) creates new engagement model
- Yellow Checkpoint cross-phase AI reasoning is a differentiator — demonstrates operational AI maturity
- DX Portal (vendor-agnostic) unlocks self-service credential management
- Multi-client deployment packaging (same orchestrator, different configs)
- AI-native audit generation is a compliance differentiator no traditional firm has built
- Multi-agent parallel execution compresses timelines vs. consultant-paced competition

**THREATS**
- CyberArk changes its migration API or partner program → core agents need rework
- Azure OpenAI model deprecation requires prompt re-engineering across all agents
- Single-client proof base makes procurement approval difficult in enterprise cycles
- Delinea acquisition/restructuring risk could affect Option A roadmap

---

## Development Decision Tree

When a new feature or idea is proposed, work through this in order:

```
1. Does it close a CRITICAL gap (G-04 dependency mapping)?
   YES → Prioritize immediately. Score with review_tool_5layer() but approve
         pending Layer 3 and Layer 4 minimum bars.
   NO  → Continue to step 2.

2. Does it close a HIGH gap (G-01, G-02, G-03, G-08)?
   YES → Score with both methods. Approve if total >= 30/50 and L3+L4 >= 5.
   NO  → Continue to step 3.

3. Does it appear in the SWOT as an Opportunity?
   YES → Score with both methods. Approve if total >= 35/50.
   NO  → Continue to step 4.

4. Is it net-new capability (not closing a gap, not an opportunity)?
   → Score with both methods. Approve only if total >= 40/50.
   → Explain which gap or opportunity it indirectly supports.
   → Flag if it introduces a new dependency (Layer 5 review required).

5. Does it introduce any red flags?
   ANY → Block development. Document the red flag. Re-propose without it.
```

---

## Architecture Integrity Rules

These are non-negotiable constraints. Any proposed addition that violates one
is rejected regardless of 5-layer score.

| Rule | Constraint |
|------|-----------|
| ARC-01 | No stored credentials anywhere — Managed Identity, Conjur JWT, or OAuth2 client_credentials — no stored plaintext credentials |
| ARC-02 | No PAM data to public API endpoints — private endpoints or on-prem LLM only |
| ARC-03 | Every destructive action requires a pre-built rollback plan |
| ARC-04 | Every agent action logs to SIEM with timestamp, actor, and outcome |
| ARC-05 | No agent executes without gate approval for CRITICAL/HIGH risk operations |
| ARC-06 | No new on-prem infrastructure — cloud-native or ExpressRoute-connected only |
| ARC-07 | Every flow opens and closes a ServiceNow CHG with evidence |
| ARC-08 | Dependency mapping (Agent 09) MUST be run before any credential migration. Hard-enforced by Agent 04 preflight gates. |
| ARC-09 | Every yellow checkpoint must carry a 5-field AI rationale (what_fired, root_cause, cross_system_context, risk_assessment, recommended_action). Yellows without rationale are rejected. |
| ARC-10 | Yellow checkpoints open ServiceNow INC tickets. Escalation to RED upgrades INC to CHG. No yellow is silently dismissed — all are logged to SIEM. |

---

## Feature Evaluation Output Template

When completing an evaluation, produce output in this format:

```
═══════════════════════════════════════════════
FEATURE EVALUATION: [Feature Name]
═══════════════════════════════════════════════

PROPOSED: [One-line description]
TYPE: [New Agent / Enhancement / New Flow / Adapter / Infrastructure]
GAP ADDRESSED: [G-XX or "Net-new"]

── 5-LAYER SCORE (review_tool_5layer) ─────────
Layer 1 · Interface      [X/10] — [one-line rationale]
Layer 2 · Intelligence   [X/10] — [one-line rationale]
Layer 3 · Orchestration  [X/10] — [one-line rationale]  ← must be >=5
Layer 4 · Agents         [X/10] — [one-line rationale]  ← must be >=5
Layer 5 · Resources      [X/10] — [one-line rationale]
TOTAL                    [X/50]

── INTEGRATION FIT (review_idea_5layer) ───────
Interface fit:      [PASS/WARN/FAIL] — [note]
Intelligence fit:   [PASS/WARN/FAIL] — [note]
Orchestration fit:  [PASS/WARN/FAIL] — [note]
Agent fit:          [PASS/WARN/FAIL] — [note]
Resource fit:       [PASS/WARN/FAIL] — [note]

── ARCHITECTURE INTEGRITY CHECK ───────────────
[List any ARC rules checked. Flag violations.]

── SWOT IMPACT ────────────────────────────────
Closes weakness:    [Y/N] — [which one]
Activates opportunity: [Y/N] — [which one]
Introduces new threat: [Y/N] — [which one]

── VERDICT ────────────────────────────────────
[APPROVE / APPROVE WITH CONDITIONS / DEFER / REJECT]
Conditions (if any): [List]
Recommended sprint: [Next / Q2 / Backlog]
═══════════════════════════════════════════════
```

---

## Roadmap Priority Stack

### COMPLETED

| # | Gap / Item | Agent | Status |
|---|-----------|-------|--------|
| 1 | G-04 — Dependency Mapper | Agent 09 | CLOSED |
| 2 | G-08 — Staging Validation | Agent 10 | CLOSED |
| 3 | G-03 — NHI Handler | Agent 12 | CLOSED |
| 4 | G-01 — Multi-vendor Adapter | Agent 11 | CLOSED |
| 5 | G-02 — App Onboarding | Agent 14 | CLOSED |
| 6 | G-05 — Hybrid Fleet | Agent 15 | CLOSED |
| 7 | G-07 — Platform Plugins | Agent 13 | CLOSED |

### ACTIVE PRIORITIES

1. **Yellow Checkpoint System**
   Cross-phase AI contextual awareness with ServiceNow INC/CHG integration.
   State machine: FIRE → CLASSIFY → NOTIFY → WINDOW → BOUNDARY → RESOLVE.

2. **G-06 — Cloud Secrets Connectors**
   AWS Secrets Manager, Azure Key Vault, GCP Secret Manager discovery and governance.

3. **DX Portal Production**
   Spring Boot 3.2 developer portal with PamVendorAdapter interface. DX-01 + DX-02 active.

4. **Flow 3 AI Upgrade**
   Replace rule-based drift with AI agent reasoning for edge cases.

5. **Multi-client Packaging**
   Same orchestrator, different config.json, automated deployment.

---

## Reference Architecture Context

For full system context when evaluating new features, refer to:

- `15-agent + 2 DX agent migration system` — Agents 01-15 + DX-01, DX-02, gate model, rollback logic
- `PAM Migration Control Center` — FastAPI + Vanilla JS dashboard for orchestration visibility
- `Yellow Checkpoint State Machine` — Cross-phase AI contextual awareness with ServiceNow INC/CHG integration
- `Identity Lifecycle Flows` — Flow 1 (onboard), Flow 2 (offboard), Flow 3 (weekly sync)
- `KeyData Cyber competitive analysis` — functional gaps, delivery model comparison
- `Conjur OSS → Cloud runbook` — dual-track migration mechanics, JWT auth, Vault Sync
- `ExpressRoute or VPN connectivity` — Managed Identity, Azure OpenAI private endpoint

The 5-layer scoring from `council.py` is the canonical evaluation gate.
Infrastructure changes must map to the 13-service Docker architecture in `DOCKER.md`.

---

## Yellow Checkpoint Sub-Component Design

Yellow Checkpoints are now implemented in the PAM Migration Control Center as the AI orchestrator's cross-phase contextual awareness layer. The orchestrator uses yellow functionality to understand context across all phases and coordinate real-time decisions. Each yellow opens a ServiceNow INC ticket; escalation to RED upgrades to CHG.

Yellow is the most complex of the three checkpoint types. Full state machine:

### State Sequence
`FIRE → CLASSIFY → NOTIFY → COUNTER CHECK → WINDOW → BOUNDARY CHECK → RESOLVED`

### FIRE State Actions
- Detect the triggering condition
- Open ServiceNow INC (informational ticket)
- Log to SIEM with full context payload

### 4 Yellow Types (classification determines routing and SLA)

| Type | SLA | Route | Expiry Behavior |
|------|-----|-------|-----------------|
| OPERATIONAL | 24hr | IAM Team queue | Escalate to IAM Manager |
| SECURITY | 2hr | IAM Team + SecOps parallel | Auto-promote to RED |
| COMPLIANCE | 48hr | IAM Manager + Compliance Officer | Auto-promote to RED, notify CISO |
| EDGE CASE | 24hr | IAM Team queue | Carry forward as RED into next phase |

### Accumulation Thresholds (per-phase counter)

| Yellow Count | Action |
|-------------|--------|
| 0-2 | Proceed, log to SIEM |
| 3-4 | Notify IAM Lead, continue |
| 5+ | Auto-promote trigger armed — next yellow in phase becomes RED |

### Response Window Paths (after notification sent)

- **Human dismisses** → RESOLVED. SIEM logs actor + timestamp.
- **Human escalates** → Promoted to RED. Pipeline halts.
- **Human snoozes** → Window resets once. Second expiry cannot be snoozed.
- **Window expires with no response** → Behavior per profile (auto-rollback | promote RED | escalate manager). Never silently dismissed.

### Phase Boundary Rules

- OPERATIONAL unresolved at boundary → carry forward, new 24hr window starts
- SECURITY unresolved at boundary → **auto-promote to RED**, next phase blocked
- COMPLIANCE unresolved at boundary → **auto-promote to RED**, next phase blocked
- EDGE CASE unresolved at boundary → **carry forward as RED** into next phase

### AI Rationale Structure (required on every yellow)

Every yellow must carry a 5-field AI-generated rationale:
1. **What fired** — the specific condition detected
2. **Root cause hypothesis** — why it fired, cross-referenced against available data
3. **Cross-system context** — what other systems show for this account/record
4. **Risk assessment** — OPERATIONAL / SECURITY / COMPLIANCE / EDGE CASE with severity
5. **Recommended action** — specific next step, not "review required"

A yellow rationale is a **decision brief**, not a log entry. The human receiving it
must be able to act without digging into raw systems. This is where Layer 2 Intelligence
earns its score — yellow is the primary output surface for agent reasoning.

### Yellow Preset Profile Examples

| Profile | SECURITY SLA | OPERATIONAL SLA | Accumulation Threshold |
|---------|-------------|-----------------|----------------------|
| SOX | 2hr | 24hr | 4 |
| HIPAA | 1hr | 24hr | 3 |
| PCI-DSS | 1hr | 12hr | 3 |
| Enterprise Standard | 2hr | 24hr | 5 |
| Fast Track | 4hr | 48hr | 8 |
# iOPEX Ecosystem Map

> The lobby for anyone — human or AI — entering this workspace for the first time.
> Each project is a different iOPEX customer engagement. All are demo-stage on local WSL, heading to production.

---

## Quick Reference

| Project | Purpose | Status | Port(s) | CLAUDE.md |
|---------|---------|--------|---------|-----------|
| **nexus-core** | Universal agent harness — runner discovery, scoped secrets, task ledger, cost tracking | V0.3.2 (V1 target: SHIFT runner) | CLI only | `nexus-core/CLAUDE.md` |
| **iOPEX/pam** | SHIFT PAM Migration — 15-agent CyberArk to KeeperPAM/Secret Server pipeline | Active (P2, Week 14) | — | `iOPEX/CLAUDE.md` |
| **iOPEX/digital-expert** | Nexus Knowledge Bot — LangGraph RAG + Telegram (@iOPEXpert_Bot) | Active | 8001 (API) | `iOPEX/CLAUDE.md` |
| **iOPEX/frontdoor-platform** | Enterprise Service Portal — React + Supabase + Gemini intent classification | Phase 2 | Render.com | `iOPEX/CLAUDE.md` |
| **iOPEX/mcp-hub** | MCP Tool Aggregator — FastMCP SSE for shift/iopex/pam-status tools | Active | 8002 (int) / 8010 (host) | — |
| **iOPEX/contract-intelligence** | Document Automation — 10-stage contract processing pipeline | Active | — | — |
| **ai-ops-tools** | MSP Operations Stack — 5-layer Docker stack for OberaConnect | Mature | 8080 (gateway) | — |
| **matchforge** | AI Job Matching — 6-factor matching + skill gap + ATS optimization | MVP complete | 8001 (demo) | — |
| **Master-Prompt** | Project Scaffolding — CRISP-E interview + 8-phase scaffold generation | Active | — | — |
| **CCNA** | Network Certification — Visual learning tools (HTML5/React/three.js) | Active | Hostinger | — |
| **JeremyITLab-CCNA** | CCNA Study — Anki flashcards + PacketTracer labs | Reference | — | — |
| **Azure** | Infrastructure Docs — Network setup, S2S VPN, ROBOCOPY guides | Reference | — | — |
| **setco** | DC Migration — Migration checklists + data sync plans | Reference | — | — |

---

## How Projects Connect

```
                          Claude Code (local dev)
                                  |
                           nexus-core CLI
                    (runner discovery, task ledger)
                     /        |        |        \
                    /         |        |         \
            SHIFT Runner  PMO Runner  Ingest    FrontDoor
            (shift.py)    (pmo.py)    Runner    Runner
                |             |         |          |
                v             v         v          v
        iOPEX/pam         PMO Brain   Digital    FrontDoor
        15 agents         directives  Expert     Portal
        P0-P7 phases      + waves     LangGraph  React+Supabase
                |             |         |
                v             v         v
              MCP Hub (port 8010) <--- aggregates all tools
              /mcp/shift  /mcp/iopex  /mcp/pam-status
                                |
                          Claude Code MCP
                          (available in every session)

    Persistence Layer:
    PostgreSQL (5432) ─── pgvector KB, checkpoints, audit
    Redis (6379) ──────── session state, caching
    Qdrant (6333) ─────── vector DB (ai-ops-tools)

    Independent Stacks:
    ai-ops-tools ──── Docker Compose (MSP ops, UniFi, NinjaOne, Azure MCP)
    matchforge ────── Standalone FastAPI (job matching MVP)
    CCNA ──────────── Static site (Hostinger)
```

---

## Getting Started

**First time here?**
1. Read this file (you're doing it)
2. Read `Master-Prompt/workspace/SOUL.md` for the Nexus persona identity
3. Read `Master-Prompt/workspace/USER.md` for how to work with Jeremy
4. Read the relevant project's `CLAUDE.md` for project-specific context

**Running the iOPEX stack locally:**
```bash
cd /home/maverick/projects/iOPEX
docker compose up -d                    # Start core stack
curl http://localhost:8080/health        # Verify gateway
curl http://localhost:8080/api/services  # Service registry
```

**Running ai-ops-tools:**
```bash
cd /home/maverick/projects/ai-ops-tools
docker compose up -d                    # Core stack
docker compose --profile chat up -d     # + Open WebUI
```

**Adding a new customer project:**
Use the Master-Prompt scaffold system:
1. Open `Master-Prompt/SCAFFOLD-ONBOARDING-PROMPT.md`
2. Run through the CRISP-E interview (8 phases)
3. Scaffold generates README, CLAUDE.md, ARCHITECTURE.md, AGENTS.md, etc.
4. Add as a nexus-core runner (~50 lines) if it needs agent orchestration

---

## Project Details

### nexus-core — Agent Harness
- **Location:** `/home/maverick/projects/nexus-core`
- **What:** Python harness that every iOPEX agent plugs into. Auto-discovers runners, scopes secrets, tracks tasks, counts costs.
- **Key pattern:** `BaseRunner` ABC — implement `run()` + `describe()` + `required_secrets`, drop in `runners/`, done.
- **Docs:** `CLAUDE.md`, `ARCHITECTURE.md`

### iOPEX/pam — SHIFT PAM Migration
- **Location:** `/home/maverick/projects/iOPEX/pam`
- **What:** 15-agent AI orchestrator for CyberArk to KeeperPAM (Option A) or Secret Server (Option B). 80-week methodology with phase gates P0-P7.
- **Key files:** `coordinator.py`, `agents/agent_01` through `agent_15`, `core/state.py`
- **Docs:** `iOPEX/CLAUDE.md` (comprehensive)

### iOPEX/digital-expert — Nexus Knowledge Bot
- **Location:** `/home/maverick/projects/iOPEX/digital-expert`
- **What:** LangGraph RAG agent serving iOPEX knowledge via Telegram (@iOPEXpert_Bot) and FastAPI. Hybrid BM25 + pgvector retrieval. Confidence-gated with Tavily web fallback.
- **Key files:** `agent_api/agent.py` (LangGraph), `run.py` (bot), `ingest/ingest.py`, `tenants/tenants.json`
- **Domains:** pam, zerotrust, network, secops, cloud, ai

### iOPEX/frontdoor-platform — Enterprise Portal
- **Location:** `/home/maverick/projects/iOPEX/frontdoor-platform`
- **What:** ServiceNow-style AI portal. React + Supabase + Gemini 2.5 Flash for intent classification. White-labeled per customer.
- **Deploy:** Render.com (static SPA)

### iOPEX/mcp-hub — MCP Tool Aggregator
- **Location:** `/home/maverick/projects/iOPEX/mcp-hub`
- **What:** FastMCP SSE server aggregating shift, iopex, and pam-status tool groups. Stateless proxy.
- **Port:** 8002 internal, 8010 host-mapped

### ai-ops-tools — MSP Operations Stack
- **Location:** `/home/maverick/projects/ai-ops-tools`
- **What:** 5-layer Docker stack for OberaConnect MSP workflows. Nginx gateway, 5 microservices, postgres + qdrant, optional Ollama/Open WebUI.
- **MCP integrations:** UniFi, NinjaOne, Azure/M365, Keeper Security
- **Docs:** Inline comments in `docker-compose.yml`

### matchforge — AI Job Matching
- **Location:** `/home/maverick/projects/matchforge`
- **What:** 6-factor AI job matching (skills, experience, salary, location), dual skill gap analysis, ATS optimization, LLM resume parsing.
- **Run:** `DEMO_MODE=true uvicorn app.main:app --port 8001 --reload`

### Master-Prompt — Project Scaffolding
- **Location:** `/home/maverick/projects/Master-Prompt`
- **What:** AI project scaffolding system. CRISP-E interview + 8-phase scaffold + Expert Panel + Red Team.
- **Key files:** `SCAFFOLD-ONBOARDING-PROMPT.md`, `workspace/SOUL.md`, `workspace/USER.md`, `workspace/TOOLS.md`

### CCNA / JeremyITLab — Network Certification
- **Location:** `/home/maverick/projects/CCNA`, `/home/maverick/projects/JeremyITLab-CCNA`
- **What:** Visual CCNA learning tools (HTML5/React/three.js animations) + Anki flashcards + PacketTracer labs.
- **Deploy:** Hostinger (jitprojects.blog)

---

## Authoritative Documentation

| What You Need | Where To Find It |
|---------------|-----------------|
| Project-specific context | `{project}/CLAUDE.md` |
| System architecture | `{project}/ARCHITECTURE.md` |
| Agent roster & orchestration | `{project}/AGENTS.md` |
| Nexus persona & identity | `Master-Prompt/workspace/SOUL.md` |
| Tools, ports & services | `Master-Prompt/workspace/TOOLS.md` |
| How to work with Jeremy | `Master-Prompt/workspace/USER.md` |
| AI Counsel analysis | `.claude/plans/reflective-sauteeing-fog.md` |
| This ecosystem map | `ECOSYSTEM.md` (you are here) |

---

## Intelligent Hill Position Map

Where each component sits on theMITmonk's prompting sophistication scale:
zero-shot (Camp 0) -> one-shot (Camp 1) -> few-shot (Camp 2) -> chain-of-thought (Camp 3) -> agents (Camp 4)

| Component | Current Camp | Evidence | Could Climb To |
|-----------|-------------|----------|----------------|
| SHIFT 15-agent pipeline | **Camp 4** (Agents) | Autonomous multi-agent with state, phases, gates, crash recovery | Summit |
| PMO Brain | **Camp 4** (Agents) | Directive/status/wave/escalate subcommands via nexus-core | Summit |
| Digital Expert RAG | **Camp 3** (CoT) | LangGraph graph: retrieve -> confidence gate -> respond OR web augment | Camp 4: add self-correction loops, multi-step reasoning |
| Master-Prompt scaffold | **Camp 3** (CoT) | Multi-phase interview with expert panels, red team | Camp 4: auto-generate based on prior project patterns |
| Telegram quick queries | **Camp 2** (Few-shot) | Grounded by RAG retrieval documents | Camp 3: explicit reasoning chains in responses |
| FrontDoor intent classifier | **Camp 1** (One-shot) | Gemini Flash single-pass classification | Camp 2: few-shot examples per customer domain |
| matchforge matching | **Camp 2** (Few-shot) | Sentence transformers + 6-factor scoring | Camp 3: explicit match reasoning with trade-off explanation |
| MCP Hub | **N/A** (proxy) | Stateless tool aggregator | N/A |
| ai-ops-tools agents | **Camp 3** (CoT) | Multi-tool orchestration with reasoning | Camp 4: full autonomous workflows |

---

## Spotter vs. Wheelchair Audit

theMITmonk's principle: For information tasks, AI removes friction. For transformation tasks, AI ADDS friction. AI should be a gym spotter, not a wheelchair.

### Currently Acting as Spotter (augmenting human capability)

- **SHIFT phase gates** — AI recommends, human approves at every gate. No autonomous decisions on production credential systems.
- **Digital Expert confidence gate** — Below 0.55, system admits "I don't have high-confidence knowledge" and goes to web. Doesn't hallucinate.
- **PMO Brain** — Surfaces blockers and escalations, doesn't resolve them. Forces human to confront what they might prefer to ignore.
- **nexus-core runner pattern** — Human writes the runner (architecture decisions), framework handles infrastructure (boilerplate). Clear separation.
- **CCNA study tools** — Jeremy is actively learning networking, not delegating understanding. Building visual tools reinforces learning (teach-to-learn).

### Wheelchair Risk Areas

| Area | Risk | Mitigation |
|------|------|-----------|
| **Master-Prompt scaffolding** | If scaffolding is so complete the developer never thinks about architecture, the scaffold becomes a crutch | CRISP-E interview forces human to articulate decisions before generation. DRAG classification (Phase 1.5) makes delegation conscious. |
| **DRAG over-delegation** | If too much moves to Zone 1 (delegate freely), critical thinking about Zone 2 activities atrophies over time | Quarterly review: "What was Zone 2 last quarter that's now Zone 1? Was that intentional or drift?" |
| **Code generation** | If Claude Code writes all code and Jeremy only reviews, implementation skill atrophies. Progressive overload principle says write harder things yourself. | Tag in CLAUDE.md which files are "human-authored." Deliberately write critical components (state.py, coordinator.py, agent logic) by hand. Use AI as reviewer/spotter. |
| **Knowledge base answers** | If consultants always defer to Digital Expert, their own domain expertise may plateau | "Teach to learn" practice: consultants regularly contribute knowledge docs, not just consume answers. The act of writing for the bot is learning. |
| **Eval dependency** | If eval harness auto-validates everything, manual quality review of answers stops | Eval is a floor, not a ceiling. Periodic manual review of edge-case queries stays in the workflow. |

### Progressive Overload Opportunities

These are areas where Jeremy can deliberately add friction to build capability:

1. **Write one new nexus-core runner from scratch per quarter** — without scaffolding, to keep the "architecture muscles" active
2. **Manually review 10 Digital Expert answers per week** — not just the eval scores, but the actual response quality
3. **Present SHIFT methodology to a client without the bot** — to ensure the knowledge lives in Jeremy's head, not just the database
4. **Hand-code one critical agent per engagement** — the one that makes the architectural decision, not the DRAG grunt work

---

## Deployment Status

All projects are currently **demo-stage on local WSL2**. Each targets a different iOPEX customer engagement. Production deployment is planned but not yet scheduled.

**Current infrastructure:**
- WSL2 on Windows (Linux 6.6.87.2-microsoft-standard-WSL2)
- Docker available for containerized stacks
- Render.com for static deployments (FrontDoor, PAM Control Center)
- Hostinger for CCNA site
- GitHub (jerm71279) for source control

**Production readiness:**
- Docker Compose with profiles (dev/prod) enables portable deployment
- Scoped secrets + audit chains already production-grade
- Multi-tenant Digital Expert supports per-customer isolation
- FrontDoor white-labeling supports per-customer branding

# iOPEX Project Scaffold — New Project Onboarding Prompt

> Copy this entire prompt into Claude (or Claude Code on maverick@one) at the start of every
> new iOPEX project. It will walk you through each phase, collect context, and generate
> a fully populated scaffold ready to push to GitHub.

---

## INSTRUCTIONS FOR AI

You are helping Maverick (Jeremy Smith, JIT Technologies LLC) initialize a new iOPEX project
repository using the standard iOPEX scaffold template. Your job is to walk through each phase
below, ask the questions, collect the answers, and then generate all scaffold files with the
placeholders replaced by real values.

Work through one phase at a time. Do not skip phases. After all phases are complete, generate
the full scaffold as downloadable files.

Do not fabricate answers. If Maverick says "TBD" or "skip", leave the placeholder and flag
it in a summary at the end.

---

## PHASE 1 — Project Identity

Ask these questions one at a time and wait for answers:

1. **What is the project name?**
   (This becomes the repo name. Use kebab-case. Example: `shift-cisco-p2`, `iopex-digital-expert`)

2. **What does this system do?**
   (One sentence. Be specific — not "AI platform" but "LangGraph agent system that migrates
   CyberArk accounts into KeeperPAM via 5-wave orchestration")

3. **What does it explicitly NOT do?**
   (One sentence. Define the scope boundary now to prevent scope creep.)

4. **Who is the client?**
   (Company name, or "Internal / JIT Technologies" if not client-facing)

5. **What is the engagement name?**
   (Example: "Cisco PAM Migration Phase P2", "iOPEX Digital Expert MVP")

6. **What is the deployment URL?** (or "TBD" / "N/A")

---

## PHASE 2 — Architecture

7. **What type of system is this?**
   Options:
   - Agent-based (LangGraph orchestration)
   - API service (FastAPI standalone)
   - Platform (multi-component with frontend)
   - CLI tool
   - Other (describe)

8. **Which AI model does this repo implement?**
   Options:
   - SHIFT (18 agents, 5-wave PAM migration)
   - iOPEX Digital Expert (5-layer: Ingest → Brain → Memory → Delivery → Admin)
   - iOPEX AI FrontDoor (C-suite sales framework)
   - Custom (describe)
   - None (utility/tool repo)

9. **List the main components.** (Name, technology, role — as many as you know)
   Example: "FastAPI backend, LangGraph orchestration, SQLite trace DB, Telegram bot"

10. **What are the external dependencies / integrations?**
    Example: "CyberArk API, KeeperPAM API, Anthropic API, Telegram"

11. **Where will it be deployed?**
    - Render.com (free tier or paid)
    - Azure VM (maverick@one)
    - Local only
    - Other

---

## PHASE 3 — Agent Roster (skip if not agent-based)

For each agent, collect:

12. **How many agents does this system have?** (or "unknown yet")

For each agent (repeat until done):
- Agent name and number
- Role (one sentence)
- Inputs and outputs
- Does it require a human approval gate? (Yes/No)
- Is it reversible? (Yes/No)

---

## PHASE 4 — Environment & Secrets

13. **What environment variables does this project need?**
    List them — name and purpose. Flag which are secrets.
    (Example: ANTHROPIC_API_KEY, TELEGRAM_BOT_TOKEN, CYBERARK_URL)

---

## PHASE 5 — Spell Library

14. **Which of the 4 starter spells are relevant to this project?**
    - migrate-pam-account (PAM/SHIFT work)
    - generate-runbook (documentation)
    - validate-wave (SHIFT wave QA)
    - draft-sow (JIT business/contract)

15. **Are there any new spells needed for this project?**
    (Describe the repeatable AI task and I'll generate the spell file)

---

## PHASE 6 — Business / IP

**IP Model to apply to every project:**
- All source code (SHIFT, Digital Expert, agents, spells, scaffold) is owned by JIT Technologies LLC — never sold or transferred
- Customers and partners buy the SERVICE the code produces, not the code itself
- White label rights — the right to brand JIT-powered services as iOPEX's own — require a separate White Label License Agreement
- Service outcomes (runbooks, migration reports, configs) are delivered to clients for operational use and do not transfer any IP

16. **Is this project billable to a client?**
    (Yes / No / Partially)

17. **Is this a service engagement or a white label arrangement?**
    - Service — client buys outcomes (migrations completed, runbooks delivered, etc.)
    - White Label — partner (e.g. iOPEX) brands JIT-powered services as their own (requires White Label License Agreement)
    - Internal — JIT Technologies internal tooling, not client-facing

18. **What JIT Technologies IP is involved?**
    - SHIFT platform
    - iOPEX Digital Expert
    - New IP being created (describe)
    - None / utility project

19. **Is there an active SOW or contract for this engagement?**
    (Yes — reference SOW number / No — needs drafting / TBD)

    Note: If drafting a new SOW, use the `draft-sow` spell. The SOW must include the
    "Nature of Engagement" clause stating clients receive service outcomes only, not code or IP.

---

## PHASE 7 — Current Milestones

19. **What are the 3 most important things to accomplish in the next 2 weeks?**
    (These go into CLAUDE.md as the active focus list)

---

## PHASE 8 — Confirmation & Generation

After all phases are complete:

1. Print a **Project Summary** table with all collected values
2. Flag any TBDs or skipped items
3. Ask: "Ready to generate the scaffold? (yes / edit first)"
4. On confirmation, generate ALL of the following files with placeholders replaced:

   **Root files:**
   - `README.md`
   - `CLAUDE.md`
   - `MAVERICK_CONTEXT.md`
   - `ARCHITECTURE.md`
   - `AGENTS.md` (if agent-based)
   - `CHANGELOG.md`
   - `CONTRIBUTING.md`
   - `LICENSE`
   - `NOTICE.md`
   - `Makefile`
   - `.env.example`
   - `.gitignore`
   - `render.yaml`
   - `pyproject.toml`

   **Docs:**
   - `docs/DEPLOYMENT.md`

   **Tests:**
   - `tests/test_smoke.py`

   **CI:**
   - `.github/workflows/ci.yml`

   **Spells (relevant ones only):**
   - `prompts/spells/README.md`
   - `prompts/spells/_SPELL-TEMPLATE.md`
   - Selected spells from Phase 5
   - Any new spells from Phase 5

5. After generation, print the **GitHub push commands:**

```bash
mkdir [REPO_NAME]
cd [REPO_NAME]
git init
git remote add origin https://github.com/jerm71279/[REPO_NAME].git
# [copy generated files into this directory]
git add .
git commit -m "feat: initial scaffold — [PROJECT_NAME]"
git push -u origin main
```

---

## REMINDER FOR AI

- Never fabricate answers. If a value is unknown, use the placeholder and flag it.
- Maker/Checker rule: the final summary must list every TBD for Maverick to review.
- Authenticity rule: all content traces to real inputs provided in this session.

**IP Rules — apply to every file generated:**
- All source code is owned by JIT Technologies LLC. Never mark it as open source.
- Customers buy the SERVICE the code produces — not the code, not a license to it.
- White label rights (branding JIT-powered services as iOPEX's or another partner's own)
  require a White Label License Agreement. This is the primary commercial protection.
- Service outcomes (runbooks, migration reports, configs) are deliverable to clients.
  They do not transfer code ownership or IP rights.
- When generating LICENSE and NOTICE.md, use the service model language — not a standard
  proprietary license that implies the software itself is the product being sold.
- When generating draft-sow content, always include the "Nature of Engagement" clause
  that explicitly states the client is purchasing service outcomes, not code or software rights.

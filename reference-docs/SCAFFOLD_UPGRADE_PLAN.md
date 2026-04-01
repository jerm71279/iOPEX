# iOPEX Scaffold Upgrade Plan: 2025 Discovery & Initialization

## Overview
This plan upgrades the `new-project.sh` script and the `project-templates/scaffold/` directory to ensure a rigid, repeatable, and risk-aware initialization process using 2025 prompt engineering techniques.

## Strategic Goals
1. **Repeatable Rigor:** Ensure every project identifies scope, issues, and concerns upfront.
2. **Logic-First Onboarding:** Use CoT to drive the discovery process.
3. **Risk-Aware Architecture:** Use Expert Panels and Failure-First analysis during scaffolding.

---

## Technical Upgrades

### 1. `new-project.sh` (Interactive Script)
- **CRISP-E Definition:** **C**ontext, **R**ole, **I**ntent, **S**cope, **P**ersona, **E**xamples.
- **Phase 1.5: Expert Panel Discovery:** Add an interactive step where the user/AI identifies 3 expert personas (e.g., Security, DevOps, Compliance) to provide "Thoughts, Concerns, and Issues" on the project name and description.
- **Phase 3.5: Failure-First Mapping:** When identifying agents or components, prompt for "What is the #1 way this component fails?" and store the answer in the scaffold.

### 2. `scaffold/SCAFFOLD-ONBOARDING-PROMPT.md` (AI Prompt)
- **CRISP-E Refactor:** Update the AI instructions to use the CRISP-E framework for generating the project's identity.
- **CoT Enforcement:** Force a `<thinking>` block before the AI asks the questions in each phase.
- **Expert Panel Logic:** Add a phase where the AI acts as a "Red Team" to challenge Maverick's project assumptions.

### 3. Template Updates (`project-templates/scaffold/`)
- **`CLAUDE.md`**: Add a mandatory **CRISP-E Persona** section.
- **`AGENTS.md`**: Add columns for **Failure Mode** and **Remediation Script**.
- **`ARCHITECTURE.md`**: Add an **Expert Panel Consensus** log to track why specific technical choices were made.
- **`MAVERICK_CONTEXT.md`**: Add an **Intent & Strategic Goal** section (the 'I' from CRISP-E).

---

## Action Items for Claude CLI

Claude, please perform an **AI Council Review** on this specific scaffold upgrade plan:

1. **Architecture Check:** Does adding an Expert Panel phase to a bash script (`new-project.sh`) add too much friction, or is it the right friction for a senior engineer?
2. **Logic Check:** Is CRISP-E the right framework for a project persona, or should we stick to RCCF?
3. **Security Check:** Does the Failure-First analysis in `AGENTS.md` provide actual security value or just documentation bloat?
4. **Integration Check:** How should we handle the "Red Team" review when Maverick is initializing a project via `new-project.sh apply` on an existing codebase?

## Collaboration Protocol
- **Gemini** will implement the `new-project.sh` bash logic and template updates.
- **Claude** will red-team the `SCAFFOLD-ONBOARDING-PROMPT.md` to ensure it drives deep discovery.

---
*Plan initiated by Gemini CLI on 2026-03-28.*

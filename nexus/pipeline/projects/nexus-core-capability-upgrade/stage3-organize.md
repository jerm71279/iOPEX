# Stage 3 — Organize: nexus-core-capability-upgrade
Date: 2026-04-05
Tool: Claude Desktop / Co-Work
Status: [ ] Draft  [x] Complete

---

## Context

Identified three Claude Code capabilities not yet used in the nexus-core stack.
Cross-referenced against the iOPEX infrastructure during a procedural review session.
Two of the three map directly to production nexus-core runners. One is a workflow pattern.

---

## Architecture Decisions

**Model switching — per-subcommand, not per-runner**
Both `pmo.py` and `nexus.py` currently use a single model constant for all subcommands.
The right granularity is per-subcommand: lightweight tasks get Haiku, production decisions get Opus.
Env var overrides stay in place — `NEXUS_PMO_MODEL` and `NEXUS_MODEL` become fallback defaults,
not the only control surface.

**Extended thinking — scoped to two methods only**
`_cmd_wave` and `_cmd_directive` are the only methods that make binary decisions with
multi-source inputs. All other subcommands are retrieval, summarisation, or Q&A — thinking
overhead is not justified there. Adding an `use_thinking` flag to `_anthropic_message`
keeps the change surgical without touching call sites that don't need it.

**Worktrees — workflow doc, not code**
Each iOPEX GitHub repo has branches. Worktrees let Claude Code run on multiple branches
of the same repo simultaneously without checkout conflicts. No code change needed —
one reference doc, reused per repo when needed.

---

## Build Order

1. **Model switching** — `pmo.py` first (more subcommands, higher stakes), then `nexus.py`
2. **Extended thinking** — builds on model switching (Opus already wired for wave/directive)
3. **Worktrees reference doc** — no code, write last

---

## Dependencies

| Dependency | Status | Notes |
|---|---|---|
| `anthropic` SDK ≥ 0.40 | Confirm | Extended thinking requires recent SDK version |
| Opus model access | Assumed active | Confirm `claude-opus-4-6` available on API key |
| nexus-core smoke tests | 28/28 passing | Run after changes to confirm no regression |

---

## Linked Artifacts

- Stage 1: (procedural review conversation — Claude Code CLI session, 2026-04-05)
- Stage 2: (cross-reference analysis — Claude Code CLI session, 2026-04-05)

---

## Handoff to Stage 4

### Context for Code Session

**Project:** nexus-core-capability-upgrade
**Repo:** `~/projects/nexus-core`
**Goal this session:** Implement model switching and extended thinking in nexus-core runners. Write worktrees reference doc.

---

**Files to modify:**

| File | Change |
|---|---|
| `src/nexus_core/runners/pmo.py` | Per-subcommand model dict + extended thinking on wave/directive |
| `src/nexus_core/runners/nexus.py` | Per-subcommand model dict |

**File to create:**

| File | Purpose |
|---|---|
| `nexus/pipeline/projects/nexus-core-capability-upgrade/worktrees-reference.md` | Worktrees usage pattern for iOPEX repos |

---

**Model switching — exact tier:**

| Subcommand | Model |
|---|---|
| `pmo directive` | `claude-opus-4-6` |
| `pmo wave` | `claude-opus-4-6` |
| `pmo escalate` | `claude-opus-4-6` |
| `pmo status` | `claude-sonnet-4-6` |
| `pmo ask` | `claude-sonnet-4-6` |
| `nexus brief` | `claude-sonnet-4-6` |
| `nexus ask` | `claude-sonnet-4-6` |
| `nexus recall` | `claude-haiku-4-5-20251001` |

---

**Extended thinking — implementation spec:**

Add optional `use_thinking: bool = False` parameter to `_anthropic_message` in `pmo.py`.

When `use_thinking=True`:
- Force model to `claude-opus-4-6` (thinking requires Opus)
- Add `thinking={"type": "enabled", "budget_tokens": 8000}` to `messages.create()`
- Set `max_tokens=16000` (must exceed budget_tokens)
- Extract text from response: filter `response.content` for blocks where `type == "text"`

Call sites:
- `_cmd_wave` → `use_thinking=True`
- `_cmd_directive` → `use_thinking=True`
- All others → default `False`

---

**Worktrees reference doc — content spec:**

Cover:
1. What worktrees are and when to use them (parallel branches, no checkout conflicts)
2. Setup command pattern (generic, repo-agnostic)
3. iOPEX repos with known active branches:
   - `~/projects/iOPEX` — `feature/jit-session-demo`, `feature/bt-autonomous-healing`, `refactor/repo-scaffold-system`
4. Claude Code usage: open separate `claude` session in each worktree directory
5. Cleanup: `git worktree remove <path>` when branch is merged

---

**Key constraints:**
- Do not change the `_anthropic_message` signature in `nexus.py` — it does not need thinking support
- Env var overrides (`NEXUS_PMO_MODEL`, `NEXUS_MODEL`) must still work — they become the per-subcommand fallback default, not a global override
- Do not add thinking to any nexus runner subcommand — nexus is session/memory ops, not decisions

**Do not:**
- Add extended thinking to `nexus.py`
- Change any runner other than `pmo.py` and `nexus.py`
- Modify tests — just run them after

**Definition of done:**
- `pmo.py` uses per-subcommand model with Opus for wave/directive/escalate
- `_cmd_wave` and `_cmd_directive` pass `thinking` parameter to Anthropic API
- `nexus.py` uses per-subcommand model with Haiku for recall
- `nexus-core` smoke tests: 28/28 passing
- Worktrees reference doc written to pipeline projects directory

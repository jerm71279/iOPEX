# Worktrees Reference — iOPEX

## What They Are

A git worktree lets you check out a second (or third) branch of the same repo into a
separate directory — without touching your current checkout. Both directories share the
same `.git` object store, so no duplication of history.

Use when you need to work on two branches of the same repo at the same time:
- Fix a production bug on `main` while continuing feature work on a branch
- Run a Claude Code session on a feature branch without losing context on main
- Compare two branches side-by-side

## When NOT to Use Them

- Across different repos — worktrees are per-repo, not cross-project
- For quick one-off lookups — just `git stash` and switch branches instead
- If the branch is already checked out in your primary worktree — git will refuse

## Setup Pattern

```bash
# From inside the repo root
git worktree add <path-for-new-worktree> <branch-name>

# Example — work on a feature branch alongside main:
git worktree add ../my-repo-feature feature/my-branch

# List active worktrees
git worktree list

# Remove when done (branch must be merged or no longer needed)
git worktree remove ../my-repo-feature
```

The new directory is a full working tree — you can run builds, tests, and Claude Code
sessions from it independently.

## iOPEX Repos with Active Branches

### ~/projects/iOPEX

| Branch | Purpose |
|---|---|
| `feature/jit-session-demo` | JIT session demo build |
| `feature/bt-autonomous-healing` | BT autonomous healing feature |
| `refactor/repo-scaffold-system` | Repo scaffold system refactor |

**Example — run feature/jit-session-demo alongside main:**
```bash
cd ~/projects/iOPEX
git worktree add ~/projects/iOPEX-jit-demo feature/jit-session-demo
```

Then open a Claude Code session in `~/projects/iOPEX-jit-demo` — it gets the
branch's own CLAUDE.md context and is fully isolated from main.

## Claude Code Usage

Each worktree directory is a first-class Claude Code workspace:

```bash
# Terminal 1 — main branch session
cd ~/projects/iOPEX
claude

# Terminal 2 — feature branch session (independent context)
cd ~/projects/iOPEX-jit-demo
claude
```

Both sessions run in parallel. Edits in one do not affect the other.
The CLAUDE.md hierarchy loads relative to each worktree root.

## Cleanup

```bash
# When the branch is merged and the worktree is no longer needed:
git worktree remove ~/projects/iOPEX-jit-demo

# Force remove if the directory has untracked files:
git worktree remove --force ~/projects/iOPEX-jit-demo

# Prune stale worktree references (e.g. after manually deleting the directory):
git worktree prune
```

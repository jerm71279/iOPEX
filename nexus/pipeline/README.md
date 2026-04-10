# Nexus Four-Stage Pipeline

Structured handoff system for the Chat → Chrome → Co-Work → Code workflow.

Each project gets four artifact files — one per stage. Handoffs are explicit markdown,
not mental context. Everything commits to GitHub.

## The Stages

| Stage | Tool | Goal | Artifact |
|-------|------|------|----------|
| 1 — Ideation | Claude Chat | Define the problem, make early decisions, scope research | `stage1-ideation.md` |
| 2 — Research | Claude Chrome | Answer the open questions from Stage 1 | `stage2-research.md` |
| 3 — Organize | Claude Desktop / Co-Work | Architecture, build order, dependencies + **AI Council Review gate** | `stage3-organize.md` |
| 4 — Build | Claude Code | Ship it | `stage4-build.md` |

> **AI Council Review** is a mandatory 6-panel gate at the end of Stage 3, before handoff to Stage 4.
> 3 domain SME panels (tailored per project) + 3 AI perspectives (Gemini = Strategic, Grok = Critical, Claude = Technical).
> Non-negotiable fixes must be resolved before Stage 4 begins.
> Reference: `iOPEX/reference-docs/AI_Council_Review_Scaffold_Upgrade.docx`

## Usage

### Start a new project

```bash
nexus-core run pipeline --subcommand new --project my-project
```

Creates `projects/my-project/` with all four stage templates pre-populated.

### Check stage status

```bash
nexus-core run pipeline --subcommand status --project my-project
```

### Advance to next stage

After completing a stage, run advance to create the next stage template
with the handoff section pre-populated from the previous stage:

```bash
nexus-core run pipeline --subcommand advance --project my-project
```

This auto-commits the completed stage to GitHub.

### Export project brief

Bundle all completed stages into a single `brief.md` for RAG ingestion
or sharing:

```bash
nexus-core run pipeline --subcommand export --project my-project
```

## Directory Structure

```
nexus/pipeline/
  README.md                  ← this file
  templates/
    stage1-ideation.md       ← blank template for Stage 1
    stage2-research.md       ← blank template for Stage 2
    stage3-organize.md       ← blank template for Stage 3
    stage4-build.md          ← blank template for Stage 4
  projects/
    {project-name}/
      stage1-ideation.md     ← filled in Stage 1
      stage2-research.md     ← filled in Stage 2
      stage3-organize.md     ← filled in Stage 3
      stage4-build.md        ← filled in Stage 4
      brief.md               ← exported bundle (after pipeline export)
```

## Friction Map

After running a project through all four stages manually for the first time,
document what was lost at each handoff, what took longest, and what would save
10+ minutes if automated:

`projects/friction-map.md` — raw findings that inform future template improvements.

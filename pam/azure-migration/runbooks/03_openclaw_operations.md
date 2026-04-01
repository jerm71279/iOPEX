# Runbook 03 — OpenClaw Operations
## CyberArk → KeeperPAM Migration | SHIFT System

**Scope:** How the delivery engineer uses the OpenClaw `shift-pmo` AI agent to operate
the SHIFT migration — triggering phases, monitoring progress, managing gates, and
generating stakeholder reports.
**Prerequisite:** DP-01 decision recorded as Option B. Azure deployment complete (Runbook 01).
Dashboard activated (Runbook 02). `az` CLI installed and authenticated on operator PC.
**Who runs this:** iOPEX delivery engineer (Jeremy Smith)

> **What OpenClaw is in this project:** The `shift-pmo` agent is the AI PMO layer that sits
> between the delivery engineer and the Azure migration backend. The engineer talks to it in
> plain language; it translates intent into `az containerapp exec` commands, runs them,
> reads the output, and reports back — acting as a single operator interface for the entire
> 15-agent SHIFT system.

---

## Architecture Recap

```
Delivery Engineer (PC)
  │
  │  plain language instructions
  ▼
OpenClaw shift-pmo agent
  │  reads: SOUL.md  USER.md  TOOLS.md
  │
  │  az containerapp exec --name <APP> --command "python3 cli.py ..."
  ▼
Azure Container App  (pam/azure-migration)
  │  runs: coordinator.py → 15 Python agents
  │  writes: output/state/  output/reports/  output/logs/
  │
  │  after each agent run:
  ▼
Azure Blob Storage  (dashboard status.json)
  │
  ▼
SHIFT Migration Control Center  (iOPEX team + Cisco stakeholders)
```

---

## Step 1 — Configure shift-pmo for This Project

Do this once at P0, immediately after Azure deployment.

**1a. Set Container App name and RG in TOOLS.md**

Open `/home/maverick/.openclaw/agents/shift-pmo/TOOLS.md` and replace the placeholders:

```
Resource Group : rg-pam-migration           ← confirm matches your RG
Container App  : <APP_NAME>                 ← from deploy.sh output
Dashboard URL  : https://<envName>dash...   ← from deploy.sh output
```

Get the values:
```bash
RG="rg-pam-migration"

APP_NAME=$(az deployment group show \
  --resource-group "$RG" --name main \
  --query properties.outputs.containerAppName.value --output tsv)

DASHBOARD_URL=$(az deployment group show \
  --resource-group "$RG" --name main \
  --query properties.outputs.dashboardUrl.value --output tsv)

echo "APP_NAME      : $APP_NAME"
echo "DASHBOARD_URL : $DASHBOARD_URL"
```

**1b. Verify az CLI access from the PC**

```bash
# Confirm az is authenticated and can reach the Container App
az containerapp show --name "$APP_NAME" --resource-group "$RG" \
  --query "{name:name, state:properties.runningStatus}" --output table
```

Expected: `Running`

**1c. Test OpenClaw can trigger the Container App**

Start an OpenClaw session and type:
```
Check migration status
```

OpenClaw should run:
```bash
az containerapp exec --name <APP_NAME> --resource-group rg-pam-migration \
  --command "python3 cli.py status"
```
And return the current migration state.

---

## Step 2 — Session Startup Protocol

Every OpenClaw session begins the same way. The `shift-pmo` agent automatically reads
its identity files (`SOUL.md`, `USER.md`, `TOOLS.md`) per the `AGENTS.md` startup protocol.

You do not need to brief it each session. It already knows:
- The project context (CyberArk → KeeperPAM, P0–P7, Cisco engagement)
- The team structure (IOPEX_DELIVERY, CLIENT_INFOSEC, KEEPERPAM_VENDOR, CLIENT_IT_OPS)
- The Azure execution commands (from TOOLS.md)
- The Yellow Checkpoint gate states
- Your communication preferences (Jeremy: brief summary first, then bullets)

**Opening a session:**
```
Start a new OpenClaw session with shift-pmo
```

OpenClaw will greet you and confirm current phase. If it doesn't know the current phase,
ask it to check:
```
Check migration status
```

---

## Step 3 — Running a Migration Phase

### Plain language → execution

You do not need to type `az` commands. Describe what you want:

| You say | OpenClaw does |
|---------|--------------|
| `Run P1` | `az containerapp exec ... "python3 cli.py run P1"` |
| `Run P5 dry run first` | `az containerapp exec ... "python3 cli.py run P5 --dry-run"` then awaits your go-ahead |
| `Run the heartbeat agent for P6` | `az containerapp exec ... "python3 cli.py agent 05-heartbeat --phase P6"` |
| `Run Wave 3 ETL` | `az containerapp exec ... "python3 cli.py agent 04-etl --phase P5"` (with wave config) |
| `Check status` | `az containerapp exec ... "python3 cli.py status"` |
| `Show me the ETL results` | Reads `output/reports/agent_04_etl_P5.json` from the container |

### Recommended pattern for every phase

1. **Dry run first** — always confirm scope before live execution:
   ```
   Run P{N} dry run
   ```

2. **Review output** — OpenClaw summarises what would run. Confirm:
   ```
   Looks good, run it live
   ```

3. **Monitor** — OpenClaw tails output as agents execute and summarises results.

4. **Review gate** — OpenClaw checks Yellow Checkpoint criteria when phase completes:
   ```
   Is P{N} ready to advance?
   ```

5. **Advance** — after gate sign-off:
   ```
   Advance to P{N+1}
   ```

---

## Step 4 — Yellow Checkpoint Gate Workflow

Each phase ends with a Yellow Checkpoint gate. OpenClaw manages the gate readiness
check and generates the sign-off summary.

**Check gate readiness:**
```
Is YC-P4 ready to pass?
```

OpenClaw will:
1. Read the heartbeat report from the Container App
2. Check all gate criteria against the output files
3. Report which items pass and which are open
4. Tell you what sign-offs are still needed

**Gate criteria by phase:**

| Gate | What OpenClaw checks |
|------|---------------------|
| YC-P1 | Discovery complete, NHI report reviewed, permission loss accepted |
| YC-P2 | All 10 staging assertions passed, no hard blocks |
| YC-P3 | Vaults created, permissions applied with 0 escalations |
| YC-P4 | Pilot ETL complete, heartbeat ≥ 95%, 0 failures |
| YC-P5 | All waves complete, integration repointing confirmed, compliance collected |
| YC-P6 | 100% fleet migrated, 100% heartbeat, 0 CyberArk patterns, cutover confirmed |
| YC-P7 | Audit archived, CyberArk decommissioned, KT complete, report signed |

**When all criteria are met:**
```
YC-P4 is clear. Advance to P5.
```

OpenClaw runs `python3 cli.py advance` and confirms the new phase.

**When criteria are not met:**
```
YC-P4 blocked — heartbeat 93%, below 95% threshold. Wave 1 has 3 stuck accounts.
```

OpenClaw identifies the blockers and suggests the fix path. Do not advance until resolved.

---

## Step 5 — Reviewing Agent Output

OpenClaw can read any report file from the Container App and summarise it.

**ETL results:**
```
Show me the Wave 2 ETL results
```

**Heartbeat pass rate:**
```
What was the heartbeat result for P5?
```

**Compliance evidence:**
```
What compliance controls have been evidenced so far?
```

**Full audit trail (last 20 entries):**
```
Show me the last 20 audit log entries
```

OpenClaw runs `az containerapp exec` to read the relevant JSON files and returns
a structured summary — you do not need to parse JSON manually.

---

## Step 6 — Generating Stakeholder Reports

OpenClaw generates PMO status reports on demand. These are ready to send to
Cisco stakeholders or paste into the change management ticket.

**Executive summary (for Cisco sponsor):**
```
Generate an executive status report for Cisco
```

Returns: current phase, % complete, gates passed, key risks, next milestone.
Concise, bottom-line-first — no technical detail.

**Technical status (for Cisco CISO / IT lead):**
```
Generate a technical status report for the Cisco security team
```

Returns: agent run results, heartbeat rates, compliance controls evidenced,
open gaps, stuck accounts if any.

**Weekly PMO directive:**
```
Generate this week's PMO directive
```

Returns: JSON PMO Directive Payload with action items per team, due dates,
gate dependencies.

**Gate sign-off document:**
```
Generate the YC-P4 sign-off summary
```

Returns: formatted gate criteria, pass/fail status, pending approvals, ready
for inclusion in the change management ticket.

> **Rule:** OpenClaw never fabricates gate status or agent outcomes.
> If data is missing from the output files, it says so — it does not fill gaps.

---

## Step 7 — Handling Failures

If an agent fails mid-phase, OpenClaw reports the failure and does not advance.

**Common failure responses:**

```
ETL failed on Wave 3 — what happened?
```

OpenClaw reads the error from `output/logs/audit.jsonl`, identifies the cause,
and recommends the fix from the runbook troubleshooting table.

```
Re-run just the ETL agent for P5
```

OpenClaw runs `python3 cli.py agent 04-etl --phase P5` — not the full phase,
just the failed agent.

```
Is the watchdog active?
```

OpenClaw checks whether Agent 04's watchdog timer is running (auto-unfreezes
vaults if the container times out). If a vault was left frozen due to failure,
OpenClaw can trigger the emergency unfreeze:

```
Emergency unfreeze all vaults
```

OpenClaw runs the coordinator's emergency unfreeze path and confirms.

---

## What OpenClaw Will Not Do

| Action | Why |
|--------|-----|
| Approve a Yellow Checkpoint gate unilaterally | Gates require human sign-off from named approvers |
| Run a phase without confirmation | Always confirms scope before live execution |
| Skip the dry-run recommendation | Always suggests dry run first for P4, P5, P6 |
| Fabricate results | If output files are missing, it reports missing — not assumed pass |
| Write to CyberArk or KeeperPAM directly | Read-only PMO role — only the Container App agents write |
| Push to git or modify runbooks | Outside the PMO scope — refer to iOPEX delivery engineer |

---

## Quick Reference — Common Instructions

| What you want | What to say to OpenClaw |
|---------------|------------------------|
| Start the project | `Start migration shift-20260401-001` |
| Dry run a phase | `Run P3 dry run` |
| Execute a phase | `Run P3 live` |
| Check status | `Check migration status` |
| Read a report | `Show me the P4 heartbeat results` |
| Check gate | `Is YC-P4 ready?` |
| Advance phase | `Advance to P5` |
| Executive report | `Generate executive status report` |
| Re-run one agent | `Re-run agent 05 heartbeat for P5` |
| Emergency unfreeze | `Emergency unfreeze — agent 04 failed` |
| Dashboard URL | `What is the dashboard URL for Cisco?` |
| This week's actions | `What needs to happen this week?` |

---

## Troubleshooting

| Issue | Cause | Fix |
|-------|-------|-----|
| OpenClaw doesn't know the Container App name | TOOLS.md not updated in P0 | Update `Resource Group` and `Container App` fields in TOOLS.md |
| `az containerapp exec` fails with auth error | `az login` expired | Run `az login` on the PC; re-open OpenClaw session |
| OpenClaw reports "output file missing" | Phase hasn't run yet | Normal — run the phase first |
| Gate check shows stale data | Dashboard blob not updated | Run `python3 cli.py status` to confirm; trigger manual export if needed |
| OpenClaw gives wrong phase | SOUL.md has old phase hardcoded | Update `CURRENT` line in SOUL.md to current phase |

---

## Next Step

→ **[P0_environment_setup.md](P0_environment_setup.md)** — Service accounts, config.json, network connectivity, preflight checks.

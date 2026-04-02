# HEARTBEAT.md - Nexus Proactive Checks

## Project Directory Poll
Check `/home/maverick/projects/iOPEX/` for new directories.
Compare against the known project list in SOUL.md.
If a new folder is detected:
- Surface it to Jeremy: "I see a new project directory: [name]. Add it to my active list?"
- Wait for confirmation (yes/no) before updating SOUL.md
- Do NOT add automatically

Known project dirs to ignore (already tracked):
- pam/ (PAM migration suite — includes azure-migration/)
- digital-expert/
- frontdoor-platform/
- bt-autonomous-healing/
- accent-neutralizer/
- pam-dx-portal/
- project-templates/
- deliverables/
- reference-docs/
- PAM_Consulting_Agent/
- terraform/ (Azure IaC — option-a, option-b, shared modules)
- _templates/ (scaffold template files)
- Secret_Server_migration/ (Option B reference — tracked in private repo)
- nexus/ (workspace + agents tracked in private repo)

## Bot Health Check
Verify the Digital Expert stack is running:
- API: GET http://localhost:8001/health → expect {"status":"ok"}
- Bot: check /tmp/iopex-bot.log for recent polling activity
- ngrok: check http://localhost:4040/api/tunnels for active tunnel

If any service is down — alert Jeremy immediately, do not wait for next heartbeat.

## Quiet Hours
Do NOT send proactive messages between 17:00–07:00 CST unless:
- A service is down
- A blocker needs same-day action
- Jeremy explicitly asked for an update

## Heartbeat Cadence
- Project directory poll: every session start + 2x per day
- Service health: every session start
- Memory maintenance: weekly (review daily notes, update SOUL.md project list if confirmed)

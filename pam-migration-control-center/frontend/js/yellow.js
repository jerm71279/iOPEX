/**
 * Yellow Checkpoints page — AI Orchestrator Cross-Phase Contextual Awareness.
 * Renders stats, phase accumulation, animated state machine, and checkpoint cards
 * with expandable 5-field AI rationale decision briefs.
 * Includes live demo: fires a new checkpoint with animated state machine flow.
 */

let yellowExpanded = {};
let stateMachineVisible = false;
let demoRunning = false;
let slaTimerInterval = null;

const YELLOW_TYPE_COLORS = {
  OPERATIONAL: { color: 'var(--cyan)', dim: 'var(--cyan-dim)', label: 'OPERATIONAL' },
  SECURITY: { color: 'var(--red)', dim: 'var(--red-dim)', label: 'SECURITY' },
  COMPLIANCE: { color: 'var(--purple)', dim: 'var(--purple-dim)', label: 'COMPLIANCE' },
  EDGE_CASE: { color: 'var(--green)', dim: 'var(--green-dim)', label: 'EDGE CASE' },
};

const YELLOW_STATUS_COLORS = {
  fired: 'badge-amber',
  notified: 'badge-amber',
  snoozed: 'badge-amber',
  resolved: 'badge-green',
  escalated: 'badge-red',
};

const SM_STATES = [
  { id: 'FIRE', label: 'Yellow Fires', color: 'var(--amber)',
    desc: 'Agent detects a condition that doesn\'t hard-stop the pipeline but cannot be silently ignored. Creates ServiceNow INC ticket. Logs to SIEM. Increments per-phase counter.' },
  { id: 'CLASSIFY', label: 'Classify Type', color: 'var(--blue)',
    desc: 'Agent classifies into: OPERATIONAL (24hr), SECURITY (2hr), COMPLIANCE (48hr), or EDGE CASE (24hr). Type determines routing, SLA, and escalation path.' },
  { id: 'NOTIFY', label: 'Notify + Window', color: 'var(--amber)',
    desc: 'Notification sent via configured channels (Slack/Teams, ServiceNow, SIEM, Email for SECURITY). Response window starts. Pipeline continues unless threshold hit.' },
  { id: 'COUNTER', label: 'Counter Check', color: 'var(--amber)',
    desc: 'Per-phase counter checked: 0-2 proceed, 3-4 notify IAM Lead, 5+ next yellow auto-promotes to RED.' },
  { id: 'WINDOW', label: 'Response Window', color: 'var(--blue)',
    desc: 'Human responds: Dismiss (\u2192 resolved), Escalate (\u2192 RED, pipeline halts), Snooze (one time, resets window), or Window expires (auto-escalate per profile).' },
  { id: 'BOUNDARY', label: 'Phase Boundary', color: 'var(--purple)',
    desc: 'At phase transitions: OPERATIONAL \u2192 carry forward. SECURITY/COMPLIANCE unresolved \u2192 auto-promote to RED, next phase blocked. EDGE CASE \u2192 carry forward as RED.' },
  { id: 'RESOLVED', label: 'Resolved', color: 'var(--green)',
    desc: 'Yellow closed. ServiceNow INC closed. SIEM event logged. Counter decremented. Evidence preserved in compliance report.' },
];

// ── Demo scenarios ──────────────────────────────────────────────────
const DEMO_SCENARIOS = [
  {
    phase: 'p3', agent: '03', type: 'SECURITY',
    condition: 'Agent 03 detected 5 accounts with ManageSafe permission being mapped to Owner role — escalation risk identified',
    ai_rationale: {
      what_fired: 'Agent 03 Permission Mapping found 5 accounts where ManageSafe permission in source maps to Owner role in target. These accounts currently have ManageSafe but NO data access permissions (UseAccounts, RetrieveAccounts). After migration, Owner role grants FULL access including credential retrieval.',
      root_cause: 'Secret Server Owner role bundles ManageSafe + ManageSafeMembers + all data permissions. The source permission model separates administrative permissions from data access. The mapping engine correctly assigns Owner (highest matching role) but this creates privilege escalation.',
      cross_system_context: 'Agent 02 (Gap Analysis) flagged this pattern in the gap report (G-03 Permission Granularity Loss). Agent 07 (Compliance) PCI-DSS Requirement 7.1 mandates least privilege. Agent 14 (Onboarding) uses the same role mapping — all future onboarding would inherit this escalation pattern.',
      risk_assessment: 'SECURITY — 5 accounts will gain credential retrieval access they did not have in source. This is a privilege escalation, not a data migration error. The compliance evidence package will flag this as a PCI-DSS finding.',
      recommended_action: 'Create a custom "Safe Admin" role in target with ManageSafe but without UseAccounts/RetrieveAccounts. Remap these 5 accounts to the custom role. Update Agent 03 mapping table to use custom role for ManageSafe-only accounts. Validate with Agent 07 before Wave 1.',
    },
  },
  {
    phase: 'p5', agent: '04', type: 'OPERATIONAL',
    condition: 'Wave 2 batch 3 — 12 accounts failed password retrieval from source during ETL export step',
    ai_rationale: {
      what_fired: 'Agent 04 ETL Pipeline during Wave 2, batch 3, failed to retrieve passwords for 12 accounts via POST /Accounts/{id}/Password/Retrieve. All 12 returned HTTP 403 "User is not authorized to perform this action".',
      root_cause: 'The migration service account (svc-pam-migration) has RetrieveAccounts permission on 140 of 142 safes. The 12 failing accounts are in 2 safes (DBA-Credentials-PROD and DBA-Credentials-DR) where the migration service account was never granted RetrieveAccounts. These safes were added to the vault 6 weeks after the migration service account was configured.',
      cross_system_context: 'Agent 01 (Discovery) inventory includes these safes. Agent 03 (Permission) mapped them correctly. Agent 10 (Staging) passed because staging used a different subset. The 12 accounts include 8 Oracle DBA accounts and 4 MSSQL SA accounts — all critical production credentials.',
      risk_assessment: 'OPERATIONAL — No data loss (accounts are not modified, just skipped). The wave can proceed for the remaining 486/498 accounts. The 12 accounts will be retried in Wave 5 (catch-all wave) after permission fix.',
      recommended_action: 'Grant RetrieveAccounts permission to svc-pam-migration on DBA-Credentials-PROD and DBA-Credentials-DR safes. Add a preflight permission check to Agent 04 that validates RetrieveAccounts on all target safes before starting export. Retry these 12 accounts in Wave 5.',
    },
  },
  {
    phase: 'p6', agent: '15', type: 'EDGE_CASE',
    condition: 'Parallel-run detected credential rotation conflict — source and target both rotated the same account within 30 seconds',
    ai_rationale: {
      what_fired: 'Agent 15 Hybrid Fleet Manager detected a rotation collision for account "svc-app-payments" in the Production-Linux safe. Source CPM rotated the password at 03:14:22 UTC and target rotated 28 seconds later at 03:14:50 UTC. The two systems now have different passwords for the same account.',
      root_cause: 'During parallel-run at 90% traffic shift, both source CPM and target rotation engine are active. The rotation schedules are offset by design (source at :00, target at :30 of each hour), but this account\'s rotation was triggered by a manual "Change Now" request in source, outside the scheduled window.',
      cross_system_context: 'Agent 05 (Heartbeat) will detect this mismatch on the next validation cycle (runs every 4 hours). Agent 04 (ETL) password sync runs hourly but the last sync completed 15 minutes before the collision. The payments application is currently routing to the target (90% traffic) and will use the target password — source password is stale for this account.',
      risk_assessment: 'EDGE_CASE — The payments application is functional (using target password). The risk is if a rollback is needed — the source password would not work. This is an expected risk during parallel-run but the manual trigger was unexpected.',
      recommended_action: 'Force immediate password sync from target to source for this account. Add a rotation lock policy: during parallel-run, manual "Change Now" requests on source should be blocked or auto-synced. Alert the payments team that a rollback for this account would require a password reset.',
    },
  },
];

// ── Option B (CyberArk Privilege Cloud) demo scenarios ──────────────
const DEMO_SCENARIOS_B = [
  {
    phase: 'p2', agent: '10', type: 'OPERATIONAL',
    condition: 'OAuth2 Identity platform access token expired mid-operation — Agent 10 staging validation interrupted at assertion 4 of 10',
    ai_rationale: {
      what_fired: 'Agent 10 Staging Validation received HTTP 401 Unauthorized from Privilege Cloud API during assertion 4 (credential retrieval verification). The OAuth2 bearer token issued by CyberArk Identity expired after 30 minutes. Assertions 1-3 completed successfully but took 31 minutes due to safe count.',
      root_cause: 'CyberArk Identity platform enforces a fixed 30-minute OAuth2 access token lifetime (client_credentials grant). Unlike on-prem PVWA session tokens which have an idle timeout and can be refreshed, Identity tokens simply expire with no refresh mechanism. The validation sequence takes 32-38 minutes for the current safe count, consistently exceeding the token lifetime.',
      cross_system_context: 'Agents 04, 05, 06, and 15 all authenticate through the same OAuth2 client (pam-migration-svc). Any operation exceeding 30 minutes will hit this wall. Agent 04 wave ETL runs 45-90 minutes per wave. Agent 15 parallel-run watchdog has a 120-minute timer. This is a systemic platform constraint affecting all long-running agent operations.',
      risk_assessment: 'OPERATIONAL — High risk to timeline if unaddressed. Every agent operation longer than 30 minutes will fail unpredictably. A token expiry during Agent 04 wave migration could leave accounts partially migrated, requiring manual intervention or Agent 06 rollback.',
      recommended_action: 'Implement a shared TokenLifecycleManager that proactively refreshes tokens at the 25-minute mark. Add assertion-level checkpointing to Agent 10 so validation can resume after token refresh. Distribute the lifecycle manager to all agents using the shared OAuth2 client. File a feature request with CyberArk for configurable token lifetime.',
    },
  },
  {
    phase: 'p1', agent: '11', type: 'SECURITY',
    condition: 'Privilege Cloud API version deprecation notice — REST API v1 endpoints scheduled for removal in 60 days, 3 agents using deprecated endpoints',
    ai_rationale: {
      what_fired: 'Agent 11 Source Adapter received deprecation warning headers (Sunset: 2025-08-15) on GET /api/v1/Safes responses from Privilege Cloud. CyberArk has announced REST API v1 endpoints will return HTTP 410 Gone after the sunset date. Agents 04, 10, and 11 are using v1 endpoints for safe enumeration, account listing, and credential retrieval.',
      root_cause: 'The migration agents were developed against Privilege Cloud REST API v1 documentation. CyberArk published v2 API specification 4 months ago with changes to pagination, response schemas, and authentication headers. The v1-to-v2 migration was not included in the original migration timeline because v1 deprecation was announced after project kickoff.',
      cross_system_context: 'Agent 04 ETL uses v1 for credential export (POST /api/v1/Accounts/{id}/Password/Retrieve), which moves to /api/v2/Credentials/{id}/retrieve with a different response format. Agent 10 uses v1 for safe membership validation. Agent 15 Hybrid Fleet Manager already uses v2 endpoints because it was developed later. The mixed v1/v2 usage means Agent 15 will continue working after sunset while Agents 04, 10, and 11 will break.',
      risk_assessment: 'SECURITY — Deprecated API endpoints receive no security patches. Running production migration workloads against unpatched endpoints creates a supply-chain risk. The 60-day window is tight given that Agent 04 ETL is the most complex consumer and requires response schema changes.',
      recommended_action: 'Create a v1-to-v2 migration task for Agents 04, 10, and 11. Start with Agent 11 (simplest consumer) as a pilot. Update response parsing for new pagination format and credential retrieval schema. Add API version header validation to agent preflight checks. Target completion 30 days before sunset to allow testing buffer.',
    },
  },
  {
    phase: 'p6', agent: '15', type: 'EDGE_CASE',
    condition: 'Privilege Cloud Connector server certificate expires in 14 days — parallel-run traffic will fail if not renewed',
    ai_rationale: {
      what_fired: 'Agent 15 Hybrid Fleet Manager health check detected that the Privilege Cloud Connector server\'s TLS certificate (CN=connector-prod.internal) expires on 2025-07-17. The Connector handles all credential retrieval traffic between the internal network and Privilege Cloud tenant. At current 90% traffic shift, 2,560 concurrent sessions route through this Connector.',
      root_cause: 'The Connector was deployed during Phase 2 (CHG0008891) with a 90-day self-signed certificate generated during installation. The certificate renewal was not added to the infrastructure team\'s certificate management system because the Connector is a new component not yet integrated into the automated renewal pipeline. The Connector does not support hot certificate replacement — it requires a service restart.',
      cross_system_context: 'Agent 04 ETL wave migrations, Agent 05 heartbeat checks, Agent 10 staging validation, and Agent 15 parallel-run traffic ALL route through this Connector. A certificate expiry would cause a total outage of all Privilege Cloud operations. Agent 06 rollback procedures also depend on the Connector — even reverting traffic to source requires Connector availability to re-sync credentials.',
      risk_assessment: 'EDGE_CASE — 14-day window is adequate for certificate renewal, but the service restart requirement means a maintenance window is needed. At 90% traffic shift, a Connector restart will cause a brief outage (estimated 2-3 minutes) affecting all concurrent credential retrievals. This must be coordinated with application teams to minimize impact.',
      recommended_action: 'Generate a new certificate with a 365-day validity period. Schedule the Connector restart during the 0200-0600 UTC maintenance window. Add the Connector certificate to the organization\'s certificate management system for automated renewal alerts. Consider deploying a second Connector for high availability — this eliminates the single-point-of-failure risk identified in yc-b03.',
    },
  },
];

async function renderYellowCheckpoints() {
  const [checkpoints, stats] = await Promise.all([
    API.get('/checkpoints'),
    API.get('/checkpoints/stats'),
  ]);

  // ── Stats row ──
  document.getElementById('yellowStats').innerHTML = `
    <div class="stat-card" style="border-top:2px solid var(--amber)">
      <div class="stat-label">Total Yellows</div>
      <div class="stat-value" style="color:var(--amber)">${stats.total}</div>
    </div>
    <div class="stat-card" style="border-top:2px solid var(--green)">
      <div class="stat-label">Resolved</div>
      <div class="stat-value" style="color:var(--green)">${stats.resolved}</div>
    </div>
    <div class="stat-card" style="border-top:2px solid var(--amber)">
      <div class="stat-label">Open</div>
      <div class="stat-value" style="color:${stats.open > 0 ? 'var(--amber)' : 'var(--text-muted)'}">${stats.open}</div>
    </div>
    <div class="stat-card" style="border-top:2px solid var(--red)">
      <div class="stat-label">Escalated to RED</div>
      <div class="stat-value" style="color:${stats.escalated > 0 ? 'var(--red)' : 'var(--text-muted)'}">${stats.escalated}</div>
    </div>
  `;

  // ── Phase accumulation bar ──
  renderAccumulation(stats.accumulation);

  // ── State machine (collapsed by default) ──
  renderStateMachine();

  // ── Checkpoint cards ──
  renderCheckpointCards(checkpoints);

  // ── Start SLA timers ──
  startSlaTimers(checkpoints);
}

function renderCheckpointCards(checkpoints) {
  document.getElementById('yellowCheckpoints').innerHTML = checkpoints.map((c, idx) => {
    const tc = YELLOW_TYPE_COLORS[c.type] || YELLOW_TYPE_COLORS.OPERATIONAL;
    const isOpen = yellowExpanded[c.id];
    const isActive = c.status === 'fired' || c.status === 'notified' || c.status === 'snoozed';
    const statusBadge = YELLOW_STATUS_COLORS[c.status] || 'badge-muted';
    const firedDate = new Date(c.fired_at).toLocaleString();
    const resolvedDate = c.resolved_at ? new Date(c.resolved_at).toLocaleString() : null;
    const sourceClass = c.source === 'ai_detected' ? 'source-ai' : 'source-procedural';
    const sourceLabel = c.source === 'ai_detected' ? 'AI DETECTED' : 'PROCEDURAL';
    const statusCardClass = c.status === 'escalated' ? 'status-escalated' : c.status === 'fired' ? 'status-fired' : '';

    return `
    <div class="yellow-card ${isOpen ? 'open' : ''} ${statusCardClass}" style="border-left-color:${tc.color};animation-delay:${idx * 0.05}s">
      <div class="yellow-card-header" onclick="toggleYellowCard('${c.id}')">
        <div style="display:flex;align-items:center;gap:10px;flex:1;min-width:0">
          <span style="font-size:1.1rem">${c.status === 'escalated' ? '&#x1F534;' : '&#x1F7E1;'}</span>
          <div style="min-width:0;flex:1">
            <div style="display:flex;gap:6px;flex-wrap:wrap;margin-bottom:4px;align-items:center">
              <span class="source-badge ${sourceClass}">${sourceLabel}</span>
              <span class="badge" style="background:${tc.dim};color:${tc.color};border:1px solid ${tc.color}33">${tc.label}</span>
              <span class="badge badge-muted">${c.phase.toUpperCase()}</span>
              <span class="badge badge-cyan">Agent ${c.agent.padStart(2, '0')}</span>
              <span class="badge ${statusBadge}">${c.status.toUpperCase()}</span>
              ${c.snow_ticket ? `<span class="badge" style="background:var(--blue-dim);color:var(--blue);border:1px solid var(--blue)33;font-size:0.55rem">${c.snow_ticket}</span>` : ''}
              ${isActive ? `<span class="sla-timer" id="sla-${c.id}" data-fired="${c.fired_at}" data-sla="${c.sla_hours}"></span>` : ''}
            </div>
            <div style="font-size:0.75rem;color:var(--text-bright);font-weight:600">${c.condition}</div>
            <div style="font-size:0.6rem;color:var(--text-muted);margin-top:2px">Fired: ${firedDate}${resolvedDate ? ' \u2014 Resolved: ' + resolvedDate : ''}</div>
          </div>
        </div>
        <span style="color:var(--text-muted);font-size:0.7rem;flex-shrink:0">${isOpen ? '&#x25B2;' : '&#x25BC;'}</span>
      </div>

      ${isOpen ? renderYellowCardBody(c, tc, isActive) : ''}
    </div>`;
  }).join('');
}

function renderYellowCardBody(c, tc, isActive) {
  const r = c.ai_rationale || {};
  const fields = [
    { num: '01', label: 'WHAT FIRED', key: 'what_fired', color: 'var(--amber)' },
    { num: '02', label: 'ROOT CAUSE HYPOTHESIS', key: 'root_cause', color: 'var(--blue)' },
    { num: '03', label: 'CROSS-SYSTEM CONTEXT', key: 'cross_system_context', color: 'var(--cyan)' },
    { num: '04', label: 'RISK ASSESSMENT', key: 'risk_assessment', color: 'var(--purple)' },
    { num: '05', label: 'RECOMMENDED ACTION', key: 'recommended_action', color: 'var(--green)' },
  ];

  return `
    <div class="yellow-card-body">
      <div class="ai-rationale-panel">
        <div style="color:${tc.color};font-size:0.6rem;font-family:var(--font-mono);font-weight:700;letter-spacing:1.5px;margin-bottom:10px">AI ORCHESTRATOR DECISION BRIEF</div>

        ${fields.map((f, i) => `
          <div class="ai-rationale-field" style="animation:fadeIn 0.3s ease ${i * 0.08}s both">
            <div class="ai-rationale-label" style="color:${f.color}">${f.num} \u2014 ${f.label}</div>
            <div class="ai-rationale-value">${r[f.key] || 'N/A'}</div>
          </div>
        `).join('')}
      </div>

      ${c.resolved_by ? `
        <div style="margin-top:14px;padding-top:12px;border-top:1px solid var(--border)">
          <div style="font-size:0.6rem;font-family:var(--font-mono);color:var(--text-muted);letter-spacing:1px;margin-bottom:6px">RESOLUTION</div>
          <div style="font-size:0.72rem;color:var(--text-standard);line-height:1.6">
            <strong style="color:var(--text-bright)">${c.resolved_by}</strong>: ${c.resolution_note || ''}
          </div>
        </div>
      ` : ''}

      ${c.status === 'escalated' ? `
        <div class="callout red" style="margin-top:12px">
          <div class="callout-title">Escalated to RED</div>
          <p>This yellow was promoted to a RED checkpoint. The pipeline is halted. ServiceNow ticket upgraded from INC to CHG. Gate approval required to proceed.</p>
        </div>
      ` : ''}

      ${isActive ? `
        <div style="margin-top:14px;display:flex;gap:8px;flex-wrap:wrap">
          <button class="btn btn-sm btn-teal" onclick="resolveYellow('${c.id}')">Resolve</button>
          <button class="btn btn-sm" style="background:var(--red-dim);color:var(--red);border:1px solid var(--red)33" onclick="escalateYellow('${c.id}')">Escalate to RED</button>
          ${c.status !== 'snoozed' ? `<button class="btn btn-sm" style="background:var(--amber-dim);color:var(--amber);border:1px solid var(--amber)33" onclick="snoozeYellow('${c.id}')">Snooze (${c.sla_hours}hr)</button>` : ''}
        </div>
      ` : ''}
    </div>`;
}

function renderAccumulation(accumulation) {
  const levelColors = {
    clear: { bg: 'var(--bg-surface)', border: 'var(--border)', text: 'var(--text-muted)' },
    proceed: { bg: 'var(--green-dim)', border: 'var(--green)', text: 'var(--green)' },
    notify_lead: { bg: 'var(--amber-dim)', border: 'var(--amber)', text: 'var(--amber)' },
    auto_promote_armed: { bg: 'var(--red-dim)', border: 'var(--red)', text: 'var(--red)' },
  };
  const levelLabels = {
    clear: 'CLEAR',
    proceed: 'PROCEED',
    notify_lead: 'NOTIFY LEAD',
    auto_promote_armed: 'AUTO-PROMOTE',
  };

  document.getElementById('yellowAccumulation').innerHTML = `
    <div style="padding:14px;display:flex;gap:8px;flex-wrap:wrap;justify-content:center">
      ${accumulation.map((a, i) => {
        const lc = levelColors[a.level] || levelColors.clear;
        const glow = a.count > 0 ? 'accum-glow' : '';
        return `
          <div class="accum-segment ${glow}" style="background:${lc.bg};border:1px solid ${lc.border}40;color:${lc.text};animation:fadeIn 0.4s ease ${i * 0.06}s both">
            <div style="font-family:var(--font-mono);font-size:0.55rem;color:var(--text-muted);letter-spacing:1px;margin-bottom:4px">${a.phase.toUpperCase()}</div>
            <div style="font-family:var(--font-mono);font-size:1.2rem;font-weight:800;color:${lc.text}">${a.count}</div>
            <div style="font-size:0.5rem;color:${lc.text};margin-top:2px;font-weight:700">${levelLabels[a.level]}</div>
          </div>`;
      }).join('')}
    </div>
    <div style="padding:0 14px 14px;display:flex;gap:14px;justify-content:center;flex-wrap:wrap">
      <span style="font-size:0.55rem;color:var(--green)">&#x25CF; 0-2 Proceed</span>
      <span style="font-size:0.55rem;color:var(--amber)">&#x25CF; 3-4 Notify Lead</span>
      <span style="font-size:0.55rem;color:var(--red)">&#x25CF; 5+ Auto-Promote Armed</span>
    </div>
  `;
}

function renderStateMachine() {
  document.getElementById('yellowStateMachine').innerHTML = `
    <div style="padding:14px;display:flex;flex-direction:column;align-items:center;gap:0">
      ${SM_STATES.map((s, i) => `
        ${i > 0 ? `<div class="sm-arrow" id="sm-arrow-${i}">&#x25BC;</div>` : ''}
        <div class="sm-node" id="sm-node-${s.id}" style="border-left-color:${s.color}">
          <div style="display:flex;align-items:center;gap:10px">
            <span class="badge" style="background:${s.color}22;color:${s.color};border:1px solid ${s.color}44;font-size:0.55rem">${s.id}</span>
            <span style="color:var(--text-bright);font-size:0.78rem;font-weight:700">${s.label}</span>
          </div>
          <div style="color:var(--text-standard);font-size:0.68rem;line-height:1.6;margin-top:6px">${s.desc}</div>
        </div>
      `).join('')}
    </div>
    <div style="text-align:center;padding-bottom:14px">
      <button class="demo-btn" id="demoBtn" onclick="runLiveDemo()" ${demoRunning ? 'disabled' : ''}>
        ${demoRunning ? 'DEMO RUNNING...' : '&#x26A1; RUN LIVE DEMO'}
      </button>
      <div style="font-size:0.55rem;color:var(--text-muted);margin-top:6px">Fires a new yellow checkpoint and animates the state machine flow</div>
    </div>
  `;
}

function toggleStateMachine() {
  stateMachineVisible = !stateMachineVisible;
  document.getElementById('yellowStateMachine').style.display = stateMachineVisible ? 'block' : 'none';
}

function toggleYellowCard(id) {
  yellowExpanded[id] = !yellowExpanded[id];
  renderYellowCheckpoints();
}

// ── SLA Timers ──────────────────────────────────────────────────────
function startSlaTimers(checkpoints) {
  if (slaTimerInterval) clearInterval(slaTimerInterval);
  slaTimerInterval = setInterval(() => updateSlaTimers(checkpoints), 1000);
  updateSlaTimers(checkpoints);
}

function updateSlaTimers(checkpoints) {
  checkpoints.forEach(c => {
    const el = document.getElementById(`sla-${c.id}`);
    if (!el) return;
    const isActive = c.status === 'fired' || c.status === 'notified' || c.status === 'snoozed';
    if (!isActive) return;

    const firedAt = new Date(c.fired_at).getTime();
    const slaMs = c.sla_hours * 60 * 60 * 1000;
    const deadline = firedAt + slaMs;
    const now = Date.now();
    const remaining = deadline - now;

    if (remaining <= 0) {
      el.className = 'sla-timer sla-critical';
      el.innerHTML = '&#x23F0; SLA EXPIRED';
    } else {
      const hrs = Math.floor(remaining / 3600000);
      const mins = Math.floor((remaining % 3600000) / 60000);
      const secs = Math.floor((remaining % 60000) / 1000);
      const pct = remaining / slaMs;
      const cls = pct > 0.5 ? 'sla-ok' : pct > 0.2 ? 'sla-warn' : 'sla-critical';
      el.className = `sla-timer ${cls}`;
      el.innerHTML = `&#x23F1; ${hrs}h ${mins}m ${secs}s`;
    }
  });
}

// ── Live Demo ───────────────────────────────────────────────────────
async function runLiveDemo() {
  if (demoRunning) return;
  demoRunning = true;

  // Show state machine if hidden
  if (!stateMachineVisible) {
    stateMachineVisible = true;
    document.getElementById('yellowStateMachine').style.display = 'block';
  }

  const btn = document.getElementById('demoBtn');
  if (btn) { btn.disabled = true; btn.innerHTML = 'DEMO RUNNING...'; }

  // Pick a random demo scenario based on selected option
  const scenarios = API.option === 'b' ? DEMO_SCENARIOS_B : DEMO_SCENARIOS;
  const scenario = scenarios[Math.floor(Math.random() * scenarios.length)];

  // Animate through state machine states
  for (let i = 0; i < SM_STATES.length; i++) {
    const state = SM_STATES[i];
    const node = document.getElementById(`sm-node-${state.id}`);
    if (!node) continue;

    // Light up current node
    node.classList.add('sm-active');
    node.style.color = state.color;
    node.scrollIntoView({ behavior: 'smooth', block: 'nearest' });

    // Wait for dramatic effect
    await sleep(800);

    // Mark as done
    node.classList.remove('sm-active');
    node.classList.add('sm-done');

    // Light up arrow
    if (i < SM_STATES.length - 1) {
      const arrow = document.getElementById(`sm-arrow-${i + 1}`);
      if (arrow) arrow.classList.add('sm-done');
    }

    await sleep(200);
  }

  // Fire the actual checkpoint via API with full AI rationale
  await API.post('/checkpoints/fire', {
    phase: scenario.phase,
    agent: scenario.agent,
    type: scenario.type,
    condition: scenario.condition,
    ai_rationale: scenario.ai_rationale,
    option: API.option || 'a',
  });

  // Brief pause then refresh
  await sleep(500);

  // Reset state machine visual
  SM_STATES.forEach(s => {
    const node = document.getElementById(`sm-node-${s.id}`);
    if (node) { node.classList.remove('sm-active', 'sm-done'); node.style.color = ''; }
  });
  for (let i = 1; i < SM_STATES.length; i++) {
    const arrow = document.getElementById(`sm-arrow-${i}`);
    if (arrow) arrow.classList.remove('sm-done');
  }

  demoRunning = false;

  // Re-render with new checkpoint — auto-expand it
  const newId = `yc-${(await API.get('/checkpoints')).length.toString().padStart(3, '0')}`;
  // Expand the newest checkpoint
  const all = await API.get('/checkpoints');
  if (all.length > 0) yellowExpanded[all[all.length - 1].id] = true;

  await renderYellowCheckpoints();
}

function sleep(ms) {
  return new Promise(resolve => setTimeout(resolve, ms));
}

// ── Actions ─────────────────────────────────────────────────────────
async function resolveYellow(id) {
  await API.post(`/checkpoints/${id}/resolve`);
  renderYellowCheckpoints();
}

async function escalateYellow(id) {
  await API.post(`/checkpoints/${id}/escalate`);
  renderYellowCheckpoints();
}

async function snoozeYellow(id) {
  await API.post(`/checkpoints/${id}/snooze`);
  renderYellowCheckpoints();
}

async function resetYellowCheckpoints() {
  yellowExpanded = {};
  await API.post('/checkpoints/reset');
  renderYellowCheckpoints();
}

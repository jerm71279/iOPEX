/**
 * Mission Control page renderer.
 */

async function renderMissionControl() {
  const [stats, risks, timeline, agents, gates, yellowStats, predictions] = await Promise.all([
    API.get('/dashboard/stats'),
    API.get('/dashboard/risks'),
    API.get('/dashboard/timeline'),
    API.get('/agents'),
    API.get('/gates'),
    API.get('/checkpoints/stats'),
    API.get('/dashboard/predictions'),
  ]);

  // Stats row
  document.getElementById('missionStats').innerHTML = `
    <div class="stat-card">
      <div class="stat-label">Total Accounts</div>
      <div class="stat-value">${stats.total_accounts.toLocaleString()}</div>
    </div>
    <div class="stat-card">
      <div class="stat-label">NHIs Detected</div>
      <div class="stat-value" style="color:var(--amber)">${stats.nhi_accounts}</div>
    </div>
    <div class="stat-card">
      <div class="stat-label">Integrations</div>
      <div class="stat-value">${stats.integrations}</div>
    </div>
    <div class="stat-card">
      <div class="stat-label">Migration Waves</div>
      <div class="stat-value">${stats.total_waves}</div>
    </div>
    <div class="stat-card">
      <div class="stat-label">Gates Passed</div>
      <div class="stat-value" style="color:var(--green)">${stats.gates_passed}/${stats.total_gates}</div>
    </div>
    <div class="stat-card">
      <div class="stat-label">Active Agents</div>
      <div class="stat-value" style="color:var(--cyan)">${stats.agents_active}</div>
    </div>
  `;

  // Current phase badge
  const cpb = document.getElementById('currentPhaseBadge');
  cpb.textContent = `${stats.current_phase.id.toUpperCase()} — ${stats.current_phase.name}`;

  // Phase timeline
  document.getElementById('phaseTimeline').innerHTML = timeline.map(p => {
    const statusClass = p.status === 'complete' ? 'past' : p.status === 'active' ? 'current' : 'future';
    const bg = p.status === 'complete' ? 'var(--green-dim)' : p.status === 'active' ? colorDimVar(p.color) : 'var(--bg-surface)';
    const fg = p.status === 'complete' ? 'var(--green)' : p.status === 'active' ? colorVar(p.color) : 'var(--text-muted)';
    return `<div class="phase-segment ${statusClass}" style="background:${bg};color:${fg};border-color:${fg}" onclick="jumpToPhase('${p.id}')">
      <div>${p.id.toUpperCase()}<br><span style="font-size:0.45rem;opacity:0.7">W${p.weeks}</span></div>
    </div>`;
  }).join('');

  // Active agents
  const agentCount = agents.filter(a => a.status === 'active').length;
  document.getElementById('activeAgentCount').textContent = `${agentCount} ACTIVE`;
  document.getElementById('agentStatusGrid').innerHTML = agents.map(a => `
    <div class="health-item" style="cursor:pointer" onclick="jumpToAgent('${a.id}')">
      <div class="health-dot ${statusDotClass(a.status)}"></div>
      <div>
        <div class="health-name">${a.num} ${a.name}</div>
        <div class="health-msg">${a.weeks} — ${a.status}</div>
      </div>
    </div>
  `).join('');

  // Risk dashboard
  const riskColors = { critical: 'red', high: 'amber', medium: 'blue', low: 'green' };
  document.getElementById('riskDashboard').innerHTML = Object.entries(risks).map(([level, r]) => `
    <div class="stat-card" style="border-top:2px solid var(--${riskColors[level]})">
      <div class="stat-label">${r.label}</div>
      <div class="stat-value" style="color:var(--${riskColors[level]})">${r.count}</div>
      <div style="font-size:0.65rem;color:var(--text-muted);margin-top:4px">${r.desc}</div>
    </div>
  `).join('');

  // Gate status
  const gatesPassed = gates.filter(g => g.status === 'passed').length;
  document.getElementById('gatePassCount').textContent = `${gatesPassed}/${gates.length} PASSED`;
  document.getElementById('gateStatusList').innerHTML = gates.map(g => `
    <div style="display:flex;align-items:center;gap:8px;padding:5px 8px;margin-bottom:3px;">
      <div class="health-dot ${statusDotClass(g.status)}"></div>
      <span style="font-size:0.72rem;color:var(--text-bright);flex:1">${g.name}</span>
      <span class="badge badge-muted">W${g.week}</span>
      <span class="badge ${g.status === 'passed' ? 'badge-green' : g.status === 'active' ? 'badge-amber' : 'badge-muted'}">${g.status.toUpperCase()}</span>
    </div>
  `).join('');

  // Yellow Checkpoints summary
  const ycPanel = document.getElementById('yellowStatusPanel');
  if (ycPanel) {
    const hasSecurity = yellowStats.by_type && yellowStats.by_type.SECURITY && yellowStats.open > 0;
    const hasCompliance = yellowStats.by_type && yellowStats.by_type.COMPLIANCE && yellowStats.open > 0;
    document.getElementById('yellowOpenCount').textContent = `${yellowStats.open} OPEN`;
    ycPanel.innerHTML = `
      <div style="display:flex;flex-wrap:wrap;gap:10px;padding:10px">
        <div style="display:flex;align-items:center;gap:8px;padding:8px 14px;background:var(--bg-surface);border:1px solid var(--border);border-radius:var(--radius);flex:1;min-width:100px;cursor:pointer" onclick="showPage('yellow',document.querySelectorAll('.nav-link')[5])">
          <div style="font-size:1.3rem">&#x1F7E1;</div>
          <div>
            <div style="font-size:0.78rem;font-weight:700;color:var(--amber)">${yellowStats.total} Total</div>
            <div style="font-size:0.6rem;color:var(--text-muted)">${yellowStats.resolved} resolved</div>
          </div>
        </div>
        <div style="display:flex;align-items:center;gap:8px;padding:8px 14px;background:var(--bg-surface);border:1px solid ${yellowStats.open > 0 ? 'var(--amber)' : 'var(--border)'};border-radius:var(--radius);flex:1;min-width:100px">
          <div class="health-dot ${yellowStats.open > 0 ? 'dot-amber' : 'dot-green'}"></div>
          <div>
            <div style="font-size:0.78rem;font-weight:700;color:${yellowStats.open > 0 ? 'var(--amber)' : 'var(--green)'}">${yellowStats.open} Open</div>
            <div style="font-size:0.6rem;color:var(--text-muted)">${yellowStats.open > 0 ? 'Requires attention' : 'All clear'}</div>
          </div>
        </div>
        <div style="display:flex;align-items:center;gap:8px;padding:8px 14px;background:var(--bg-surface);border:1px solid ${yellowStats.escalated > 0 ? 'var(--red)' : 'var(--border)'};border-radius:var(--radius);flex:1;min-width:100px">
          <div class="health-dot ${yellowStats.escalated > 0 ? 'dot-red' : 'dot-green'}"></div>
          <div>
            <div style="font-size:0.78rem;font-weight:700;color:${yellowStats.escalated > 0 ? 'var(--red)' : 'var(--green)'}">${yellowStats.escalated} Escalated</div>
            <div style="font-size:0.6rem;color:var(--text-muted)">${yellowStats.escalated > 0 ? 'RED — pipeline halted' : 'No escalations'}</div>
          </div>
        </div>
      </div>
    `;
  }

  // ML Model Status
  renderMLStatus();

  // Predictive Insights
  renderPredictions(predictions);

  // Circuit Breaker Status
  renderCircuitBreaker();

  // Schema Drift Monitor
  renderSchemaDrift();

  // Mission Control blurb (appended after all panels)
  const blurbTarget = document.getElementById('page-mission');
  if (blurbTarget && !document.getElementById('missionBlurb')) {
    const blurb = document.createElement('div');
    blurb.id = 'missionBlurb';
    blurb.innerHTML = _renderMissionBlurb();
    blurbTarget.appendChild(blurb);
  }
}

// ── Predictive Intelligence Flow ────────────────────────────────────
let _pfAnimating = false;
let _pfAutoPlay = false;
let _pfDecisionResolve = null;
let _pfSpeed = 1; // 0.25 = slow, 1 = normal, 3 = fast

const PF_AGENTS = [
  { num: '11', name: 'Src', phase: 'p1', purpose: 'Extracts raw data from source PAM' },
  { num: '01', name: 'Disc', phase: 'p1', purpose: 'Scans full CyberArk environment' },
  { num: '09', name: 'Dep', phase: 'p1', purpose: 'Maps application→account dependencies' },
  { num: '12', name: 'NHI', phase: 'p1', purpose: 'Classifies non-human identities' },
  { num: '02', name: 'Gap', phase: 'p1', purpose: 'Assesses 10-domain maturity gaps' },
  { num: '13', name: 'Plat', phase: 'p2', purpose: 'Validates target platform coverage' },
  { num: '10', name: 'Stag', phase: 'p2', purpose: '10-assertion staging validation' },
  { num: '03', name: 'Perm', phase: 'p3', purpose: 'Maps 22 CyberArk permissions to target' },
  { num: '14', name: 'Onbd', phase: 'p3', purpose: '10-step app onboarding pipeline' },
  { num: '04', name: 'ETL', phase: 'p45', purpose: '7-step ETL with crash recovery' },
  { num: '05', name: 'Hrtb', phase: 'p45', purpose: '10-check post-migration validation' },
  { num: '18', name: 'Intgr', phase: 'p45', purpose: '12-check independent integrity re-validation (Agent 18)' },
  { num: '06', name: 'Intg', phase: 'p67', purpose: 'CCP/AAM integration repointing' },
  { num: '07', name: 'Comp', phase: 'p67', purpose: 'PCI-DSS, NIST, HIPAA, SOX evidence' },
  { num: '15', name: 'Hybr', phase: 'p67', purpose: 'Parallel-run traffic shift manager' },
  { num: '08', name: 'Rnbk', phase: 'p67', purpose: 'Phase gate management + decommission' },
];

const PF_PHASE_GROUPS = [
  { key: 'p1', label: 'P1 DISCOVERY' },
  { key: 'p2', label: 'P2 STAGING' },
  { key: 'p3', label: 'P3 STRUCTURE' },
  { key: 'p45', label: 'P4-P5 ETL' },
  { key: 'p67', label: 'P6-P7 OPS' },
];

function _getPredictiveExamples() {
  return [
    {
      id: 1, label: 'Permission Escalation', severity: 'high', category: 'security',
      condition: '47 accounts with ManageSafe-only permissions are being mapped to Owner role — a privilege escalation from read-only safe admin to full data access',
      sourceAgents: ['03'],
      checkpoints: [{ id: 'yc-a02', label: '47 ManageSafe→Owner escalations', phase: 'P1' }],
      crossRefs: [{ from: 'yc-a02', to: '14', reason: 'Onboarding Factory uses same mapping table' }],
      prediction: { id: 'pred-a01', severity: 'HIGH', title: 'Permission escalation compounding via Onboarding Factory' },
      impactPhases: ['P3', 'P4', 'P5'],
      impactAgents: ['03', '14'],
      impactText: '60+ accounts over-provisioned by P5 end',
      recommendation: 'Update Agent 14 mapping table + apply compensating control',
      feedbackAgent: '14',
      decisions: {
        d1: { q: 'Threshold exceeded?',
          yesText: '47 escalations found — exceeds 10-escalation threshold, so a yellow checkpoint fires',
          noText: 'Escalation count is below threshold — logged as informational, no checkpoint fires' },
        d2: { q: 'Cross-system impact?',
          yesText: 'Agent 14 (Onboarding Factory) uses the same permission mapping table — new accounts will inherit the escalation',
          noText: 'Escalation is isolated to Agent 03 — no other agents reference this mapping, logged as advisory' },
        d3: { q: 'Compounding risk?',
          yesText: 'Every new account onboarded in P4-P5 will inherit Owner instead of View — escalation grows with each wave',
          noText: 'Existing escalation does not propagate — checkpoint resolves with a one-time fix' },
        d4: { q: 'Remediate or accept risk?',
          yesText: 'Fix the mapping table now — Agent 14 re-runs onboarding pipeline with corrected permissions',
          noText: 'Accept the risk — escalated accounts are documented but not corrected; prediction stays active' },
      },
    },
    {
      id: 2, label: 'Wave 3 NHI Overrun', severity: 'critical', category: 'bottleneck',
      condition: 'Source extraction latency measured at 182 seconds per account — 52% above the 120-second benchmark, with 554 NHI accounts queued for Wave 3',
      sourceAgents: ['11', '01'],
      checkpoints: [{ id: 'yc-a01', label: 'Extraction latency 182s vs 120s benchmark', phase: 'P1' }],
      crossRefs: [
        { from: 'yc-a01', to: '09', reason: '3 accounts used by IIS app pools' },
        { from: 'yc-a01', to: '12', reason: 'NHI Handler confirms human accounts w/ app bindings' },
        { from: 'yc-a01', to: '10', reason: 'Staging env uses same PVWA — extraction at risk' },
      ],
      prediction: { id: 'pred-a02', severity: 'CRITICAL', title: 'Wave 3 NHI volume exceeds maintenance window' },
      impactPhases: ['P5'],
      impactAgents: ['04', '11', '12'],
      impactText: 'Wave 3 overruns 12-hour maintenance window by 2+ hours',
      recommendation: 'Pre-split Wave 3 into sub-waves (3a: 280, 3b: 274 NHIs)',
      feedbackAgent: '04',
      decisions: {
        d1: { q: 'Threshold exceeded?',
          yesText: '182s per account exceeds the 120s benchmark — checkpoint fires flagging extraction bottleneck',
          noText: 'Latency is within acceptable benchmark — no performance concern, no checkpoint fires' },
        d2: { q: 'Cross-system impact?',
          yesText: '3 downstream agents depend on this data — Agent 09 (dependency maps), Agent 12 (NHI classification), Agent 10 (staging) are all affected',
          noText: 'No other agents depend on extraction timing — latency is a local concern only' },
        d3: { q: 'Compounding risk?',
          yesText: '554 NHIs at 182s each = 28 hours extraction — Wave 3 will overrun the 12-hour maintenance window by 2+ hours',
          noText: 'Volume is small enough that the latency does not breach the maintenance window — checkpoint resolved' },
        d4: { q: 'Remediate or accept risk?',
          yesText: 'Split Wave 3 into two sub-waves (3a: 280, 3b: 274) — Agent 04 re-plans ETL scheduling to fit within window',
          noText: 'Accept the overrun risk — maintain single Wave 3 and request an extended maintenance window' },
      },
    },
    {
      id: 3, label: 'Rate Limit Escalation', severity: 'critical', category: 'capacity',
      condition: 'API call failure rate of 18% at 100 req/min during P1 discovery, and 16% failure at 500 req/min during P6 parallel-run — two independent signals from different phases',
      sourceAgents: ['11', '15'],
      checkpoints: [
        { id: 'yc-b01', label: '18% failure at 100 req/min', phase: 'P1' },
        { id: 'yc-b04', label: '16% failure at 500 req/min', phase: 'P6' },
      ],
      crossRefs: [
        { from: 'yc-b01', to: '04', reason: 'Rate limiter set to 100/min — inadequate for parallel load' },
        { from: 'yc-b04', to: '05', reason: 'Heartbeat checks unaffected (04:00 UTC) but daytime at risk' },
      ],
      prediction: { id: 'pred-b01', severity: 'CRITICAL', title: 'API rate limit escalation curve threatens cutover' },
      impactPhases: ['P6', 'P7'],
      impactAgents: ['04', '05', '11', '15'],
      impactText: '10% headroom at 500 req/min — any burst triggers cascading 429 errors',
      recommendation: 'Request 1,000 req/min tier + implement request coalescing',
      feedbackAgent: '15',
      decisions: {
        d1: { q: 'Threshold exceeded?',
          yesText: '18% failure rate exceeds 5% threshold — TWO checkpoints fire, one in P1 and one in P6, flagging a cross-phase pattern',
          noText: 'Failure rate is within acceptable range — API errors are transient and do not warrant a checkpoint' },
        d2: { q: 'Cross-system impact?',
          yesText: 'Agent 04 (ETL rate limiter) and Agent 05 (heartbeat timing) are both constrained by the same API ceiling',
          noText: 'Rate limits only affect the source adapter — no downstream agents are impacted' },
        d3: { q: 'Compounding risk?',
          yesText: 'P1 rate (18%) + P6 rate (16%) project to P7: only 10% headroom at 500 req/min ceiling — any traffic burst causes cascading 429 errors',
          noText: 'Failure rates are stable and not trending upward — no escalation curve detected' },
        d4: { q: 'Remediate or accept risk?',
          yesText: 'Request 1,000 req/min tier upgrade + implement request coalescing — Agent 15 re-validates capacity',
          noText: 'Accept 10% headroom — monitor rate limits and trigger manual escalation if 429 errors spike' },
      },
    },
  ];
}

function _renderPredictiveFlow() {
  const examples = _getPredictiveExamples();

  // Build agent ecosystem HTML
  let agentHtml = '';
  PF_PHASE_GROUPS.forEach(g => {
    const agents = PF_AGENTS.filter(a => a.phase === g.key);
    agentHtml += `<div class="pf-agent-group">
      <div class="pf-agent-group-label">${g.label}</div>
      <div style="display:flex;gap:4px;flex-wrap:wrap;justify-content:center;">
        ${agents.map(a => `<div class="pf-node" id="pf-agent-${a.num}">
          <div class="pf-tooltip">${a.purpose}</div>
          <div style="font-weight:700;font-size:0.6rem;">${a.num}</div>
          <div style="font-size:0.42rem;color:inherit;">${a.name}</div>
        </div>`).join('')}
      </div>
    </div>`;
  });

  return `
    <div class="callout callout-teal" style="margin-top:16px;font-size:0.68rem;line-height:1.6;">
      <div style="font-weight:700;margin-bottom:6px;">Predictive Intelligence — How 15 Agents Drive Forecasting</div>
      <p style="margin:0;">The prediction engine emerges from interactions between all 15 agents. When an agent detects an ambiguous condition, it fires a yellow checkpoint whose <code style="font-family:var(--font-mono);color:var(--teal);">cross_system_context</code> cross-references other agents' data. The prediction engine correlates these signals to identify compounding risks. Each prediction drives agent re-execution in a continuous feedback loop. Select an example below to trace a real prediction through the ecosystem.</p>
    </div>
    <div class="pf-container">
      <div class="pf-header">
        <div class="pf-header-title">Predictive Intelligence Flow</div>
        <div class="pf-controls">
          ${examples.map((e, i) => `<button class="pf-example-btn ${i === 0 ? 'active' : ''}" id="pf-ex-${e.id}" onclick="selectPredictiveExample(${e.id})">${e.label}</button>`).join('')}
          <button class="demo-btn" id="pfReplayBtn" onclick="replayPredictiveDemo()" style="font-size:0.5rem;padding:3px 8px;">&#x25B6; REPLAY</button>
          <button class="pf-autoplay ${_pfAutoPlay ? 'active' : ''}" onclick="togglePfAutoPlay()">Auto &#x25B6;</button>
          <button class="pf-autoplay" id="pfPauseBtn" onclick="togglePfPause()">&#x23F8; PAUSE</button>
          <div class="pf-speed-control">
            <span class="pf-speed-label" id="pfSpeedLabel">1x</span>
            <input type="range" class="pf-speed-dial" id="pfSpeedDial" min="0.25" max="3" step="0.25" value="1" oninput="setPfSpeed(this.value)">
          </div>
        </div>
      </div>

      <!-- Layer 1: Agent Ecosystem -->
      <div class="pf-layer">
        <div class="pf-layer-label">Layer 1 — Agent Ecosystem</div>
        <div class="pf-agents">${agentHtml}</div>
      </div>

      <!-- Layer 2: Yellow Checkpoint Bus -->
      <div class="pf-layer">
        <div class="pf-layer-label">Layer 2 — Yellow Checkpoint Bus</div>
        <div class="pf-bus" id="pfCheckpointBus"></div>
        <div class="pf-caption" id="pfCaption1"></div>
      </div>

      <!-- Layer 3: Decision Engine -->
      <div class="pf-layer">
        <div class="pf-layer-label">Layer 3 — Decision Engine + Prediction</div>
        <div style="display:flex;align-items:center;justify-content:center;gap:12px;flex-wrap:wrap;min-height:60px;" id="pfDecisionEngine"></div>
        <div class="pf-caption" id="pfCaption2"></div>
      </div>

      <!-- Layer 4: Impact + Feedback -->
      <div class="pf-layer">
        <div class="pf-layer-label">Layer 4 — Impact Projection + Feedback Loop</div>
        <div style="text-align:center;min-height:40px;" id="pfImpactZone"></div>
        <div class="pf-caption" id="pfCaption3"></div>
        <div class="pf-feedback" id="pfFeedback"></div>
      </div>
    </div>`;
}

function selectPredictiveExample(num) {
  document.querySelectorAll('.pf-example-btn').forEach(b => b.classList.remove('active'));
  const btn = document.getElementById(`pf-ex-${num}`);
  if (btn) btn.classList.add('active');
  resetPredictiveFlow();
  playPredictiveDemo(num);
}

function replayPredictiveDemo() {
  const activeBtn = document.querySelector('.pf-example-btn.active');
  const num = activeBtn ? parseInt(activeBtn.id.replace('pf-ex-', '')) : 1;
  resetPredictiveFlow();
  playPredictiveDemo(num);
}

function togglePfAutoPlay() {
  _pfAutoPlay = !_pfAutoPlay;
  document.querySelector('.pf-autoplay').classList.toggle('active', _pfAutoPlay);
}

function setPfSpeed(val) {
  _pfSpeed = parseFloat(val);
  const label = document.getElementById('pfSpeedLabel');
  if (label) label.textContent = _pfSpeed < 1 ? `${_pfSpeed}x` : `${_pfSpeed}x`;
}

function resetPredictiveFlow() {
  if (_pfDecisionResolve) { _pfDecisionResolve('cancel'); _pfDecisionResolve = null; }
  _pfAnimating = false;
  _pfPaused = false;
  if (_pfPauseResolve) { _pfPauseResolve(); _pfPauseResolve = null; }
  const pauseBtn = document.getElementById('pfPauseBtn');
  if (pauseBtn) { pauseBtn.textContent = '\u23F8 PAUSE'; pauseBtn.classList.remove('active'); }
  PF_AGENTS.forEach(a => {
    const el = document.getElementById(`pf-agent-${a.num}`);
    if (el) el.className = 'pf-node';
  });
  ['pfCheckpointBus', 'pfDecisionEngine', 'pfImpactZone', 'pfFeedback'].forEach(id => {
    const el = document.getElementById(id);
    if (el) el.innerHTML = '';
  });
  ['pfCaption1', 'pfCaption2', 'pfCaption3'].forEach(id => {
    const el = document.getElementById(id);
    if (el) { el.textContent = ''; el.classList.remove('pf-visible'); }
  });
}

function _pfSleep(ms) {
  if (_pfPaused) return new Promise(r => { _pfPauseResolve = r; });
  return new Promise(r => setTimeout(r, ms / _pfSpeed));
}

let _pfPaused = false;
let _pfPauseResolve = null;

function togglePfPause() {
  _pfPaused = !_pfPaused;
  const btn = document.getElementById('pfPauseBtn');
  if (btn) {
    btn.textContent = _pfPaused ? '\u25B6 PLAY' : '\u23F8 PAUSE';
    btn.classList.toggle('active', _pfPaused);
  }
  if (!_pfPaused && _pfPauseResolve) {
    const r = _pfPauseResolve;
    _pfPauseResolve = null;
    r();
  }
}

function _pfSetCaption(id, text) {
  const el = document.getElementById(id);
  if (!el) return;
  el.textContent = text;
  el.classList.add('pf-visible');
}

function _pfClearCaption(id) {
  const el = document.getElementById(id);
  if (!el) return;
  el.classList.remove('pf-visible');
  setTimeout(() => { if (el) el.textContent = ''; }, 400);
}

function _pfAwaitDecision(decisionId, question) {
  return new Promise(resolve => {
    if (_pfAutoPlay) {
      setTimeout(() => resolve('yes'), 1500 / _pfSpeed);
      return;
    }
    _pfDecisionResolve = resolve;
    const yesBtn = document.getElementById(`pf-d-yes-${decisionId}`);
    const noBtn = document.getElementById(`pf-d-no-${decisionId}`);
    const waitEl = document.getElementById(`pf-d-wait-${decisionId}`);
    if (yesBtn) { yesBtn.classList.add('pf-visible'); yesBtn.onclick = () => { _pfDecisionResolve = null; resolve('yes'); }; }
    if (noBtn) { noBtn.classList.add('pf-visible'); noBtn.onclick = () => { _pfDecisionResolve = null; resolve('no'); }; }
    const yesDesc = document.getElementById(`pf-d-yesdesc-${decisionId}`);
    const noDesc = document.getElementById(`pf-d-nodesc-${decisionId}`);
    if (yesDesc) yesDesc.style.opacity = '1';
    if (noDesc) noDesc.style.opacity = '1';
    if (waitEl) waitEl.style.display = 'block';
  });
}

function _pfBuildDecision(id, decision) {
  return `<div class="pf-decision-wrap">
    <div class="pf-decision" id="pf-diamond-${id}"><div class="pf-decision-label">?</div></div>
    <div style="font-size:0.5rem;color:var(--text-muted);font-family:var(--font-mono);margin-top:2px;">${decision.q}</div>
    <div class="pf-decide-btns">
      <div style="display:flex;flex-direction:column;align-items:center;gap:2px;">
        <button class="pf-decide-btn pf-yes-btn" id="pf-d-yes-${id}">YES</button>
        <div style="font-size:0.42rem;color:var(--green);max-width:140px;text-align:center;line-height:1.3;opacity:0;" id="pf-d-yesdesc-${id}">${decision.yesText}</div>
      </div>
      <div style="display:flex;flex-direction:column;align-items:center;gap:2px;">
        <button class="pf-decide-btn pf-no-btn" id="pf-d-no-${id}">NO</button>
        <div style="font-size:0.42rem;color:var(--text-muted);max-width:140px;text-align:center;line-height:1.3;opacity:0;" id="pf-d-nodesc-${id}">${decision.noText}</div>
      </div>
    </div>
    <div class="pf-waiting" id="pf-d-wait-${id}" style="display:none;">awaiting decision...</div>
  </div>`;
}

async function playPredictiveDemo(exampleNum) {
  if (_pfAnimating) return;
  _pfAnimating = true;

  const examples = _getPredictiveExamples();
  const ex = examples.find(e => e.id === exampleNum) || examples[0];

  // Step 1: Highlight involved agents
  ex.sourceAgents.forEach(num => {
    const el = document.getElementById(`pf-agent-${num}`);
    if (el) el.style.borderColor = 'var(--cyan)';
  });
  const allInvolved = [...new Set([...ex.sourceAgents, ...ex.impactAgents, ...ex.crossRefs.map(r => r.to)])];
  allInvolved.forEach(num => {
    const el = document.getElementById(`pf-agent-${num}`);
    if (el) el.style.borderColor = 'var(--border-light)';
  });
  await _pfSleep(800);

  // Step 2: Source agents pulse
  for (const num of ex.sourceAgents) {
    const el = document.getElementById(`pf-agent-${num}`);
    if (el) el.classList.add('pf-active');
  }
  _pfSetCaption('pfCaption1', `Agent ${ex.sourceAgents.join(' + Agent ')} detects: ${ex.condition}`);
  await _pfSleep(1500);

  // Step 3: Decision 1 — Threshold
  const bus = document.getElementById('pfCheckpointBus');
  const engine = document.getElementById('pfDecisionEngine');
  engine.innerHTML = _pfBuildDecision('d1', ex.decisions.d1);
  const d1Diamond = document.getElementById('pf-diamond-d1');
  if (d1Diamond) d1Diamond.classList.add('pf-active-amber');

  const d1Result = await _pfAwaitDecision('d1', ex.decisions.d1.q);
  if (d1Result === 'cancel') return;

  // Mark decision
  if (d1Diamond) { d1Diamond.classList.remove('pf-active-amber'); d1Diamond.classList.add(d1Result === 'yes' ? 'pf-done' : 'pf-done-no'); }
  document.getElementById('pf-d-yes-d1')?.classList.add(d1Result === 'yes' ? 'pf-chosen' : 'pf-unchosen');
  document.getElementById('pf-d-no-d1')?.classList.add(d1Result === 'no' ? 'pf-chosen' : 'pf-unchosen');
  document.getElementById('pf-d-wait-d1').style.display = 'none';

  if (d1Result === 'no') {
    _pfSetCaption('pfCaption2', ex.decisions.d1.noText);
    ex.sourceAgents.forEach(n => { const el = document.getElementById(`pf-agent-${n}`); if (el) el.classList.replace('pf-active', 'pf-done'); });
    _pfAnimating = false;
    return;
  }

  _pfSetCaption('pfCaption2', ex.decisions.d1.yesText);
  await _pfSleep(800);

  // Step 4: Checkpoints fire on bus
  bus.innerHTML = ex.checkpoints.map(c =>
    `<div class="pf-node pf-active-amber" id="pf-ck-${c.id}" style="min-width:100px;">
      <div style="font-weight:700;">${c.id}</div>
      <div style="font-size:0.42rem;">${c.phase}: ${c.label}</div>
    </div>`
  ).join('<span style="color:var(--text-muted);font-size:0.8rem;">+</span>');
  ex.sourceAgents.forEach(n => { const el = document.getElementById(`pf-agent-${n}`); if (el) { el.classList.remove('pf-active'); el.classList.add('pf-done'); } });
  await _pfSleep(1200);

  // Step 5: Cross-reference lines (highlight cross-referenced agents)
  for (const ref of ex.crossRefs) {
    const agent = document.getElementById(`pf-agent-${ref.to}`);
    if (agent) agent.classList.add('pf-crossref');
  }
  _pfClearCaption('pfCaption2');
  await _pfSleep(300);
  _pfSetCaption('pfCaption1', `Cross-system context: ${ex.crossRefs.map(r => `Agent ${r.to} — ${r.reason}`).join(' | ')}`);
  await _pfSleep(2000);

  // Step 6: Decision 2 — Cross-system impact
  engine.innerHTML += _pfBuildDecision('d2', ex.decisions.d2);
  const d2Diamond = document.getElementById('pf-diamond-d2');
  if (d2Diamond) d2Diamond.classList.add('pf-active-amber');

  const d2Result = await _pfAwaitDecision('d2', ex.decisions.d2.q);
  if (d2Result === 'cancel') return;

  if (d2Diamond) { d2Diamond.classList.remove('pf-active-amber'); d2Diamond.classList.add(d2Result === 'yes' ? 'pf-done' : 'pf-done-no'); }
  document.getElementById('pf-d-yes-d2')?.classList.add(d2Result === 'yes' ? 'pf-chosen' : 'pf-unchosen');
  document.getElementById('pf-d-no-d2')?.classList.add(d2Result === 'no' ? 'pf-chosen' : 'pf-unchosen');
  document.getElementById('pf-d-wait-d2').style.display = 'none';

  if (d2Result === 'no') {
    _pfSetCaption('pfCaption2', ex.decisions.d2.noText);
    ex.crossRefs.forEach(r => { const el = document.getElementById(`pf-agent-${r.to}`); if (el) el.classList.remove('pf-crossref'); });
    ex.checkpoints.forEach(c => { const el = document.getElementById(`pf-ck-${c.id}`); if (el) { el.classList.remove('pf-active-amber'); el.classList.add('pf-done'); } });
    _pfAnimating = false;
    return;
  }

  _pfSetCaption('pfCaption2', ex.decisions.d2.yesText);
  await _pfSleep(1200);

  // Step 7: Decision 3 — Compounding risk
  engine.innerHTML += _pfBuildDecision('d3', ex.decisions.d3);
  const d3Diamond = document.getElementById('pf-diamond-d3');
  if (d3Diamond) d3Diamond.classList.add('pf-active-amber');

  const d3Result = await _pfAwaitDecision('d3', ex.decisions.d3.q);
  if (d3Result === 'cancel') return;

  if (d3Diamond) { d3Diamond.classList.remove('pf-active-amber'); d3Diamond.classList.add(d3Result === 'yes' ? 'pf-done' : 'pf-done-no'); }
  document.getElementById('pf-d-yes-d3')?.classList.add(d3Result === 'yes' ? 'pf-chosen' : 'pf-unchosen');
  document.getElementById('pf-d-no-d3')?.classList.add(d3Result === 'no' ? 'pf-chosen' : 'pf-unchosen');
  document.getElementById('pf-d-wait-d3').style.display = 'none';

  if (d3Result === 'no') {
    _pfSetCaption('pfCaption2', ex.decisions.d3.noText);
    _pfAnimating = false;
    return;
  }

  _pfSetCaption('pfCaption2', ex.decisions.d3.yesText);
  await _pfSleep(800);

  // Step 8: Prediction appears
  const sevColor = ex.severity === 'critical' ? 'red' : ex.severity === 'high' ? 'amber' : 'blue';
  engine.innerHTML += `
    <span style="color:var(--text-muted);font-size:0.8rem;">&#x25B6;</span>
    <div class="pf-node pf-active-purple" id="pf-prediction" style="min-width:120px;">
      <div style="font-weight:700;">${ex.prediction.id}</div>
      <div style="font-size:0.42rem;">${ex.prediction.title.substring(0, 40)}...</div>
      <span class="badge badge-${sevColor}" style="font-size:0.42rem;margin-top:4px;">${ex.prediction.severity}</span>
    </div>`;
  await _pfSleep(1500);

  // Step 9: Impact projection
  const impact = document.getElementById('pfImpactZone');
  impact.innerHTML = `
    <div style="display:flex;gap:8px;justify-content:center;flex-wrap:wrap;margin-bottom:8px;">
      <div style="font-size:0.55rem;color:var(--text-muted);font-family:var(--font-mono);">PHASES:</div>
      ${ex.impactPhases.map(p => `<span class="badge badge-${sevColor}" style="font-size:0.48rem;">${p}</span>`).join('')}
      <div style="font-size:0.55rem;color:var(--text-muted);font-family:var(--font-mono);margin-left:8px;">AGENTS:</div>
      ${ex.impactAgents.map(a => `<span class="badge badge-cyan" style="font-size:0.48rem;">${a}</span>`).join('')}
    </div>
    <div style="font-size:0.62rem;color:var(--${sevColor});font-weight:600;">${ex.impactText}</div>`;

  // Highlight impacted agents in Layer 1
  ex.impactAgents.forEach(n => {
    const el = document.getElementById(`pf-agent-${n}`);
    if (el && !el.classList.contains('pf-done')) el.classList.add('pf-active-red');
  });
  await _pfSleep(1500);

  // Step 10: Decision 4 — Remediate
  _pfSetCaption('pfCaption3', '');
  const feedback = document.getElementById('pfFeedback');
  feedback.innerHTML = _pfBuildDecision('d4', ex.decisions.d4);
  const d4Diamond = document.getElementById('pf-diamond-d4');
  if (d4Diamond) d4Diamond.classList.add('pf-active-amber');

  const d4Result = await _pfAwaitDecision('d4', ex.decisions.d4.q);
  if (d4Result === 'cancel') return;

  if (d4Diamond) { d4Diamond.classList.remove('pf-active-amber'); d4Diamond.classList.add(d4Result === 'yes' ? 'pf-done' : 'pf-done-no'); }
  document.getElementById('pf-d-yes-d4')?.classList.add(d4Result === 'yes' ? 'pf-chosen' : 'pf-unchosen');
  document.getElementById('pf-d-no-d4')?.classList.add(d4Result === 'no' ? 'pf-chosen' : 'pf-unchosen');
  document.getElementById('pf-d-wait-d4').style.display = 'none';

  if (d4Result === 'no') {
    _pfSetCaption('pfCaption3', ex.decisions.d4.noText);
    const pred = document.getElementById('pf-prediction');
    if (pred) { pred.classList.remove('pf-active-purple'); pred.classList.add('pf-active-amber'); }
    _pfAnimating = false;
    return;
  }

  // Step 11: Feedback loop
  _pfSetCaption('pfCaption3', ex.recommendation);
  await _pfSleep(1200);

  feedback.innerHTML += `
    <div class="pf-feedback-arrow pf-visible" style="margin-top:10px;">
      &#x21B0; FEEDBACK: Agent ${ex.feedbackAgent} re-runs with fix &#x21B0;
    </div>
    <div style="font-size:0.52rem;color:var(--teal);margin-top:6px;font-family:var(--font-mono);">
      Agent re-executes → new checkpoint data feeds back into cycle
    </div>`;

  // Flash feedback agent
  const fbAgent = document.getElementById(`pf-agent-${ex.feedbackAgent}`);
  if (fbAgent) {
    fbAgent.classList.remove('pf-active-red', 'pf-crossref');
    fbAgent.classList.add('pf-active');
    await _pfSleep(1500);
    fbAgent.classList.remove('pf-active');
    fbAgent.classList.add('pf-done');
  }

  // Settle all to done
  await _pfSleep(800);
  ex.crossRefs.forEach(r => {
    const el = document.getElementById(`pf-agent-${r.to}`);
    if (el) { el.classList.remove('pf-crossref', 'pf-active-red'); el.classList.add('pf-done'); }
  });
  ex.impactAgents.forEach(n => {
    const el = document.getElementById(`pf-agent-${n}`);
    if (el) { el.classList.remove('pf-active-red'); el.classList.add('pf-done'); }
  });
  ex.checkpoints.forEach(c => {
    const el = document.getElementById(`pf-ck-${c.id}`);
    if (el) { el.classList.remove('pf-active-amber'); el.classList.add('pf-done'); }
  });
  const pred = document.getElementById('pf-prediction');
  if (pred) { pred.classList.remove('pf-active-purple'); pred.classList.add('pf-done'); }

  _pfAnimating = false;
}

// ── Prediction Cards ────────────────────────────────────────────────

function renderPredictions(predictions) {
  const panel = document.getElementById('predictionsPanel');
  const badge = document.getElementById('predictionCount');
  if (!panel || !badge) return;

  badge.textContent = `${predictions.length} FORECASTS`;

  const severityColors = {
    critical: { border: 'var(--red)', dot: 'dot-red' },
    high: { border: 'var(--amber)', dot: 'dot-amber' },
    medium: { border: 'var(--blue)', dot: 'dot-blue' },
    low: { border: 'var(--green)', dot: 'dot-green' },
  };

  const categoryColors = {
    bottleneck: { bg: 'var(--amber-dim)', color: 'var(--amber)' },
    compliance: { bg: 'var(--purple-dim)', color: 'var(--purple)' },
    capacity: { bg: 'var(--cyan-dim)', color: 'var(--cyan)' },
    security: { bg: 'var(--red-dim)', color: 'var(--red)' },
  };

  panel.innerHTML = `
    <div style="padding:14px;display:flex;flex-direction:column;gap:10px;">
      ${predictions.map((p, idx) => {
        const sev = severityColors[p.severity] || severityColors.medium;
        const cat = categoryColors[p.category] || categoryColors.bottleneck;
        const catLabel = p.category.toUpperCase();
        const agentList = p.affected_agents.map(a => String(a).padStart(2, '0')).join(', ');
        const phaseList = p.affected_phases.map(ph => ph.toUpperCase()).join(', ');
        const sourceList = p.source_checkpoints.join(', ');

        return `
          <div class="prediction-card" style="
            background:var(--bg-card);
            border:1px solid var(--border);
            border-left:4px solid ${sev.border};
            border-radius:var(--radius);
            overflow:hidden;
            animation: fadeIn 0.3s ease ${idx * 0.08}s both;
            position:relative;
          ">
            <div class="prediction-scanline"></div>
            <div style="padding:14px 16px;">
              <div style="display:flex;align-items:center;gap:8px;margin-bottom:8px;flex-wrap:wrap;">
                <div class="health-dot ${sev.dot}" style="width:8px;height:8px;"></div>
                <span class="badge" style="background:${cat.bg};color:${cat.color};font-size:0.48rem;padding:2px 6px;letter-spacing:1px;">${catLabel}</span>
                <span style="font-size:0.55rem;color:var(--text-muted);font-family:var(--font-mono);letter-spacing:0.5px;margin-left:auto;">${p.severity.toUpperCase()}</span>
              </div>
              <div style="font-weight:700;font-size:0.82rem;color:var(--text-bright);margin-bottom:6px;line-height:1.4;">${p.title}</div>
              <div style="font-size:0.72rem;color:var(--text-standard);line-height:1.6;margin-bottom:10px;">${p.description}</div>
              <div style="display:flex;flex-wrap:wrap;gap:12px;margin-bottom:8px;">
                <div style="font-size:0.6rem;color:var(--text-muted);">
                  <span style="font-family:var(--font-mono);letter-spacing:0.5px;">BASED ON:</span>
                  <span style="color:var(--amber);font-family:var(--font-mono);margin-left:4px;">${sourceList}</span>
                </div>
                <div style="font-size:0.6rem;color:var(--text-muted);">
                  <span style="font-family:var(--font-mono);letter-spacing:0.5px;">AGENTS:</span>
                  <span style="color:var(--cyan);font-family:var(--font-mono);margin-left:4px;">${agentList}</span>
                </div>
                <div style="font-size:0.6rem;color:var(--text-muted);">
                  <span style="font-family:var(--font-mono);letter-spacing:0.5px;">PHASES:</span>
                  <span style="color:var(--purple);font-family:var(--font-mono);margin-left:4px;">${phaseList}</span>
                </div>
              </div>
              <div style="font-size:0.65rem;color:var(--text-muted);margin-bottom:6px;">
                <span style="font-family:var(--font-mono);font-size:0.55rem;letter-spacing:0.5px;">PREDICTED IMPACT:</span>
                <span style="color:${sev.border};margin-left:4px;">${p.predicted_impact}</span>
              </div>
              <details class="prediction-rec">
                <summary style="
                  font-family:var(--font-mono);
                  font-size:0.58rem;
                  font-weight:600;
                  color:var(--teal);
                  cursor:pointer;
                  letter-spacing:0.5px;
                  padding:6px 0;
                  user-select:none;
                ">&#x25B6; RECOMMENDATION</summary>
                <div style="
                  font-size:0.72rem;
                  color:var(--text-standard);
                  line-height:1.7;
                  padding:10px 14px;
                  margin-top:6px;
                  background:var(--bg-surface);
                  border:1px solid var(--border);
                  border-radius:var(--radius);
                ">${p.recommendation}</div>
              </details>
            </div>
          </div>`;
      }).join('')}
    </div>
    ${_renderPredictiveFlow()}
  `;

  // Auto-select first example after render
  setTimeout(() => selectPredictiveExample(1), 300);
}

// ── Circuit Breaker Panel ──────────────────────────────────────────

async function renderCircuitBreaker() {
  const panel = document.getElementById('circuitBreakerPanel');
  const badge = document.getElementById('cbStatusBadge');
  if (!panel) return;

  const data = await API.get('/circuit-breaker');
  if (!data || data.error) return;

  const stateColor = { CLOSED: 'green', HALF_OPEN: 'amber', OPEN: 'red' };
  const stateDot   = { CLOSED: 'dot-green', HALF_OPEN: 'dot-amber', OPEN: 'dot-red' };
  const stateBadge = { CLOSED: 'badge-green', HALF_OPEN: 'badge-amber', OPEN: 'badge-red' };

  const s = data.summary;
  if (badge) {
    if (s.open > 0) {
      badge.className = 'badge badge-red';
      badge.textContent = `${s.open} OPEN`;
    } else if (s.half_open > 0) {
      badge.className = 'badge badge-amber';
      badge.textContent = `${s.half_open} HALF-OPEN`;
    } else {
      badge.className = 'badge badge-green';
      badge.textContent = 'ALL CLOSED';
    }
  }

  const targets = Object.entries(data.targets);
  panel.innerHTML = `
    <div style="display:grid;grid-template-columns:repeat(auto-fill,minmax(200px,1fr));gap:10px;padding:14px;">
      ${targets.map(([key, t]) => `
        <div style="background:var(--bg-surface);border:1px solid var(--border);border-top:3px solid var(--${stateColor[t.state]});border-radius:var(--radius);padding:12px;">
          <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px;">
            <div style="font-size:0.68rem;font-weight:700;color:var(--text-bright)">${t.label}</div>
            <span class="badge ${stateBadge[t.state]}" style="font-size:0.45rem;">${t.state.replace('_', '-')}</span>
          </div>
          <div style="display:flex;align-items:center;gap:6px;margin-bottom:6px;">
            <div class="health-dot ${stateDot[t.state]}"></div>
            <div style="font-size:0.6rem;color:var(--text-muted);">
              ${t.state === 'CLOSED' ? 'Normal operation' :
                t.state === 'HALF_OPEN' ? 'Recovery probe — ' + t.half_open_probes + ' probe(s)' :
                'All calls rejected'}
            </div>
          </div>
          <div style="display:grid;grid-template-columns:1fr 1fr;gap:4px;margin-top:8px;">
            <div style="font-size:0.58rem;color:var(--text-muted);">Failures<br><span style="color:var(--${t.failure_count > 0 ? 'amber' : 'text-standard'});font-weight:700;">${t.failure_count}</span></div>
            <div style="font-size:0.58rem;color:var(--text-muted);">Error Rate<br><span style="color:var(--${t.error_rate_pct > 5 ? 'red' : t.error_rate_pct > 1 ? 'amber' : 'text-standard'});font-weight:700;">${t.error_rate_pct.toFixed(1)}%</span></div>
            <div style="font-size:0.58rem;color:var(--text-muted);">Avg Latency<br><span style="color:var(--${t.avg_latency_ms > 2000 ? 'red' : t.avg_latency_ms > 500 ? 'amber' : 'text-standard'});font-weight:700;">${t.avg_latency_ms}ms</span></div>
            <div style="font-size:0.58rem;color:var(--text-muted);">Fallback<br><span style="color:var(--cyan);font-family:var(--font-mono);font-size:0.5rem;">${t.fallback_strategy.replace('_', ' ')}</span></div>
          </div>
          ${t.last_trip ? `<div style="font-size:0.52rem;color:var(--amber);margin-top:8px;font-family:var(--font-mono);">Last trip: ${new Date(t.last_trip).toLocaleTimeString()}</div>` : ''}
        </div>
      `).join('')}
    </div>
    <div style="padding:0 14px 12px;font-size:0.58rem;color:var(--text-muted);font-family:var(--font-mono);">
      CLOSED = normal &nbsp;&bull;&nbsp; HALF-OPEN = recovery probe &nbsp;&bull;&nbsp; OPEN = all calls rejected &nbsp;&bull;&nbsp; Updated: ${new Date(data.last_updated).toLocaleTimeString()}
    </div>
  `;
}

// ── Schema Drift Panel ─────────────────────────────────────────────

async function renderSchemaDrift() {
  const panel = document.getElementById('schemaDriftPanel');
  const badge = document.getElementById('driftEventCount');
  if (!panel) return;

  const data = await API.get('/schema-drift/events');
  if (!data || data.error) return;

  const s = data.summary;
  if (badge) {
    const hasCritHigh = s.critical > 0 || s.high > 0;
    badge.className = `badge ${hasCritHigh ? 'badge-red' : s.medium > 0 ? 'badge-amber' : 'badge-muted'}`;
    badge.textContent = `${s.total} EVENTS`;
  }

  const sevColor  = { CRITICAL: 'red', HIGH: 'amber', MEDIUM: 'blue', LOW: 'green', INFO: 'text-muted' };
  const sevBadge  = { CRITICAL: 'badge-red', HIGH: 'badge-amber', MEDIUM: 'badge-cyan', LOW: 'badge-green', INFO: 'badge-muted' };
  const catIcon   = { STRUCTURAL: '&#x25A0;', PLATFORM: '&#x25C6;', ACCOUNT: '&#x25CF;', POLICY: '&#x26A0;', MEMBERSHIP: '&#x21C4;', CONNECTIVITY: '&#x26A1;' };

  const bs = data.baseline_snapshot;
  const cs = data.current_snapshot;

  panel.innerHTML = `
    <div style="display:grid;grid-template-columns:1fr 1fr;gap:10px;padding:14px 14px 8px;">
      <div style="background:var(--bg-surface);border:1px solid var(--border);border-radius:var(--radius);padding:10px 12px;">
        <div style="font-size:0.55rem;color:var(--text-muted);font-family:var(--font-mono);margin-bottom:4px;">BASELINE — ${bs.phase} SNAPSHOT</div>
        <div style="font-size:0.65rem;color:var(--text-standard);">${bs.total_safes} Safes &bull; ${bs.total_accounts.toLocaleString()} Accounts</div>
        <div style="font-size:0.5rem;color:var(--text-muted);font-family:var(--font-mono);margin-top:4px;">hash: ${bs.schema_hash}</div>
      </div>
      <div style="background:var(--bg-surface);border:1px solid ${bs.schema_hash !== cs.schema_hash ? 'var(--amber)' : 'var(--border)'};border-radius:var(--radius);padding:10px 12px;">
        <div style="font-size:0.55rem;color:var(--text-muted);font-family:var(--font-mono);margin-bottom:4px;">CURRENT SNAPSHOT</div>
        <div style="font-size:0.65rem;color:var(--text-standard);">${cs.total_safes} Safes &bull; ${cs.total_accounts.toLocaleString()} Accounts
          <span style="color:var(--amber);margin-left:6px;">+${cs.total_safes - bs.total_safes} Safe</span>
          <span style="color:var(--amber);margin-left:6px;">+${cs.total_accounts - bs.total_accounts} Accts</span>
        </div>
        <div style="font-size:0.5rem;color:${bs.schema_hash !== cs.schema_hash ? 'var(--amber)' : 'var(--green)'};font-family:var(--font-mono);margin-top:4px;">hash: ${cs.schema_hash} ${bs.schema_hash !== cs.schema_hash ? '⚠ DRIFTED' : '✓ MATCH'}</div>
      </div>
    </div>
    <div style="padding:0 14px 14px;display:flex;flex-direction:column;gap:6px;">
      ${data.events.map(e => `
        <div style="display:flex;align-items:flex-start;gap:10px;padding:8px 10px;background:var(--bg-surface);border:1px solid var(--border);border-left:3px solid var(--${sevColor[e.severity]});border-radius:var(--radius);">
          <span style="font-size:0.8rem;color:var(--${sevColor[e.severity]});margin-top:1px;">${catIcon[e.category] || '&#x25CF;'}</span>
          <div style="flex:1">
            <div style="display:flex;gap:6px;align-items:center;margin-bottom:3px;flex-wrap:wrap;">
              <span class="badge ${sevBadge[e.severity]}" style="font-size:0.42rem;">${e.severity}</span>
              <span class="badge badge-muted" style="font-size:0.42rem;">${e.category}</span>
              <span style="font-size:0.58rem;color:var(--text-bright);font-weight:600;">${e.safe_name}</span>
              ${e.status === 'YELLOW_CHECKPOINT_FIRED' ? `<span style="font-size:0.42rem;color:var(--amber);font-family:var(--font-mono);">&#x1F7E1; ${e.checkpoint_id}</span>` : ''}
            </div>
            <div style="font-size:0.62rem;color:var(--text-standard);line-height:1.5;">${e.description}</div>
            <div style="font-size:0.55rem;color:var(--text-muted);margin-top:3px;font-family:var(--font-mono);">${e.delta} &bull; ${new Date(e.detected_at).toLocaleString()}</div>
          </div>
        </div>
      `).join('')}
    </div>
    <div style="padding:0 14px 12px;font-size:0.58rem;color:var(--text-muted);font-family:var(--font-mono);">
      ${s.checkpoints_fired} checkpoint(s) fired &bull; Last scan: ${new Date(data.last_scan).toLocaleTimeString()} &bull; Prevents 98%→77% accuracy decay over multi-year Cisco engagement
    </div>
  `;
}

// ── Mission Control Blurb ──────────────────────────────────────────
function _renderMissionBlurb() {
  return `
    <details class="callout callout-teal" style="margin-top:20px;cursor:pointer;font-size:0.68rem;line-height:1.6;">
      <summary style="font-weight:700;user-select:none;">What You're Looking At</summary>
      <p style="margin:8px 0 0;">Mission Control is the real-time command center for the PAM migration. The stats row shows total account inventory across all waves. The phase timeline tracks progress through 8 phases (P0-P7). Agent health monitors the 15 AI agents executing the migration. Risk profile categorizes accounts by migration complexity. Gate status tracks human approval checkpoints. Yellow checkpoints show AI-detected conditions requiring attention. Predictions forecast risks before they materialize.</p>
      <p style="margin:6px 0 0;"><strong>For technical teams:</strong> All data originates from the 15-agent orchestrator. Stats aggregate agent outputs (Agent 01 discovery counts, Agent 12 NHI classifications). Predictions are derived from yellow checkpoint <code style="font-family:var(--font-mono);color:var(--teal);">cross_system_context</code> correlations — not static rules. The dashboard refreshes on each page visit to reflect current agent state.</p>
    </details>`;
}

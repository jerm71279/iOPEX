/**
 * HELIX — Cascade Simulator
 */

let cascadeRunning = false;
let cascadeTimer = null;

const CASCADE_STEPS = [
  {
    id: 'trigger',
    system: 'DnP SQL',
    label: 'SOURCE',
    event: 'Identity update triggered — DoB field: NULL → 10/9/1981',
    result: 'Cascade initiated — downstream sync sequence started',
    status: 'idle',
  },
  {
    id: 'oneview',
    system: 'One View',
    label: 'BROADBAND',
    event: 'Receiving identity delta from DnP SQL',
    result: '✓ DoB updated to 10/9/1981 — sync confirmed',
    status: 'idle',
  },
  {
    id: 'saf',
    system: 'SAF',
    label: 'DIGITAL IDENTITY',
    event: 'Awaiting identity delta...',
    result: '✗ No response — cascade stalled. Record remains: DoB NULL',
    status: 'idle',
    failure: true,
  },
  {
    id: 'hub',
    system: 'Customer Hub',
    label: 'PROFILE (MONGODB)',
    event: 'Awaiting identity delta...',
    result: '✗ Not reached — stale record persists: DoB NULL',
    status: 'idle',
    failure: true,
  },
];

const AI_STEPS = [
  {
    agent: 'Observability Agent',
    alias: 'The Interceptor',
    event: 'Cascade stall detected — SAF + Customer Hub have not received delta within 30s window',
    action: 'Capturing data delta: { field: "DoB", old: null, new: "10/9/1981", target: ["SAF", "Customer Hub"] }',
    color: 'var(--cyan)',
  },
  {
    agent: 'Resolution Agent',
    alias: 'The Precision Fixer',
    event: 'Received delta payload from Observability Agent',
    action: 'Executing targeted fix → SAF: pushing DoB = 10/9/1981',
    color: 'var(--green)',
  },
  {
    agent: 'Resolution Agent',
    alias: 'The Precision Fixer',
    event: 'SAF confirmed — DoB updated ✓',
    action: 'Executing targeted fix → Customer Hub: pushing DoB = 10/9/1981',
    color: 'var(--green)',
  },
  {
    agent: 'Resolution Agent',
    alias: 'The Precision Fixer',
    event: 'Customer Hub confirmed — DoB updated ✓',
    action: 'All downstream targets consistent — resolution complete. Logging to audit.',
    color: 'var(--green)',
  },
  {
    agent: 'RPA Automation',
    alias: 'The User Advocate',
    event: 'Backend fix confirmed across all domains',
    action: 'Clearing stale auth state for Buck Barrow (BB-0042) — login access restored ✓',
    color: 'var(--purple)',
  },
];

function renderCascade() {
  const el = document.getElementById('cascadeContent');
  if (!el) return;
  cascadeRunning = false;
  if (cascadeTimer) clearTimeout(cascadeTimer);

  el.innerHTML = `
    <div class="callout amber" style="margin-bottom:20px;">
      <div class="callout-title">Scenario: Buck Barrow — DoB Update (BB-0042)</div>
      <p>Identity Date of Birth updated in DnP SQL. Watch the cascade trigger, the Partial Success Trap, and the AI layer's autonomous resolution in real time.</p>
    </div>

    <div class="panel">
      <div class="panel-header">
        <div class="panel-title">Cascade Simulation</div>
        <div style="display:flex;gap:8px;align-items:center;">
          <select id="simSpeed" style="background:var(--bg-surface);color:var(--text-standard);border:1px solid var(--border);border-radius:4px;padding:4px 8px;font-size:0.72rem;">
            <option value="1">1× Speed</option>
            <option value="2">2× Speed</option>
            <option value="0.5">0.5× Speed</option>
          </select>
          <button class="btn btn-sm btn-bt" id="runCascadeBtn" onclick="runCascade()">▶ Run Simulation</button>
          <button class="btn btn-sm btn-ghost" onclick="resetCascade()">Reset</button>
        </div>
      </div>
      <div class="cascade-pipeline" id="simPipeline" style="flex-direction:column;gap:8px;padding:20px;"></div>
    </div>

    <div class="panel" id="aiLayerPanel" style="display:none;">
      <div class="panel-header">
        <div class="panel-title" style="color:var(--bt);">&#x2B21; AI Intelligence Layer — Activating</div>
        <span class="badge badge-bt" id="aiStepBadge">INTERCEPTED</span>
      </div>
      <div id="aiStepList" style="padding:14px;"></div>
    </div>

    <div class="panel" id="outcomePanel" style="display:none;">
      <div class="panel-header">
        <div class="panel-title">Outcome</div>
        <span class="badge badge-green">RESOLVED</span>
      </div>
      <div class="panel-body">
        <div style="display:grid;grid-template-columns:repeat(auto-fill,minmax(160px,1fr));gap:12px;margin-bottom:16px;">
          <div class="stat-card"><div class="stat-label">Total Time</div><div class="stat-value" style="color:var(--green);">8s</div><div class="stat-sub">vs ~4h manual</div></div>
          <div class="stat-card"><div class="stat-label">Staff Involved</div><div class="stat-value" style="color:var(--green);">0</div><div class="stat-sub">Fully autonomous</div></div>
          <div class="stat-card"><div class="stat-label">Systems Fixed</div><div class="stat-value" style="color:var(--bt);">2</div><div class="stat-sub">SAF + Customer Hub</div></div>
          <div class="stat-card"><div class="stat-label">User Impact</div><div class="stat-value" style="color:var(--green);">0</div><div class="stat-sub">Login restored</div></div>
        </div>
        <div class="callout green">
          <div class="callout-title">&#x2713; All systems consistent</div>
          <p>DnP SQL, One View, SAF, Customer Hub, and Excalibur are all reporting DoB = 10/9/1981 for account BB-0042 (Buck Barrow). Audit log updated. Zero manual intervention required.</p>
        </div>
      </div>
    </div>
  `;

  buildSimPipeline();
}

function buildSimPipeline() {
  const pipeline = document.getElementById('simPipeline');
  if (!pipeline) return;
  pipeline.innerHTML = CASCADE_STEPS.map((s, i) => `
    <div id="sim-step-${s.id}" style="display:flex;align-items:flex-start;gap:12px;padding:12px 16px;background:var(--bg-surface);border:1px solid var(--border);border-radius:var(--radius);transition:all 0.4s ease;">
      <div style="min-width:24px;height:24px;border-radius:50%;background:var(--bg-card);border:2px solid var(--border);display:flex;align-items:center;justify-content:center;font-family:var(--font-mono);font-size:0.6rem;font-weight:700;color:var(--text-muted);flex-shrink:0;margin-top:2px;" id="sim-dot-${s.id}">${i+1}</div>
      <div style="flex:1;">
        <div style="display:flex;gap:8px;align-items:center;margin-bottom:4px;">
          <span style="font-family:var(--font-mono);font-size:0.58rem;color:var(--text-muted);letter-spacing:1px;">${s.label}</span>
          <strong style="font-size:0.82rem;color:var(--text-bright);">${s.system}</strong>
          <span class="badge badge-muted" id="sim-badge-${s.id}">WAITING</span>
        </div>
        <div style="font-size:0.72rem;color:var(--text-muted);" id="sim-msg-${s.id}">${s.event}</div>
      </div>
    </div>
  `).join('');
}

function runCascade() {
  if (cascadeRunning) return;
  cascadeRunning = true;
  resetCascadeState();
  document.getElementById('runCascadeBtn').disabled = true;
  document.getElementById('aiLayerPanel').style.display = 'none';
  document.getElementById('outcomePanel').style.display = 'none';

  const speed = parseFloat(document.getElementById('simSpeed').value) || 1;
  const delay = (ms) => ms / speed;

  // Step through cascade
  let t = 0;
  CASCADE_STEPS.forEach((step, i) => {
    cascadeTimer = setTimeout(() => animateStep(step, i), t += delay(i === 0 ? 500 : 1200));
  });

  // After cascade shows failure — activate AI layer
  setTimeout(() => {
    document.getElementById('aiLayerPanel').style.display = 'block';
    document.getElementById('aiLayerPanel').scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    let aiDelay = 0;
    const aiList = document.getElementById('aiStepList');
    if (aiList) aiList.innerHTML = '';
    AI_STEPS.forEach((step, i) => {
      setTimeout(() => renderAiStep(step, i), aiDelay += delay(1400));
    });

    // Show outcome
    setTimeout(() => {
      document.getElementById('outcomePanel').style.display = 'block';
      document.getElementById('outcomePanel').scrollIntoView({ behavior: 'smooth', block: 'nearest' });
      document.getElementById('runCascadeBtn').disabled = false;
      cascadeRunning = false;
      showToast('<strong>Simulation complete</strong><br>All systems healed. Zero staff intervention.', 'bt');
    }, aiDelay + delay(1200));

  }, t + delay(800));
}

function animateStep(step, i) {
  const stepEl = document.getElementById(`sim-step-${step.id}`);
  const dotEl = document.getElementById(`sim-dot-${step.id}`);
  const badgeEl = document.getElementById(`sim-badge-${step.id}`);
  const msgEl = document.getElementById(`sim-msg-${step.id}`);
  if (!stepEl) return;

  if (step.failure) {
    stepEl.style.borderColor = 'var(--red)';
    stepEl.style.background = 'var(--red-dim)';
    dotEl.style.background = 'var(--red)';
    dotEl.style.borderColor = 'var(--red)';
    dotEl.style.color = '#fff';
    dotEl.innerHTML = '✗';
    badgeEl.className = 'badge badge-red';
    badgeEl.textContent = 'STALLED';
    msgEl.textContent = step.result;
    msgEl.style.color = 'var(--red)';
  } else {
    stepEl.style.borderColor = 'var(--green)';
    stepEl.style.background = 'var(--green-dim)';
    dotEl.style.background = 'var(--green)';
    dotEl.style.borderColor = 'var(--green)';
    dotEl.style.color = '#fff';
    dotEl.innerHTML = '✓';
    badgeEl.className = 'badge badge-green';
    badgeEl.textContent = 'SYNCED';
    msgEl.textContent = step.result;
    msgEl.style.color = 'var(--green)';
  }
}

function renderAiStep(step, i) {
  const list = document.getElementById('aiStepList');
  if (!list) return;
  const div = document.createElement('div');
  div.className = 'animate-in';
  div.style.cssText = 'display:flex;gap:12px;padding:10px 14px;background:var(--bg-surface);border:1px solid var(--border);border-radius:var(--radius);margin-bottom:8px;';
  div.innerHTML = `
    <div style="width:8px;height:8px;border-radius:50%;background:${step.color};box-shadow:0 0 8px ${step.color};flex-shrink:0;margin-top:6px;"></div>
    <div>
      <div style="font-family:var(--font-mono);font-size:0.6rem;color:${step.color};letter-spacing:1px;">${step.agent.toUpperCase()} — ${step.alias}</div>
      <div style="font-size:0.72rem;color:var(--text-muted);margin:2px 0;">${step.event}</div>
      <div style="font-size:0.72rem;color:var(--text-standard);font-weight:500;">${step.action}</div>
    </div>`;
  list.appendChild(div);
}

function resetCascadeState() {
  CASCADE_STEPS.forEach(step => {
    const stepEl = document.getElementById(`sim-step-${step.id}`);
    const dotEl = document.getElementById(`sim-dot-${step.id}`);
    const badgeEl = document.getElementById(`sim-badge-${step.id}`);
    const msgEl = document.getElementById(`sim-msg-${step.id}`);
    if (!stepEl) return;
    stepEl.style.borderColor = 'var(--border)';
    stepEl.style.background = 'var(--bg-surface)';
    if (dotEl) { dotEl.style.background = 'var(--bg-card)'; dotEl.style.borderColor = 'var(--border)'; dotEl.style.color = 'var(--text-muted)'; }
    if (badgeEl) { badgeEl.className = 'badge badge-muted'; badgeEl.textContent = 'WAITING'; }
    if (msgEl) { msgEl.textContent = step.event; msgEl.style.color = 'var(--text-muted)'; }
  });
}

function resetCascade() {
  cascadeRunning = false;
  if (cascadeTimer) clearTimeout(cascadeTimer);
  resetCascadeState();
  const ai = document.getElementById('aiLayerPanel');
  const out = document.getElementById('outcomePanel');
  if (ai) ai.style.display = 'none';
  if (out) out.style.display = 'none';
  const btn = document.getElementById('runCascadeBtn');
  if (btn) btn.disabled = false;
}

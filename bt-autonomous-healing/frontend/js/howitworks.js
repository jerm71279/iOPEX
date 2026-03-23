/**
 * HELIX — How It Works: 8-act animated infographic
 */

const HIW_ACTS = [
  {
    title: 'The Trigger',
    desc: 'A customer\'s Date of Birth is updated in the DnP SQL identity database. This fires a cascade — a chain of synchronisation events that should update all downstream systems.',
    nodes: [
      { label: 'SOURCE', name: 'DnP SQL', cls: 'healthy' },
      { arrow: '→', arrowCls: 'live' },
      { label: 'BROADBAND', name: 'One View', cls: '' },
      { arrow: '→', arrowCls: '' },
      { label: 'DIGITAL ID', name: 'SAF', cls: '' },
      { arrow: '→', arrowCls: '' },
      { label: 'PROFILE', name: 'Customer Hub', cls: '' },
    ],
    log: [
      { cls: 'log-cyan', text: '[14:31:51] DnP SQL → Trigger fired: DoB update — NULL → 10/9/1981' },
      { cls: 'log-cyan', text: '[14:31:51] Cascade sequence initiated across downstream systems' },
    ],
  },
  {
    title: 'Cascade Starts',
    desc: 'The first step succeeds. One View — the broadband database — receives and applies the identity update. DoB is now correct in broadband.',
    nodes: [
      { label: 'SOURCE', name: 'DnP SQL', cls: 'healthy' },
      { arrow: '→', arrowCls: 'live' },
      { label: 'BROADBAND', name: 'One View', cls: 'healthy' },
      { arrow: '→', arrowCls: '' },
      { label: 'DIGITAL ID', name: 'SAF', cls: '' },
      { arrow: '→', arrowCls: '' },
      { label: 'PROFILE', name: 'Customer Hub', cls: '' },
    ],
    log: [
      { cls: 'log-green', text: '[14:31:52] One View ✓ — DoB updated to 10/9/1981' },
      { cls: 'log-cyan', text: '[14:31:52] Cascade continuing to SAF...' },
    ],
  },
  {
    title: 'The Partial Success Trap',
    desc: 'The cascade stalls. SAF — Digital Identity — does not receive the update. The chain breaks here. Customer Hub is also unreached. This is "The Tangle."',
    nodes: [
      { label: 'SOURCE', name: 'DnP SQL', cls: 'healthy' },
      { arrow: '→', arrowCls: 'live' },
      { label: 'BROADBAND', name: 'One View', cls: 'healthy' },
      { arrow: '→', arrowCls: 'broken' },
      { label: 'DIGITAL ID', name: 'SAF', cls: 'failed' },
      { arrow: '→', arrowCls: '' },
      { label: 'PROFILE', name: 'Customer Hub', cls: 'failed' },
    ],
    log: [
      { cls: 'log-red', text: '[14:31:58] ✗ SAF — No response. Cascade stalled.' },
      { cls: 'log-red', text: '[14:31:58] ✗ Customer Hub — Not reached. Stale record persists.' },
      { cls: 'log-amber', text: '[14:31:58] ⚠ Data inconsistency: One View has new DoB. SAF + Customer Hub have NULL.' },
    ],
  },
  {
    title: 'The Tangle',
    desc: 'The customer now exists in an inconsistent state across the BT estate. One View has the correct DoB, but SAF and Customer Hub still have the old value. The customer cannot authenticate — login fails.',
    nodes: [
      { label: 'SOURCE', name: 'DnP SQL', cls: 'healthy' },
      { arrow: '→', arrowCls: 'live' },
      { label: 'BROADBAND', name: 'One View', cls: 'healthy' },
      { arrow: '→', arrowCls: 'broken' },
      { label: 'DIGITAL ID', name: 'SAF', cls: 'stale' },
      { arrow: '→', arrowCls: '' },
      { label: 'PROFILE', name: 'Customer Hub', cls: 'stale' },
    ],
    log: [
      { cls: 'log-amber', text: '[14:32:01] Customer attempts login — authentication failure' },
      { cls: 'log-amber', text: '[14:32:01] SAF returning stale identity: DoB = NULL' },
      { cls: 'log-red', text: '[14:32:01] Without AI layer: staff escalation required (~4 hours to resolve)' },
    ],
  },
  {
    title: 'Observability Agent Activates',
    desc: 'The Observability Agent — always watching the cascade — detects the stall within 30 seconds. It captures the exact data delta and prepares it for autonomous re-orchestration.',
    nodes: [
      { label: 'SOURCE', name: 'DnP SQL', cls: 'healthy' },
      { arrow: '→', arrowCls: 'live' },
      { label: 'BROADBAND', name: 'One View', cls: 'healthy' },
      { arrow: '→', arrowCls: 'broken' },
      { label: 'DIGITAL ID', name: 'SAF', cls: 'stale' },
      { arrow: '→', arrowCls: '' },
      { label: 'PROFILE', name: 'Customer Hub', cls: 'stale' },
      { extra: true, label: 'AI AGENT', name: 'Observability', cls: 'agent' },
    ],
    log: [
      { cls: 'log-bt', text: '[14:31:58] Observability Agent: Cascade stall detected at 30s threshold' },
      { cls: 'log-bt', text: '[14:31:58] Capturing delta: { field: DoB, old: NULL, new: 10/9/1981 }' },
      { cls: 'log-bt', text: '[14:31:58] Triggering Resolution Agent with delta payload' },
    ],
  },
  {
    title: 'Precision Fix Executed',
    desc: 'The Resolution Agent receives the data delta and executes targeted fixes — pushing only the changed field to SAF and Customer Hub. No full resync. No race conditions.',
    nodes: [
      { label: 'SOURCE', name: 'DnP SQL', cls: 'healthy' },
      { arrow: '→', arrowCls: 'live' },
      { label: 'BROADBAND', name: 'One View', cls: 'healthy' },
      { arrow: '→', arrowCls: 'healing' },
      { label: 'DIGITAL ID', name: 'SAF', cls: 'healing' },
      { arrow: '→', arrowCls: 'healing' },
      { label: 'PROFILE', name: 'Customer Hub', cls: 'healing' },
    ],
    log: [
      { cls: 'log-green', text: '[14:32:04] Resolution Agent → SAF: pushing DoB = 10/9/1981' },
      { cls: 'log-green', text: '[14:32:05] SAF ✓ confirmed — DoB = 10/9/1981' },
      { cls: 'log-green', text: '[14:32:06] Resolution Agent → Customer Hub: pushing DoB = 10/9/1981' },
      { cls: 'log-green', text: '[14:32:07] Customer Hub ✓ confirmed — DoB = 10/9/1981' },
    ],
  },
  {
    title: 'User Access Restored',
    desc: 'The RPA Automation agent operates at the application layer — clearing the stale authentication state so the customer can log in immediately, without any manual intervention.',
    nodes: [
      { label: 'SOURCE', name: 'DnP SQL', cls: 'healthy' },
      { arrow: '→', arrowCls: 'live' },
      { label: 'BROADBAND', name: 'One View', cls: 'healthy' },
      { arrow: '→', arrowCls: 'live' },
      { label: 'DIGITAL ID', name: 'SAF', cls: 'healthy' },
      { arrow: '→', arrowCls: 'live' },
      { label: 'PROFILE', name: 'Customer Hub', cls: 'healthy' },
    ],
    log: [
      { cls: 'log-bt', text: '[14:32:07] RPA Automation: Backend fix confirmed — clearing stale auth tokens' },
      { cls: 'log-green', text: '[14:32:08] Account recovery complete — login restored ✓' },
      { cls: 'log-green', text: '[14:32:08] Customer authenticated successfully' },
    ],
  },
  {
    title: 'Zero Manual Intervention',
    desc: 'All five BT systems are consistent. The entire healing cycle completed in 8 seconds. No staff escalation. No ticket. No customer wait. This is the Autonomous Healing Architecture.',
    nodes: [
      { label: 'SOURCE', name: 'DnP SQL', cls: 'healthy' },
      { arrow: '→', arrowCls: 'live' },
      { label: 'BROADBAND', name: 'One View', cls: 'healthy' },
      { arrow: '→', arrowCls: 'live' },
      { label: 'DIGITAL ID', name: 'SAF', cls: 'healthy' },
      { arrow: '→', arrowCls: 'live' },
      { label: 'PROFILE', name: 'Customer Hub', cls: 'healthy' },
    ],
    log: [
      { cls: 'log-green', text: '[14:32:09] ✓ All 5 domains consistent — identity verified across estate' },
      { cls: 'log-green', text: '[14:32:09] Audit log entry written — full delta + resolution chain recorded' },
      { cls: 'log-bt',   text: '[14:32:09] Autonomous Healing Architecture: 8 seconds. 0 staff. 0 escalations.' },
    ],
  },
];

let hiwCurrentAct = 0;
let hiwPlaying = false;
let hiwInterval = null;

function renderHowItWorks() {
  const el = document.getElementById('howItWorksContent');
  if (!el) return;
  hiwCurrentAct = 0;
  hiwPlaying = false;
  if (hiwInterval) clearInterval(hiwInterval);

  el.innerHTML = `
    <!-- Progress dots -->
    <div class="hiw-progress" id="hiwProgress">
      ${HIW_ACTS.map((_, i) => `<div class="hiw-progress-dot${i === 0 ? ' active' : ''}" id="hiw-dot-${i}"></div>`).join('')}
    </div>

    <!-- Stage -->
    <div class="hiw-stage" id="hiwStage"></div>

    <!-- Log -->
    <div class="hiw-log" id="hiwLog"></div>

    <!-- Controls -->
    <div class="hiw-controls" style="margin-top:16px;">
      <button class="btn btn-bt btn-sm" id="hiwPlayBtn" onclick="hiwTogglePlay()">&#x25B6; Play</button>
      <button class="btn btn-ghost btn-sm" onclick="hiwPrev()">&#x25C0; Prev</button>
      <button class="btn btn-ghost btn-sm" onclick="hiwNext()">Next &#x25B6;</button>
      <select id="hiwSpeed" style="background:var(--bg-surface);color:var(--text-standard);border:1px solid var(--border);border-radius:4px;padding:4px 8px;font-size:0.72rem;">
        <option value="3000">1× Speed</option>
        <option value="1500">2× Speed</option>
        <option value="6000">0.5× Speed</option>
      </select>
      <button class="btn btn-ghost btn-sm" onclick="hiwRestart()">&#x21BA; Restart</button>
      <div class="hiw-step-counter" id="hiwCounter">Act 1 of ${HIW_ACTS.length}</div>
    </div>
  `;

  hiwRenderAct(0);
}

function hiwRenderAct(idx) {
  const act = HIW_ACTS[idx];
  if (!act) return;

  // Update progress dots
  HIW_ACTS.forEach((_, i) => {
    const dot = document.getElementById(`hiw-dot-${i}`);
    if (!dot) return;
    dot.className = 'hiw-progress-dot' + (i < idx ? ' done' : i === idx ? ' active' : '');
  });

  const counter = document.getElementById('hiwCounter');
  if (counter) counter.textContent = `Act ${idx + 1} of ${HIW_ACTS.length}`;

  const stage = document.getElementById('hiwStage');
  if (stage) {
    stage.innerHTML = `
      <div class="hiw-act-label">ACT ${idx + 1} / ${HIW_ACTS.length}</div>
      <div class="hiw-act-title animate-in">${act.title}</div>
      <div class="hiw-act-desc animate-in">${act.desc}</div>
      <div class="hiw-diagram animate-in">
        ${act.nodes.map(n => {
          if (n.arrow) return `<div class="hiw-arrow ${n.arrowCls || ''}">${n.arrow}</div>`;
          if (n.extra) return `
            <div style="margin-left:16px;padding-left:16px;border-left:2px dashed var(--bt);">
              <div class="hiw-node ${n.cls}">
                <div class="hiw-node-label">${n.label}</div>
                <div class="hiw-node-name">${n.name}</div>
              </div>
            </div>`;
          return `<div class="hiw-node ${n.cls}">
            <div class="hiw-node-label">${n.label}</div>
            <div class="hiw-node-name">${n.name}</div>
          </div>`;
        }).join('')}
      </div>`;
  }

  const log = document.getElementById('hiwLog');
  if (log) {
    log.innerHTML = act.log.map(l => `<div class="log-entry ${l.cls}">${l.text}</div>`).join('\n');
  }
}

function hiwNext() {
  if (hiwCurrentAct < HIW_ACTS.length - 1) {
    hiwCurrentAct++;
    hiwRenderAct(hiwCurrentAct);
  } else {
    hiwStop();
  }
}

function hiwPrev() {
  if (hiwCurrentAct > 0) {
    hiwCurrentAct--;
    hiwRenderAct(hiwCurrentAct);
  }
}

function hiwTogglePlay() {
  if (hiwPlaying) {
    hiwStop();
  } else {
    hiwPlay();
  }
}

function hiwPlay() {
  hiwPlaying = true;
  const btn = document.getElementById('hiwPlayBtn');
  if (btn) btn.innerHTML = '&#x23F8; Pause';
  const speed = parseInt(document.getElementById('hiwSpeed')?.value || 3000);
  hiwInterval = setInterval(() => {
    if (hiwCurrentAct < HIW_ACTS.length - 1) {
      hiwCurrentAct++;
      hiwRenderAct(hiwCurrentAct);
    } else {
      hiwStop();
    }
  }, speed);
}

function hiwStop() {
  hiwPlaying = false;
  if (hiwInterval) clearInterval(hiwInterval);
  const btn = document.getElementById('hiwPlayBtn');
  if (btn) btn.innerHTML = '&#x25B6; Play';
}

function hiwRestart() {
  hiwStop();
  hiwCurrentAct = 0;
  hiwRenderAct(0);
}

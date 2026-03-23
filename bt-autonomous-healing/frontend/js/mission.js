/**
 * HELIX — Mission Control page
 */

const DOMAINS = [
  { id: 'dnp',     name: 'DnP SQL',        role: 'Identity Source',       status: 'healthy',    msg: 'Trigger source active — 0 pending events' },
  { id: 'oneview', name: 'One View',        role: 'Broadband',             status: 'healthy',    msg: 'Last sync: 2 min ago — 1,847 accounts' },
  { id: 'saf',     name: 'SAF',             role: 'Digital Identity',      status: 'stale',      msg: '3 stale records — awaiting Resolution Agent' },
  { id: 'hub',     name: 'Customer Hub',    role: 'Profile (MongoDB)',     status: 'stale',      msg: '3 stale records — queued for healing' },
  { id: 'excal',   name: 'Excalibur',       role: 'Mobile / BACS',         status: 'healthy',    msg: 'Delinquency data current — last sync: 8 min' },
];

const AGENTS = [
  { id: 'obs',  name: 'Observability Agent', alias: 'The Interceptor', status: 'monitoring', msg: 'Monitoring cascade — 0 active failures' },
  { id: 'res',  name: 'Resolution Agent',    alias: 'The Precision Fixer', status: 'active',  msg: 'Executing 3 targeted fixes — SAF + Customer Hub' },
  { id: 'heal', name: 'Healing Agent',        alias: 'The System Restorer', status: 'standby', msg: 'On standby — no full restoration required' },
  { id: 'rpa',  name: 'RPA Automation',       alias: 'The User Advocate',  status: 'standby',  msg: 'Application layer ready — 0 account recoveries pending' },
];

const EVENTS = [
  { time: '14:32:07', type: 'bt',    msg: 'Resolution Agent: DoB delta (10/9/1981) pushed to SAF — account BB-0042' },
  { time: '14:32:05', type: 'bt',    msg: 'Resolution Agent: DoB delta pushed to Customer Hub — account BB-0042' },
  { time: '14:31:58', type: 'amber', msg: 'Observability Agent: Cascade stall detected — SAF + Customer Hub out of sync post One View update' },
  { time: '14:31:52', type: 'green', msg: 'One View: Identity update applied — Buck Barrow (BB-0042) DoB: 10/9/1981' },
  { time: '14:31:51', type: 'cyan',  msg: 'DnP SQL trigger: Identity DoB update — account BB-0042 → cascade initiated' },
  { time: '14:28:14', type: 'green', msg: 'Healing Agent: System restoration complete — all 5 domains consistent' },
  { time: '14:25:03', type: 'bt',    msg: 'RPA Automation: Account recovery complete — login restored for affected user' },
];

const STATS = [
  { label: 'Domains Monitored', value: '5',   sub: 'All active',    color: 'var(--green)' },
  { label: 'AI Agents Active',  value: '4',   sub: '1 executing',   color: 'var(--bt)' },
  { label: 'Stale Records',     value: '3',   sub: 'Being resolved', color: 'var(--amber)' },
  { label: 'Healed Today',      value: '47',  sub: 'Zero manual',   color: 'var(--green)' },
  { label: 'Avg Heal Time',     value: '8s',  sub: 'vs 4h manual',  color: 'var(--cyan)' },
  { label: 'Staff Escalations', value: '0',   sub: 'This session',  color: 'var(--green)' },
];

function renderMissionControl() {
  // Stats
  const statsEl = document.getElementById('missionStats');
  if (statsEl) {
    statsEl.innerHTML = STATS.map(s => `
      <div class="stat-card">
        <div class="stat-label">${s.label}</div>
        <div class="stat-value" style="color:${s.color}">${s.value}</div>
        <div class="stat-sub">${s.sub}</div>
      </div>`).join('');
  }

  // Domain health
  const domainEl = document.getElementById('domainHealthGrid');
  if (domainEl) {
    domainEl.innerHTML = DOMAINS.map(d => {
      const dotClass = d.status === 'healthy' ? 'dot-green' : d.status === 'stale' ? 'dot-amber' : 'dot-red';
      return `<div class="health-item">
        <div class="health-dot ${dotClass}"></div>
        <div class="health-info">
          <div class="health-name">${d.name} <span style="font-size:0.6rem;color:var(--text-muted);font-family:var(--font-mono);">${d.role}</span></div>
          <div class="health-msg">${d.msg}</div>
        </div>
      </div>`;
    }).join('');
  }

  // Agent health
  const agentEl = document.getElementById('agentHealthGrid');
  if (agentEl) {
    agentEl.innerHTML = AGENTS.map(a => {
      const dotClass = a.status === 'monitoring' ? 'dot-bt' : a.status === 'active' ? 'dot-green' : 'dot-amber';
      return `<div class="health-item">
        <div class="health-dot ${dotClass}"></div>
        <div class="health-info">
          <div class="health-name">${a.name} <span style="font-size:0.58rem;color:var(--bt);font-family:var(--font-mono);">${a.alias}</span></div>
          <div class="health-msg">${a.msg}</div>
        </div>
      </div>`;
    }).join('');
  }

  // Badge updates
  const agentBadge = document.getElementById('agentStatusBadge');
  if (agentBadge) agentBadge.textContent = '1 EXECUTING';

  // Recent events
  const eventsEl = document.getElementById('recentEvents');
  if (eventsEl) {
    const typeColors = { bt: 'var(--bt)', amber: 'var(--amber)', green: 'var(--green)', cyan: 'var(--cyan)', red: 'var(--red)' };
    eventsEl.innerHTML = EVENTS.map(e => `
      <div class="audit-row">
        <div class="audit-time">${e.time}</div>
        <div class="audit-action" style="color:${typeColors[e.type] || 'var(--text-standard)'};">${e.msg}</div>
      </div>`).join('');
    document.getElementById('eventCount').textContent = `${EVENTS.length} EVENTS`;
  }

  // Cascade health mini view
  const cascadeEl = document.getElementById('cascadeHealthPanel');
  if (cascadeEl) {
    const steps = [
      { name: 'DnP SQL',       status: 'done' },
      { name: 'One View',      status: 'done' },
      { name: 'SAF',           status: 'healing' },
      { name: 'Customer Hub',  status: 'healing' },
      { name: 'Excalibur',     status: 'done' },
    ];
    const arrowStatus = ['active', 'active', 'healing', 'healing'];
    const arrowColors = { active: 'live', healing: 'healing', broken: 'broken' };
    cascadeEl.innerHTML = steps.map((s, i) => {
      const arrow = i < steps.length - 1
        ? `<div class="cascade-arrow ${arrowColors[arrowStatus[i]] || ''}">&rarr;</div>`
        : '';
      return `<div class="cascade-step ${s.status}">
        <div class="cascade-step-label">SYSTEM</div>
        <div class="cascade-step-name">${s.name}</div>
      </div>${arrow}`;
    }).join('');
    document.getElementById('cascadeHealthBadge').textContent = '2 HEALING';
  }
}

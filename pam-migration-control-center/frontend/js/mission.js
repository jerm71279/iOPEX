/**
 * Mission Control page renderer.
 */

async function renderMissionControl() {
  const [stats, risks, timeline, agents, gates] = await Promise.all([
    API.get('/dashboard/stats'),
    API.get('/dashboard/risks'),
    API.get('/dashboard/timeline'),
    API.get('/agents'),
    API.get('/gates'),
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
}

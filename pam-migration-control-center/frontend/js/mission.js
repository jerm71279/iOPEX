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

  // Predictive Insights
  renderPredictions(predictions);
}

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
  `;
}

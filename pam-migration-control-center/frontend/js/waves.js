/**
 * Wave Execution page renderer + ETL pipeline animation.
 */

let waveAnimating = false;

async function renderWaves() {
  const waves = await API.get('/waves');
  const riskColors = { low: 'green', medium: 'amber', high: 'red', critical: 'red' };

  // Wave cards
  document.getElementById('waveCards').innerHTML = waves.map(w => `
    <div class="wave-card">
      <div class="wave-number" style="color:var(--${riskColors[w.risk]})">${w.id}</div>
      <div class="wave-info">
        <div class="wave-name">${w.name}</div>
        <div class="wave-type">${w.type}</div>
        <div style="display:flex;gap:6px;margin-top:4px;flex-wrap:wrap">
          ${w.agents.map(a => `<span class="badge badge-cyan">${a.num}</span>`).join('')}
        </div>
      </div>
      <div class="wave-stats">
        <span class="badge ${riskBadgeClass(w.risk)}">${w.risk.toUpperCase()}</span>
        <div style="text-align:right">
          <div style="font-family:var(--font-mono);font-size:1rem;font-weight:700;color:var(--text-bright)">${w.account_count.toLocaleString()}</div>
          <div style="font-size:0.6rem;color:var(--text-muted)">${w.account_pct}</div>
        </div>
      </div>
    </div>
  `).join('');

  // ETL pipeline for selected wave
  renderETLPipeline(waves[0]);

  // Heartbeat checks (show pilot validation format)
  renderHeartbeatChecks();
}

function renderETLPipeline(wave) {
  if (!wave) return;
  const steps = wave.etl_steps || [];
  document.getElementById('etlPipeline').innerHTML = steps.map((s, i) =>
    (i > 0 ? '<div class="etl-arrow">&#x25B6;</div>' : '') +
    `<div class="etl-step" id="etl-step-${i}">${s}</div>`
  ).join('');
  document.getElementById('etlResult').style.display = 'none';
}

async function runWaveSimulation() {
  if (waveAnimating) return;
  waveAnimating = true;
  const waveId = document.getElementById('waveSelect').value;
  const btn = document.getElementById('runWaveBtn');
  btn.textContent = 'Running...';
  btn.disabled = true;

  // Get wave data to render pipeline
  const waves = await API.get('/waves');
  const wave = waves.find(w => w.id === waveId);
  if (wave) renderETLPipeline(wave);

  // Animate steps
  const steps = document.querySelectorAll('.etl-step');
  for (let i = 0; i < steps.length; i++) {
    steps[i].classList.add('active');
    await sleep(800);
    steps[i].classList.remove('active');
    steps[i].classList.add('done');
  }

  // Fetch simulation result
  const result = await API.post(`/waves/${waveId}/simulate`);
  const rate = result.total_accounts > 0 ? ((result.migrated / result.total_accounts) * 100).toFixed(1) : '0';
  document.getElementById('etlResult').style.display = 'block';
  document.getElementById('etlResult').innerHTML = `
    <div class="callout teal">
      <div class="callout-title">Wave ${result.wave} Simulation Complete</div>
      <p>Migrated: <strong>${result.migrated}</strong> / ${result.total_accounts} accounts. Failed: <strong style="color:var(--red)">${result.failed}</strong>. Success rate: <strong>${rate}%</strong></p>
      <p style="margin-top:6px"><span style="cursor:pointer;text-decoration:underline;color:var(--cyan)" onclick="viewWaveDetail('${waveId}')">View detailed step results</span></p>
    </div>
  `;

  btn.textContent = 'Run Wave';
  btn.disabled = false;
  waveAnimating = false;

  // Update heartbeat after simulation
  renderHeartbeatChecks();
}

async function viewWaveDetail(waveId) {
  const result = await API.post(`/waves/${waveId}/simulate`);
  const total = result.total_accounts || 0;
  const migrated = result.migrated || 0;
  const failed = result.failed || 0;
  const rate = total > 0 ? ((migrated / total) * 100).toFixed(1) : '0';

  let html = `
    <div style="margin-bottom:14px;display:flex;gap:6px">
      <span class="badge badge-muted">WAVE ${result.wave}</span>
      <span class="badge ${result.status === 'simulated' ? 'badge-teal' : 'badge-amber'}">${(result.status || 'complete').toUpperCase()}</span>
    </div>
    <div class="rpt-metrics">
      ${metricCard('Total Accounts', total.toLocaleString())}
      ${metricCard('Migrated', migrated.toLocaleString(), 'var(--green)')}
      ${metricCard('Failed', failed.toLocaleString(), failed > 0 ? 'var(--red)' : 'var(--text-muted)')}
      ${metricCard('Success Rate', rate + '%', parseFloat(rate) >= 95 ? 'var(--green)' : 'var(--amber)')}
    </div>
    <div class="rpt-section-label">ETL Pipeline Steps</div>
  `;

  (result.steps || []).forEach(step => {
    const durSec = (step.duration_ms / 1000).toFixed(1);
    const pct = step.status === 'done' ? 100 : (step.status === 'active' ? 50 : 0);
    html += `
      <div class="rpt-step">
        <div class="rpt-step-header">
          <span class="rpt-step-name">${step.step}</span>
          <span class="rpt-step-dur">${durSec}s</span>
        </div>
        <div class="rpt-progress"><div class="rpt-progress-fill" style="width:${pct}%"></div></div>
        <div class="rpt-step-detail">${step.detail}</div>
      </div>
    `;
  });

  html += renderCollapsibleJSON(result);
  openDrill(`Wave ${result.wave} — ETL Pipeline Detail`, html);
}

function renderHeartbeatChecks() {
  const isOptB = API.option === 'b';
  const checks = [
    { name: 'Count Comparison', msg: '2847 source = 2847 target (0.0% variance)', status: 'pass' },
    { name: 'Heartbeat Status', msg: '2705/2847 verified (95.0%)', status: 'pass' },
    { name: 'Permission Mapping', msg: isOptB ? '22→22 parity verified, 0 exceptions' : '22→4 role mapping verified, 0 exceptions', status: 'pass' },
    { name: isOptB ? 'Safe Structure' : 'Folder Structure', msg: isOptB ? '142 safes created in Privilege Cloud' : '142 folders created, hierarchy correct', status: 'pass' },
    { name: 'Metadata Integrity', msg: 'All description/custom fields preserved', status: 'pass' },
    { name: 'Group Assignments', msg: '234 group memberships translated', status: 'pass' },
    { name: 'Password Policies', msg: isOptB ? 'Cloud CPM rotation active per platform' : 'Rotation policies applied per template', status: 'pass' },
    { name: 'Access Patterns', msg: '0 unexpected permission escalations', status: 'pass' },
    { name: 'Audit Continuity', msg: isOptB ? 'Audit logs migrated to Privilege Cloud' : 'Audit entries present for all accounts', status: 'pass' },
    { name: 'Recording Preservation', msg: isOptB ? 'PSM recordings transferred to cloud storage' : 'Manual verification required in P7', status: isOptB ? 'pass' : 'warn' },
  ];

  document.getElementById('heartbeatChecks').innerHTML = checks.map(c => `
    <div class="health-item">
      <div class="health-dot ${c.status === 'pass' ? 'dot-green' : c.status === 'warn' ? 'dot-amber' : 'dot-red'}"></div>
      <div>
        <div class="health-name">${c.name}</div>
        <div class="health-msg">${c.msg}</div>
      </div>
    </div>
  `).join('');
}

function sleep(ms) { return new Promise(r => setTimeout(r, ms)); }

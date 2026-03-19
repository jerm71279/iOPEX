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

  // Heartbeat checks
  renderHeartbeatChecks();

  // Agent 18 integrity report (default wave 1)
  renderIntegrityReport('1');
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

  // ML anomaly overlay
  await renderETLAnomalyOverlay(waveId);

  btn.textContent = 'Run Wave';
  btn.disabled = false;
  waveAnimating = false;

  // Update heartbeat + integrity after simulation
  renderHeartbeatChecks();
  renderIntegrityReport(waveId);
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
  const opt = API.option;
  const checks = [
    { name: 'Count Comparison', msg: '2847 source = 2847 target (0.0% variance)', status: 'pass' },
    { name: 'Heartbeat Status', msg: '2705/2847 verified (95.0%)', status: 'pass' },
    {
      name: 'Permission Mapping',
      msg: opt === 'b' ? '22→4 axes verified, 3 escalation flags reviewed' :
           opt === 'c' ? '22→3 levels verified, 5 escalation flags reviewed' :
           '22→Vault roles verified, 2 escalation flags reviewed',
      status: 'pass',
    },
    {
      name: opt === 'b' ? 'Shared Folder / PAM Hierarchy' : opt === 'c' ? 'Resource Group Structure' : 'Vault Structure',
      msg: opt === 'b' ? '142 shared folders + PAM hierarchy created (pamUser/pamMachine/pamDatabase)' :
           opt === 'c' ? '142 resource groups created, hierarchy correct' :
           '142 vaults created in Devolutions Server, hierarchy correct',
      status: 'pass',
    },
    { name: 'Metadata Integrity', msg: 'All description/custom fields preserved', status: 'pass' },
    { name: 'Group Assignments', msg: '234 group memberships translated', status: 'pass' },
    {
      name: 'Password Policies',
      msg: opt === 'b' ? 'Keeper Gateway rotation active per platform (~25-30 platforms covered)' :
           opt === 'c' ? 'MiniOrange rotation policies applied per resource group' :
           'Devolutions RDM Agent rotation active per entry type',
      status: 'pass',
    },
    { name: 'Access Patterns', msg: '0 unexpected permission escalations detected', status: 'pass' },
    {
      name: 'Audit Continuity',
      msg: opt === 'b' ? 'CyberArk audit archived read-only; Keeper event log active' :
           opt === 'c' ? 'CyberArk audit archived read-only; MiniOrange basic audit active' :
           'CyberArk audit archived read-only; Devolutions audit log active',
      status: 'warn',
    },
    {
      name: 'Recording Preservation',
      msg: opt === 'b' ? 'CyberArk PSM archived; KCM (Guacamole) session recording active going forward' :
           opt === 'c' ? 'CyberArk PSM archived; MiniOrange limited recording — manual verification required' :
           'CyberArk PSM archived; RDM session recording active going forward',
      status: opt === 'c' ? 'warn' : 'pass',
    },
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

// ── Agent 18 — Integrity Validation Report ──────────────────────────

async function renderIntegrityReport(waveId) {
  const panel = document.getElementById('integrityChecksPanel');
  const badge = document.getElementById('integrityAccBadge');
  if (!panel) return;

  panel.innerHTML = '<div style="padding:14px;color:var(--text-muted);font-size:0.7rem;">Loading integrity report...</div>';

  const data = await API.get(`/integrity/${waveId}`);
  if (data.error) {
    panel.innerHTML = `<div style="padding:14px;color:var(--red);font-size:0.7rem;">${data.error}</div>`;
    return;
  }

  const accColor = data.accuracy_pct >= 99 ? 'var(--green)' : data.accuracy_pct >= 95 ? 'var(--amber)' : 'var(--red)';
  if (badge) badge.textContent = `${data.accuracy_pct.toFixed(1)}% ACCURACY`;

  const statusColor = { pass: 'dot-green', warn: 'dot-amber', fail: 'dot-red' };
  const statusLabel = { pass: 'PASS', warn: 'WARN', fail: 'FAIL' };
  const statusBadge = { pass: 'badge-green', warn: 'badge-amber', fail: 'badge-red' };
  const sevColor = { CRITICAL: 'var(--red)', HIGH: 'var(--amber)', MEDIUM: 'var(--blue)' };

  panel.innerHTML = `
    <div style="padding:14px 18px 8px;display:flex;gap:10px;flex-wrap:wrap;border-bottom:1px solid var(--border);margin-bottom:8px;">
      <div style="display:flex;flex-direction:column;align-items:center;padding:8px 14px;background:var(--bg-surface);border:1px solid var(--border);border-radius:var(--radius);min-width:70px;">
        <div style="font-size:1.1rem;font-weight:800;color:${accColor}">${data.accuracy_pct.toFixed(1)}%</div>
        <div style="font-size:0.52rem;color:var(--text-muted);margin-top:2px;">Accuracy</div>
      </div>
      <div style="display:flex;flex-direction:column;align-items:center;padding:8px 14px;background:var(--bg-surface);border:1px solid var(--border);border-radius:var(--radius);min-width:60px;">
        <div style="font-size:1.1rem;font-weight:800;color:var(--green)">${data.passed}</div>
        <div style="font-size:0.52rem;color:var(--text-muted);margin-top:2px;">Passed</div>
      </div>
      <div style="display:flex;flex-direction:column;align-items:center;padding:8px 14px;background:var(--bg-surface);border:1px solid ${data.failed > 0 ? 'var(--red)' : 'var(--border)'};border-radius:var(--radius);min-width:60px;">
        <div style="font-size:1.1rem;font-weight:800;color:${data.failed > 0 ? 'var(--red)' : 'var(--text-muted)'}">${data.failed}</div>
        <div style="font-size:0.52rem;color:var(--text-muted);margin-top:2px;">Failed</div>
      </div>
      <div style="display:flex;flex-direction:column;align-items:center;padding:8px 14px;background:var(--bg-surface);border:1px solid ${data.warned > 0 ? 'var(--amber)' : 'var(--border)'};border-radius:var(--radius);min-width:60px;">
        <div style="font-size:1.1rem;font-weight:800;color:${data.warned > 0 ? 'var(--amber)' : 'var(--text-muted)'}">${data.warned}</div>
        <div style="font-size:0.52rem;color:var(--text-muted);margin-top:2px;">Warned</div>
      </div>
      <div style="flex:1;display:flex;flex-direction:column;justify-content:center;padding:8px 12px;background:var(--bg-surface);border:1px solid var(--border);border-radius:var(--radius);min-width:160px;">
        <div style="font-size:0.6rem;color:var(--text-muted);font-family:var(--font-mono);">WAVE ${data.wave} — ${data.wave_name}</div>
        <div style="font-size:0.6rem;color:var(--text-muted);margin-top:3px;">${data.total_accounts.toLocaleString()} accounts &bull; ${data.checks_run} IC checks</div>
        <div style="font-size:0.55rem;color:var(--purple);margin-top:3px);font-family:var(--font-mono);">${data.session}</div>
      </div>
    </div>
    <div class="health-grid" style="padding:8px 14px 14px;">
      ${data.checks.map(c => `
        <div class="health-item" style="${c.status === 'fail' ? 'border:1px solid var(--red-dim);background:var(--red-dim);border-radius:4px;' : c.status === 'warn' ? 'border:1px solid var(--amber-dim);background:var(--amber-dim);border-radius:4px;' : ''}">
          <div class="health-dot ${statusColor[c.status]}"></div>
          <div style="flex:1">
            <div class="health-name" style="display:flex;gap:6px;align-items:center;">
              <span>${c.id}</span>
              <span style="color:var(--text-standard)">${c.name}</span>
              ${c.blocking ? '<span style="font-size:0.42rem;font-family:var(--font-mono);color:' + sevColor[c.severity] + ';border:1px solid currentColor;padding:1px 4px;border-radius:2px;">BLOCKING</span>' : ''}
            </div>
            <div class="health-msg">${c.detail}</div>
          </div>
          <span class="badge ${statusBadge[c.status]}" style="font-size:0.42rem;">${statusLabel[c.status]}</span>
        </div>
      `).join('')}
    </div>
  `;
}

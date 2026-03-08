/**
 * Account Explorer — grouping, batching, migration flow, and profile drilldown.
 */

let acctViewTab = 'explorer';   // 'explorer' | 'flow'
let acctGroupBy = 'department';
let acctBatchBy = 'wave';
let acctFilterGroup = null;     // active group card filter
let acctSearch = '';
let acctFilters = { wave: '', risk: '', status: '', nhi_type: '' };

// ── Main entry point ────────────────────────────────────────────────
async function renderAccountExplorer() {
  const el = document.getElementById('page-accounts');
  if (!el) return;

  el.innerHTML = `
    <div class="page-header">
      <div class="page-title">Account Explorer</div>
      <div class="page-subtitle">50 Accounts — Grouped by Organization, Platform, NHI Type & Wave</div>
    </div>

    <!-- View Tabs -->
    <div class="view-tabs">
      <button class="view-tab ${acctViewTab === 'explorer' ? 'active' : ''}"
              onclick="acctSwitchTab('explorer')">Account Explorer</button>
      <button class="view-tab ${acctViewTab === 'flow' ? 'active' : ''}"
              onclick="acctSwitchTab('flow')">Migration Flow</button>
    </div>

    <div id="acctExplorerView" style="display:${acctViewTab === 'explorer' ? 'block' : 'none'}">
      <div id="acctStats" class="stats-grid"></div>
      <div id="acctGroupTabs"></div>
      <div id="acctGroupCards" class="acct-group-grid"></div>
      <div id="acctSearchBar"></div>
      <div id="acctTable"></div>
    </div>

    <div id="acctFlowView" style="display:${acctViewTab === 'flow' ? 'block' : 'none'}">
      <div id="acctBatchSelector"></div>
      <div id="acctClassRules"></div>
      <div id="acctFlowLanes"></div>
    </div>
  `;

  if (acctViewTab === 'explorer') {
    await _renderExplorer();
  } else {
    await _renderFlow();
  }
}

function acctSwitchTab(tab) {
  acctViewTab = tab;
  renderAccountExplorer();
}

// ── Explorer View ───────────────────────────────────────────────────
async function _renderExplorer() {
  const accounts = await API.get('/accounts');
  _renderStats(accounts);
  _renderGroupTabs();
  await _renderGroupCards();
  _renderSearchBar();
  _renderAccountTable(accounts);
}

function _renderStats(accounts) {
  const total = accounts.length;
  const nhis = accounts.filter(a => a.is_nhi).length;
  const highRisk = accounts.filter(a => a.risk === 'high' || a.risk === 'critical').length;
  const blocked = accounts.filter(a => a.status === 'blocked').length;
  const batches = new Set(accounts.map(a => a.batch)).size;

  document.getElementById('acctStats').innerHTML = [
    _statCard('TOTAL ACCOUNTS', total, '--teal'),
    _statCard('NHIs', nhis, '--amber'),
    _statCard('HIGH RISK', highRisk, '--red'),
    _statCard('BLOCKED', blocked, '--red'),
    _statCard('BATCHES', batches, '--cyan'),
  ].join('');
}

function _statCard(label, value, color) {
  return `<div class="stat-card">
    <div class="stat-label">${label}</div>
    <div class="stat-value" style="color:var(${color})">${value}</div>
  </div>`;
}

function _renderGroupTabs() {
  const tabs = [
    { key: 'department', label: 'Department' },
    { key: 'role', label: 'Role' },
    { key: 'platformId', label: 'Platform' },
    { key: 'nhi_type', label: 'NHI Type' },
    { key: 'wave', label: 'Wave' },
    { key: 'risk', label: 'Risk' },
  ];
  document.getElementById('acctGroupTabs').innerHTML = `<div class="group-tabs">${
    tabs.map(t => `<button class="group-tab ${acctGroupBy === t.key ? 'active' : ''}"
      onclick="acctSetGroupBy('${t.key}')">${t.label}</button>`).join('')
  }</div>`;
}

async function acctSetGroupBy(key) {
  acctGroupBy = key;
  acctFilterGroup = null;
  _renderGroupTabs();
  await _renderGroupCards();
  // Re-fetch and re-render table (clear group filter)
  const accounts = await _fetchFilteredAccounts();
  _renderAccountTable(accounts);
}

async function _renderGroupCards() {
  const data = await API.get(`/accounts/groups?group_by=${acctGroupBy}`);
  const groups = data.groups || [];
  document.getElementById('acctGroupCards').innerHTML = groups.map(g => `
    <div class="group-card ${acctFilterGroup === g.key ? 'group-card-active' : ''}"
         onclick="acctFilterByGroup('${g.key}')">
      <div class="group-card-name">${_friendlyGroupName(g.key, acctGroupBy)}</div>
      <div class="group-card-count">${g.count}</div>
      <div class="group-card-meta">
        ${g.nhi_count ? `<span class="badge badge-amber">${g.nhi_count} NHI</span>` : ''}
        ${g.high_risk ? `<span class="badge badge-red">${g.high_risk} HIGH</span>` : ''}
      </div>
    </div>
  `).join('');
}

function _friendlyGroupName(key, groupBy) {
  if (groupBy === 'wave') return `Wave ${key}`;
  if (groupBy === 'nhi_type') {
    if (key === 'human') return 'Human';
    return key.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase());
  }
  return key;
}

async function acctFilterByGroup(key) {
  acctFilterGroup = acctFilterGroup === key ? null : key;
  await _renderGroupCards();
  const accounts = await _fetchFilteredAccounts();
  _renderAccountTable(accounts);
}

function _renderSearchBar() {
  document.getElementById('acctSearchBar').innerHTML = `
    <div class="acct-search-row">
      <input type="text" class="acct-search-input" placeholder="Search by name or userName..."
             value="${acctSearch}" oninput="acctOnSearch(this.value)">
      <select class="acct-filter-select" onchange="acctSetFilter('wave',this.value)">
        <option value="">All Waves</option>
        ${[1,2,3,4,5].map(w => `<option value="${w}" ${acctFilters.wave == w ? 'selected' : ''}>Wave ${w}</option>`).join('')}
      </select>
      <select class="acct-filter-select" onchange="acctSetFilter('risk',this.value)">
        <option value="">All Risk</option>
        ${['low','medium','high','critical'].map(r => `<option value="${r}" ${acctFilters.risk === r ? 'selected' : ''}>${r}</option>`).join('')}
      </select>
      <select class="acct-filter-select" onchange="acctSetFilter('status',this.value)">
        <option value="">All Status</option>
        ${['migrated','in_progress','pending','blocked'].map(s => `<option value="${s}" ${acctFilters.status === s ? 'selected' : ''}>${s.replace('_',' ')}</option>`).join('')}
      </select>
      <select class="acct-filter-select" onchange="acctSetFilter('nhi_type',this.value)">
        <option value="">All Types</option>
        ${['service_account','api_key','application_identity','database_account','robotic_process','machine_identity','shared_account'].map(t =>
          `<option value="${t}" ${acctFilters.nhi_type === t ? 'selected' : ''}>${t.replace(/_/g,' ')}</option>`
        ).join('')}
      </select>
    </div>
  `;
}

let _acctSearchTimer;
function acctOnSearch(val) {
  clearTimeout(_acctSearchTimer);
  _acctSearchTimer = setTimeout(async () => {
    acctSearch = val;
    const accounts = await _fetchFilteredAccounts();
    _renderAccountTable(accounts);
  }, 250);
}

async function acctSetFilter(key, val) {
  acctFilters[key] = val;
  const accounts = await _fetchFilteredAccounts();
  _renderAccountTable(accounts);
}

async function _fetchFilteredAccounts() {
  let qs = '';
  if (acctFilters.wave) qs += `&wave=${acctFilters.wave}`;
  if (acctFilters.risk) qs += `&risk=${acctFilters.risk}`;
  if (acctFilters.status) qs += `&status=${acctFilters.status}`;
  if (acctFilters.nhi_type) qs += `&nhi_type=${acctFilters.nhi_type}`;
  if (acctSearch) qs += `&search=${encodeURIComponent(acctSearch)}`;

  // Apply group filter
  if (acctFilterGroup !== null) {
    if (acctGroupBy === 'wave') qs += `&wave=${acctFilterGroup}`;
    else if (acctGroupBy === 'department') qs += `&department=${encodeURIComponent(acctFilterGroup)}`;
    else if (acctGroupBy === 'role') qs += `&role=${encodeURIComponent(acctFilterGroup)}`;
    else if (acctGroupBy === 'nhi_type' && acctFilterGroup !== 'human') qs += `&nhi_type=${acctFilterGroup}`;
    else if (acctGroupBy === 'risk') qs += `&risk=${acctFilterGroup}`;
  }

  return API.get(`/accounts?${qs}`);
}

function _renderAccountTable(accounts) {
  if (!accounts.length) {
    document.getElementById('acctTable').innerHTML = '<div class="panel" style="padding:20px;text-align:center;color:var(--text-muted);">No accounts match the current filters.</div>';
    return;
  }

  const rows = accounts.map(a => {
    const statusCls = {migrated:'badge-green',in_progress:'badge-amber',pending:'badge-muted',blocked:'badge-red'}[a.status] || 'badge-muted';
    const riskCls = riskBadgeClass(a.risk);
    const pipeLabel = a.pipeline_step === 'COMPLETE' ? '7/7' : `${a.pipeline_progress}/7`;
    const pipeColor = a.pipeline_step === 'COMPLETE' ? 'var(--green)' : 'var(--amber)';
    return `<tr class="acct-row" onclick="acctOpenProfile('${a.id}')">
      <td class="acct-name-cell">${a.name}</td>
      <td>${a.userName}</td>
      <td>${a.department}</td>
      <td><span class="badge badge-muted">${a.platformId}</span></td>
      <td>W${a.wave}</td>
      <td>${a.batch}</td>
      <td><span class="badge ${riskCls}">${a.risk}</span></td>
      <td><span class="badge ${statusCls}">${a.status.replace('_',' ')}</span></td>
      <td><span style="color:${pipeColor}">${pipeLabel} ${a.pipeline_step === 'COMPLETE' ? '' : a.pipeline_step}</span></td>
      <td>${a.is_nhi ? `<span class="badge badge-amber">${(a.nhi_type||'').replace(/_/g,' ')}</span>` : '<span style="color:var(--text-muted)">-</span>'}</td>
    </tr>`;
  }).join('');

  document.getElementById('acctTable').innerHTML = `
    <div class="panel" style="overflow-x:auto;">
      <table class="account-table">
        <thead>
          <tr>
            <th>Name</th><th>User</th><th>Department</th><th>Platform</th>
            <th>Wave</th><th>Batch</th><th>Risk</th><th>Status</th>
            <th>Pipeline</th><th>NHI Type</th>
          </tr>
        </thead>
        <tbody>${rows}</tbody>
      </table>
    </div>
  `;
}

// ── Profile Drilldown ───────────────────────────────────────────────
async function acctOpenProfile(id) {
  const a = await API.get(`/accounts/${id}`);
  if (a.error) return;

  const opt = API.option;
  const pipeSteps = ['FREEZE','EXPORT','TRANSFORM','CREATE','IMPORT','HEARTBEAT','UNFREEZE'];

  // Build pipeline progress bar
  const pipelineHtml = pipeSteps.map((s, i) => {
    let cls = '';
    if (a.pipeline_progress > i) cls = 'done';
    else if (a.pipeline_progress === i) cls = 'active';
    return `<div class="etl-step ${cls}">${s}</div>${i < pipeSteps.length - 1 ? '<span class="etl-arrow">&#x2192;</span>' : ''}`;
  }).join('');

  // NHI section
  let nhiHtml = '';
  if (a.is_nhi) {
    const confPct = Math.round(a.nhi_confidence * 100);
    nhiHtml = `
      <div class="profile-section">
        <div class="section-label">NHI CLASSIFICATION</div>
        <div class="detail-row"><div class="detail-label">TYPE</div><div class="detail-value"><span class="badge badge-amber">${(a.nhi_type||'').replace(/_/g,' ')}</span></div></div>
        <div class="detail-row"><div class="detail-label">CONFIDENCE</div><div class="detail-value">
          <div class="confidence-bar-track"><div class="confidence-bar-fill" style="width:${confPct}%;background:${confPct >= 90 ? 'var(--green)' : confPct >= 70 ? 'var(--amber)' : 'var(--red)'}"></div></div>
          <span style="font-size:0.68rem;color:var(--text-muted);margin-left:8px;">${confPct}%</span>
        </div></div>
        <div class="detail-row"><div class="detail-label">SIGNALS</div><div class="detail-value">${(a.nhi_signals||[]).map(s => `<span class="permission-chip">${s}</span>`).join(' ')}</div></div>
      </div>`;
  }

  // Permission section
  let permHtml = '';
  const pm = a.permission_mapping || {};
  if (opt === 'a') {
    permHtml = `
      <div class="profile-section">
        <div class="section-label">PERMISSIONS (${pm.model})</div>
        <div class="detail-row"><div class="detail-label">SS ROLE</div><div class="detail-value"><span class="badge badge-blue">${pm.target_role || '-'}</span></div></div>
        <div class="detail-row"><div class="detail-label">ESCALATION</div><div class="detail-value">${pm.escalation_flag ? '<span class="badge badge-red">ESCALATED</span>' : '<span class="badge badge-green">None</span>'}</div></div>
        <div class="detail-row"><div class="detail-label">SOURCE PERMS</div><div class="detail-value">${a.permissions_count} ${a.has_sensitive_permissions ? '<span class="badge badge-red">SENSITIVE</span>' : ''}</div></div>
      </div>`;
  } else {
    const perms = pm.target_permissions || [];
    const sensitive = ['ManageSafe','ManageSafeMembers','AccessWithoutConfirmation','SpecifyNextAccountContent','BackupSafe','RequestsAuthorizationLevel1','RequestsAuthorizationLevel2'];
    permHtml = `
      <div class="profile-section">
        <div class="section-label">PERMISSIONS (${pm.model})</div>
        <div class="detail-row"><div class="detail-label">MAPPED</div><div class="detail-value" style="display:flex;flex-wrap:wrap;gap:4px;">
          ${perms.map(p => `<span class="permission-chip ${sensitive.includes(p) ? 'perm-sensitive' : ''}">${p}</span>`).join('')}
        </div></div>
      </div>`;
  }

  const content = `
    <div class="profile-section">
      <div class="section-label">IDENTITY</div>
      <div class="detail-row"><div class="detail-label">NAME</div><div class="detail-value">${a.name}</div></div>
      <div class="detail-row"><div class="detail-label">USERNAME</div><div class="detail-value" style="font-family:var(--font-mono);">${a.userName}</div></div>
      <div class="detail-row"><div class="detail-label">ADDRESS</div><div class="detail-value">${a.address}</div></div>
      <div class="detail-row"><div class="detail-label">SAFE</div><div class="detail-value">${a.safeName}</div></div>
      <div class="detail-row"><div class="detail-label">PLATFORM</div><div class="detail-value"><span class="badge badge-muted">${a.platformId}</span></div></div>
      <div class="detail-row"><div class="detail-label">SECRET TYPE</div><div class="detail-value">${a.secretType}</div></div>
      <div class="detail-row"><div class="detail-label">EMPLOYEE ID</div><div class="detail-value" style="font-family:var(--font-mono);">${a.employee_id}</div></div>
    </div>

    <div class="profile-section">
      <div class="section-label">ORGANIZATION</div>
      <div class="detail-row"><div class="detail-label">DEPARTMENT</div><div class="detail-value">${a.department}</div></div>
      <div class="detail-row"><div class="detail-label">TITLE</div><div class="detail-value">${a.title}</div></div>
      <div class="detail-row"><div class="detail-label">ROLE</div><div class="detail-value"><span class="badge badge-blue">${a.role}</span></div></div>
      <div class="detail-row"><div class="detail-label">MANAGER</div><div class="detail-value">${a.manager}</div></div>
    </div>

    ${nhiHtml}

    <div class="profile-section">
      <div class="section-label">WAVE ASSIGNMENT</div>
      <div class="detail-row"><div class="detail-label">WAVE</div><div class="detail-value"><span class="badge ${riskBadgeClass(a.risk)}">Wave ${a.wave}</span></div></div>
      <div class="detail-row"><div class="detail-label">REASON</div><div class="detail-value">${a.wave_reason}</div></div>
      <div class="detail-row"><div class="detail-label">BATCH</div><div class="detail-value" style="font-family:var(--font-mono);">${a.batch}</div></div>
    </div>

    <div class="profile-section">
      <div class="section-label">PIPELINE STATUS</div>
      <div class="etl-pipeline" style="padding:12px 0;">${pipelineHtml}</div>
    </div>

    ${permHtml}

    <div class="profile-section">
      <div class="section-label">MIGRATION</div>
      <div class="detail-row"><div class="detail-label">RISK</div><div class="detail-value"><span class="badge ${riskBadgeClass(a.risk)}">${a.risk}</span></div></div>
      <div class="detail-row"><div class="detail-label">STATUS</div><div class="detail-value"><span class="badge ${
        {migrated:'badge-green',in_progress:'badge-amber',pending:'badge-muted',blocked:'badge-red'}[a.status]||'badge-muted'
      }">${a.status.replace('_',' ')}</span></div></div>
      <div class="detail-row"><div class="detail-label">DEPENDENCIES</div><div class="detail-value">${(a.dependencies||[]).length ? a.dependencies.join(', ') : 'None'}</div></div>
    </div>

    <div class="profile-section">
      <div class="section-label">TIMELINE</div>
      <div class="detail-row"><div class="detail-label">CREATED</div><div class="detail-value">${a.created_date ? new Date(a.created_date).toLocaleDateString() : '-'}</div></div>
      <div class="detail-row"><div class="detail-label">LAST ACCESSED</div><div class="detail-value">${a.last_accessed ? new Date(a.last_accessed).toLocaleDateString() : '-'}</div></div>
    </div>
  `;

  openDrill(`Account: ${a.name}`, content);
}

// ── Migration Flow View ─────────────────────────────────────────────
async function _renderFlow() {
  _renderBatchSelector();
  const data = await API.get(`/accounts/migration-flow?batch_by=${acctBatchBy}`);
  const waves = data.waves || [];

  // Classification rules (only shown in wave mode)
  if (acctBatchBy === 'wave') {
    _renderClassRules();
  } else {
    document.getElementById('acctClassRules').innerHTML = '';
  }

  _renderFlowLanes(waves);
}

function _renderBatchSelector() {
  const options = [
    { key: 'wave', label: 'Wave (Default)' },
    { key: 'department', label: 'Department' },
    { key: 'platformId', label: 'Platform' },
    { key: 'role', label: 'Role' },
    { key: 'nhi_type', label: 'NHI Type' },
    { key: 'risk', label: 'Risk Level' },
  ];
  document.getElementById('acctBatchSelector').innerHTML = `
    <div class="acct-batch-selector">
      <span class="batch-selector-label">BATCH BY:</span>
      <select class="acct-filter-select" onchange="acctSetBatchBy(this.value)">
        ${options.map(o => `<option value="${o.key}" ${acctBatchBy === o.key ? 'selected' : ''}>${o.label}</option>`).join('')}
      </select>
    </div>
  `;
}

async function acctSetBatchBy(key) {
  acctBatchBy = key;
  await _renderFlow();
}

function _renderClassRules() {
  const rules = [
    { wave: 1, label: 'TEST/DEV', pattern: "name/safe matches: test|dev|sandbox|poc|lab|demo", color: '--green' },
    { wave: 2, label: 'STANDARD', pattern: "everything else (no pattern match, not NHI)", color: '--amber' },
    { wave: 3, label: 'INFRA', pattern: "name/safe matches: infra|network|firewall|switch|router|admin", color: '--red' },
    { wave: 4, label: 'NHI (NO CCP)', pattern: "Agent 12 NHI detected, no CCP/AAM integration", color: '--red' },
    { wave: 5, label: 'NHI (CCP)', pattern: "Agent 12 NHI detected + Applications API found CCP/AAM", color: '--purple' },
  ];
  document.getElementById('acctClassRules').innerHTML = `
    <div class="panel" style="margin-bottom:16px;">
      <div class="panel-header">
        <div class="panel-title">Wave Classification Rules (Agent 04 ETL)</div>
      </div>
      <div style="padding:14px;">
        ${rules.map(r => `
          <div class="classification-rule">
            <span class="class-rule-wave" style="background:var(${r.color}-dim);color:var(${r.color});">WAVE ${r.wave}</span>
            <span class="class-rule-label">${r.label}</span>
            <span class="class-rule-arrow">&#x2190;</span>
            <span class="class-rule-pattern">${r.pattern}</span>
          </div>
        `).join('')}
      </div>
    </div>
  `;
}

function _renderFlowLanes(waves) {
  const gateMap = { g7: 'WAVE 1 COMPLETE', g8: 'WAVE 2 COMPLETE', g9: 'WAVE 3 COMPLETE', g10: 'WAVE 4 COMPLETE', g11: 'WAVE 5 COMPLETE' };
  const steps = ['FREEZE', 'EXPORT', 'TRANSFORM', 'CREATE', 'IMPORT', 'HEARTBEAT', 'UNFREEZE'];
  const riskColors = { low: '--green', medium: '--amber', high: '--red', critical: '--purple' };

  let html = '';
  waves.forEach((w, idx) => {
    const color = riskColors[w.risk] || '--teal';
    const laneName = w.name || `Group ${idx + 1}`;

    // Batch cards
    const batchHtml = w.batches.map(b => {
      const total = b.count;
      const pp = b.pipeline_progress || {};
      const barSegments = steps.map(s => {
        const cnt = pp[s] || 0;
        const pct = total > 0 ? (cnt / total) * 100 : 0;
        const segColor = pct >= 100 ? 'var(--green)' : pct > 0 ? 'var(--amber)' : 'var(--bg-surface)';
        return `<div class="pipe-seg" title="${s}: ${cnt}/${total}" style="background:${segColor};"></div>`;
      }).join('');

      const statusParts = Object.entries(b.status_breakdown || {}).map(([k, v]) => {
        const c = {migrated:'var(--green)',in_progress:'var(--amber)',pending:'var(--text-muted)',blocked:'var(--red)'}[k]||'var(--text-muted)';
        return `<span style="color:${c};font-size:0.62rem;">${v} ${k.replace('_',' ')}</span>`;
      }).join(' &middot; ');

      // Check if all complete
      const allDone = steps.every(s => (pp[s] || 0) >= total);

      return `<div class="batch-card" onclick="acctBatchDrill('${b.batch_id}')">
        <div class="batch-card-header">
          <span class="batch-card-id">${b.batch_id}</span>
          <span class="batch-card-count">${total} accounts</span>
          ${allDone ? '<span class="badge badge-green" style="margin-left:auto;">COMPLETE</span>' : ''}
        </div>
        <div class="pipeline-bar">${barSegments}</div>
        <div class="pipeline-bar-labels">
          ${steps.map(s => `<span>${s.substring(0,3)}</span>`).join('')}
        </div>
        <div class="batch-card-status">${statusParts}</div>
      </div>`;
    }).join('');

    html += `
      <div class="wave-lane" style="border-left-color:var(${color});">
        <div class="wave-lane-header">
          <span class="wave-lane-name" style="color:var(${color});">${laneName.toUpperCase()}</span>
          <span class="badge ${riskBadgeClass(w.risk)}">${w.risk}</span>
          <span style="font-size:0.68rem;color:var(--text-muted);">${w.total} accounts</span>
          ${w.gate ? `<span class="badge badge-muted" style="margin-left:auto;">Gate: ${w.gate}</span>` : ''}
        </div>
        <div class="wave-lane-batches">${batchHtml}</div>
      </div>
    `;

    // Gate connector between waves (only in wave mode)
    if (acctBatchBy === 'wave' && w.gate && idx < waves.length - 1) {
      const gateName = gateMap[w.gate] || w.gate;
      html += `
        <div class="gate-connector">
          <div class="gate-connector-line"></div>
          <div class="gate-connector-badge">
            <span class="badge badge-green">&#x2713; ${gateName}</span>
            <span style="font-size:0.55rem;color:var(--text-muted);margin-left:6px;">HUMAN APPROVAL</span>
          </div>
          <div class="gate-connector-line"></div>
        </div>
      `;
    }
  });

  document.getElementById('acctFlowLanes').innerHTML = html || '<div class="panel" style="padding:20px;text-align:center;color:var(--text-muted);">No flow data.</div>';
}

async function acctBatchDrill(batchId) {
  // Filter table to accounts in that batch — switch to explorer view with filter
  acctViewTab = 'explorer';
  acctFilterGroup = null;
  acctSearch = '';
  // Clear filters except set search to batch id prefix
  const accounts = await API.get('/accounts');
  const filtered = accounts.filter(a => a.batch === batchId);
  renderAccountExplorer();
  // After render, override table with filtered results
  setTimeout(() => _renderAccountTable(filtered), 50);
}

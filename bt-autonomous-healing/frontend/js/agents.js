/**
 * HELIX — AI Agents page
 */

const AGENT_DATA = [
  {
    id: 'obs',
    num: '01',
    name: 'Observability Agent',
    alias: 'The Interceptor',
    status: 'monitoring',
    statusLabel: 'MONITORING',
    color: 'var(--cyan)',
    colorDim: 'var(--cyan-dim)',
    desc: 'Actively monitors the data synchronisation cascade and intercepts failures immediately after the Partial Success Trap.',
    trigger: 'Cascade event from DnP SQL identity update',
    detects: 'Stall after One View update — SAF + Customer Hub not receiving delta',
    action: 'Captures data delta (field, old value, new value), logs event, triggers Resolution Agent',
    outputs: ['Failure event log with data delta', 'Resolution Agent trigger payload', 'Audit trail entry'],
    stats: { resolved: 47, avgTime: '6s', active: 0 },
    detail: 'The Interceptor operates as a passive event listener on the cascade bus. When a DnP SQL trigger fires, it tracks the propagation across all downstream systems. If SAF or Customer Hub have not received the update within a configurable window (default: 30s), it declares a cascade failure and autonomously initiates re-orchestration — pushing the captured data delta to all remaining out-of-sync stores.',
  },
  {
    id: 'res',
    num: '02',
    name: 'Resolution Agent',
    alias: 'The Precision Fixer',
    status: 'active',
    statusLabel: 'EXECUTING',
    color: 'var(--green)',
    colorDim: 'var(--green-dim)',
    desc: 'Executes targeted, granular fixes for specific data mismatches identified during system scans — field-level accuracy across distributed repositories.',
    trigger: 'Triggered by Observability Agent on cascade failure, or on schedule scan',
    detects: 'Field-level mismatches: DoB, address, mobile SIM sequence, account flags',
    action: 'Pushes corrected field values to specific out-of-sync stores only — no full resync',
    outputs: ['Per-field correction log', 'Affected system confirmation', 'Healing Agent notification if scope exceeds threshold'],
    stats: { resolved: 312, avgTime: '4s', active: 3 },
    detail: 'The Precision Fixer receives the data delta from the Observability Agent — a structured payload containing the field name, the correct value, and which systems have not yet received it. It executes targeted API calls directly to SAF and Customer Hub to apply only the changed fields. This approach avoids triggering a full resync, which would risk re-introducing race conditions. Every fix is logged with before/after values for full auditability.',
  },
  {
    id: 'heal',
    num: '03',
    name: 'Healing Agent',
    alias: 'The System Restorer',
    status: 'standby',
    statusLabel: 'STANDBY',
    color: 'var(--bt)',
    colorDim: 'var(--bt-dim)',
    desc: 'Orchestrates general system restoration when the entire multi-database environment needs returning to a verified healthy state — broader than a single field fix.',
    trigger: 'Triggered when Resolution Agent identifies widespread inconsistency (>5 affected fields) or by scheduled health scan',
    detects: 'Multi-field inconsistency, cross-domain drift, cascaded partial failures',
    action: 'Full consistency scan across all 5 domains, coordinated restoration sequence, verified healthy state confirmation',
    outputs: ['System health report', 'Restoration sequence log', 'Verified consistency confirmation across all domains'],
    stats: { resolved: 18, avgTime: '42s', active: 0 },
    detail: 'The System Restorer is the escalation path for complex, multi-field drift. Where the Precision Fixer handles single-trigger partial successes, the Healing Agent takes a broader view — running a full consistency scan across DnP SQL, One View, SAF, Customer Hub, and Excalibur to build a complete picture of drift. It then applies a coordinated restoration sequence, waiting for each domain to confirm consistency before proceeding to the next, to prevent race conditions.',
  },
  {
    id: 'rpa',
    num: '04',
    name: 'RPA Automation',
    alias: 'The User Advocate',
    status: 'standby',
    statusLabel: 'STANDBY',
    color: 'var(--purple)',
    colorDim: 'var(--purple-dim)',
    desc: 'Operates at the application layer to translate backend data fixes into restored user experiences — account recovery after login failures caused by data inconsistency.',
    trigger: 'Triggered after Resolution or Healing Agent confirms backend fix, or by customer complaint signal ("unable to login")',
    detects: 'Login failure states, account lockouts, authentication errors caused by stale SAF/Customer Hub data',
    action: 'Application-layer account recovery: clears stale auth tokens, forces re-authentication against corrected identity data, confirms login restored',
    outputs: ['Account recovery confirmation', 'User login status log', 'Customer complaint ticket auto-resolution'],
    stats: { resolved: 29, avgTime: '12s', active: 0 },
    detail: 'The backend data fix alone does not always restore user access — stale session tokens, cached identity assertions, or lingering auth failures can persist. The User Advocate handles the application-layer consequences of data inconsistency. When a customer reports being unable to log in, or when the healing agents detect that a fixed account still has an authentication failure state, the RPA Automation clears the stale auth state and forces a clean re-authentication against the now-corrected identity data.',
  },
];

let selectedAgentId = null;

function renderAgentGrid() {
  const detail = document.getElementById('agentDetail');
  const grid = document.getElementById('agentGrid');
  if (!grid) return;

  grid.innerHTML = AGENT_DATA.map(a => `
    <div class="agent-card status-${a.status} ${selectedAgentId === a.id ? 'selected' : ''}"
         onclick="selectAgent('${a.id}')">
      <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:6px;">
        <div class="agent-num">AGENT ${a.num}</div>
        <span class="badge" style="background:${a.colorDim};color:${a.color};">${a.statusLabel}</span>
      </div>
      <div class="agent-name">${a.name}</div>
      <div class="agent-alias">${a.alias}</div>
      <div class="agent-desc">${a.desc}</div>
      <div class="agent-stat-row">
        <span class="badge badge-muted">${a.stats.resolved} resolved</span>
        <span class="badge badge-muted">avg ${a.stats.avgTime}</span>
        ${a.stats.active > 0 ? `<span class="badge badge-amber">${a.stats.active} active</span>` : ''}
      </div>
    </div>`).join('');

  if (selectedAgentId) renderAgentDetail(selectedAgentId);
}

function selectAgent(id) {
  selectedAgentId = selectedAgentId === id ? null : id;

  document.querySelectorAll('.agent-card').forEach(c => c.classList.remove('selected'));
  if (selectedAgentId) {
    const cards = document.querySelectorAll('.agent-card');
    const idx = AGENT_DATA.findIndex(a => a.id === id);
    if (idx >= 0) cards[idx].classList.add('selected');
    renderAgentDetail(id);
  } else {
    const detail = document.getElementById('agentDetail');
    if (detail) detail.style.display = 'none';
  }
}

function renderAgentDetail(id) {
  const a = AGENT_DATA.find(x => x.id === id);
  if (!a) return;
  const detail = document.getElementById('agentDetail');
  if (!detail) return;

  detail.style.display = 'block';
  detail.innerHTML = `
    <div class="agent-detail" style="border-color:${a.color};">
      <div style="display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:16px;">
        <div>
          <div style="font-family:var(--font-mono);font-size:0.6rem;color:var(--text-muted);letter-spacing:1px;">AGENT ${a.num}</div>
          <div style="font-size:1.1rem;font-weight:800;color:var(--text-bright);margin:4px 0 2px;">${a.name}</div>
          <div style="font-family:var(--font-mono);font-size:0.65rem;color:${a.color};">${a.alias}</div>
        </div>
        <span class="badge" style="background:${a.colorDim};color:${a.color};">${a.statusLabel}</span>
      </div>

      <div class="detail-row">
        <div class="detail-label">Mission</div>
        <div class="detail-value">${a.detail}</div>
      </div>
      <div class="detail-row">
        <div class="detail-label">Trigger</div>
        <div class="detail-value">${a.trigger}</div>
      </div>
      <div class="detail-row">
        <div class="detail-label">Detects</div>
        <div class="detail-value">${a.detects}</div>
      </div>
      <div class="detail-row">
        <div class="detail-label">Action</div>
        <div class="detail-value">${a.action}</div>
      </div>
      <div class="detail-row">
        <div class="detail-label">Outputs</div>
        <div class="detail-value">
          <ul style="padding-left:16px;margin:0;">
            ${a.outputs.map(o => `<li>${o}</li>`).join('')}
          </ul>
        </div>
      </div>

      <div style="display:flex;gap:8px;margin-top:16px;">
        <div class="stat-card" style="flex:1;padding:12px;">
          <div class="stat-label">Total Resolved</div>
          <div class="stat-value" style="color:${a.color};">${a.stats.resolved}</div>
        </div>
        <div class="stat-card" style="flex:1;padding:12px;">
          <div class="stat-label">Avg Resolution</div>
          <div class="stat-value" style="color:${a.color};">${a.stats.avgTime}</div>
        </div>
        <div class="stat-card" style="flex:1;padding:12px;">
          <div class="stat-label">Currently Active</div>
          <div class="stat-value" style="color:${a.stats.active > 0 ? 'var(--amber)' : 'var(--text-muted)'};">${a.stats.active}</div>
        </div>
      </div>

      <div style="text-align:right;margin-top:12px;">
        <button class="btn btn-ghost btn-sm" onclick="selectAgent('${a.id}')">Close &times;</button>
      </div>
    </div>`;
}

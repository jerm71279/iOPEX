/**
 * HELIX — Audit Log
 */

const AUDIT_ENTRIES = [
  { time: '14:32:09', agent: 'RESOLUTION', agentColor: 'var(--green)', action: 'Customer Hub: DoB field updated', delta: 'DoB: NULL → 10/9/1981', dest: 'Customer Hub', ref: 'BB-0042' },
  { time: '14:32:07', agent: 'RESOLUTION', agentColor: 'var(--green)', action: 'SAF: DoB field updated — consistency confirmed', delta: 'DoB: NULL → 10/9/1981', dest: 'SAF', ref: 'BB-0042' },
  { time: '14:32:07', agent: 'RPA', agentColor: 'var(--purple)', action: 'Application layer: stale auth tokens cleared, login restored', delta: 'auth_state: FAILED → ACTIVE', dest: 'App Layer', ref: 'BB-0042' },
  { time: '14:32:04', agent: 'RESOLUTION', agentColor: 'var(--green)', action: 'Resolution Agent activated — executing targeted field fix', delta: 'Target: SAF, Customer Hub', dest: 'Multi', ref: 'BB-0042' },
  { time: '14:31:58', agent: 'OBSERVER', agentColor: 'var(--cyan)', action: 'Cascade stall intercepted — delta payload captured and queued', delta: 'DoB: NULL → 10/9/1981', dest: 'Resolution Agent', ref: 'BB-0042' },
  { time: '14:31:52', agent: 'SYSTEM', agentColor: 'var(--text-muted)', action: 'One View: DoB update applied — cascade step 1 complete', delta: 'DoB: NULL → 10/9/1981', dest: 'One View', ref: 'BB-0042' },
  { time: '14:31:51', agent: 'SYSTEM', agentColor: 'var(--text-muted)', action: 'DnP SQL trigger: identity update initiated — cascade started', delta: 'DoB update', dest: 'Cascade', ref: 'BB-0042' },
  { time: '14:28:14', agent: 'HEALING', agentColor: 'var(--bt)', action: 'System restoration complete — all 5 domains verified consistent', delta: 'Full consistency check', dest: 'All Domains', ref: 'BH-0117' },
  { time: '14:25:03', agent: 'RPA', agentColor: 'var(--purple)', action: 'Account recovery executed — user login access restored', delta: 'auth_state: FAILED → ACTIVE', dest: 'App Layer', ref: 'BH-0117' },
  { time: '14:22:51', agent: 'RESOLUTION', agentColor: 'var(--green)', action: 'Customer Hub: SIM sequence updated', delta: 'sim_seq: SEQ-4470-A → SEQ-4471-A', dest: 'Customer Hub', ref: 'BH-0117' },
  { time: '14:22:49', agent: 'RESOLUTION', agentColor: 'var(--green)', action: 'SAF: SIM sequence updated', delta: 'sim_seq: SEQ-4470-A → SEQ-4471-A', dest: 'SAF', ref: 'BH-0117' },
  { time: '14:22:44', agent: 'OBSERVER', agentColor: 'var(--cyan)', action: 'Partial cascade detected — SIM sequence stall in SAF + Customer Hub', delta: 'sim_seq: SEQ-4470-A → SEQ-4471-A', dest: 'Resolution Agent', ref: 'BH-0117' },
  { time: '14:15:09', agent: 'HEURISTIC', agentColor: 'var(--teal)', action: 'Scheduled scan: all domains consistent — no action required', delta: '—', dest: 'Audit Log', ref: 'SCAN' },
  { time: '14:00:09', agent: 'HEURISTIC', agentColor: 'var(--teal)', action: 'Scheduled scan: 1 stale field detected — Resolution Agent triggered', delta: 'addr: old → new', dest: 'Resolution Agent', ref: 'SCAN' },
  { time: '13:47:22', agent: 'HEALING', agentColor: 'var(--bt)', action: 'Full restore completed — 3 fields corrected across 2 domains', delta: 'Multi-field correction', dest: 'SAF + Hub', ref: 'HEAL-023' },
];

function renderAuditLog() {
  const el = document.getElementById('auditContent');
  if (!el) return;

  el.innerHTML = `
    <div class="stats-grid" style="margin-bottom:20px;">
      <div class="stat-card"><div class="stat-label">Total Entries</div><div class="stat-value" style="color:var(--bt);">${AUDIT_ENTRIES.length}</div><div class="stat-sub">This session</div></div>
      <div class="stat-card"><div class="stat-label">Fields Corrected</div><div class="stat-value" style="color:var(--green);">47</div><div class="stat-sub">Zero manual</div></div>
      <div class="stat-card"><div class="stat-label">Domains Touched</div><div class="stat-value" style="color:var(--cyan);">5</div></div>
      <div class="stat-card"><div class="stat-label">Log Integrity</div><div class="stat-value" style="color:var(--green);">SHA-256</div><div class="stat-sub">Hash chain active</div></div>
    </div>

    <div class="panel">
      <div class="panel-header">
        <div class="panel-title">Action Log</div>
        <div style="display:flex;gap:8px;align-items:center;">
          <select id="auditFilter" onchange="filterAuditLog(this.value)" style="background:var(--bg-surface);color:var(--text-standard);border:1px solid var(--border);border-radius:4px;padding:4px 8px;font-size:0.72rem;">
            <option value="all">All Agents</option>
            <option value="OBSERVER">Observability</option>
            <option value="RESOLUTION">Resolution</option>
            <option value="HEALING">Healing</option>
            <option value="RPA">RPA</option>
            <option value="HEURISTIC">Heuristic Monitor</option>
            <option value="SYSTEM">System</option>
          </select>
          <span class="badge badge-muted">${AUDIT_ENTRIES.length} entries</span>
        </div>
      </div>
      <div style="overflow-x:auto;">
        <table style="width:100%;border-collapse:collapse;" id="auditTable">
          <thead>
            <tr>
              <th style="text-align:left;padding:10px 12px;font-family:var(--font-mono);font-size:0.55rem;color:var(--text-muted);letter-spacing:1.5px;text-transform:uppercase;border-bottom:1px solid var(--border);background:var(--bg-surface);">Time</th>
              <th style="text-align:left;padding:10px 12px;font-family:var(--font-mono);font-size:0.55rem;color:var(--text-muted);letter-spacing:1.5px;text-transform:uppercase;border-bottom:1px solid var(--border);background:var(--bg-surface);">Agent</th>
              <th style="text-align:left;padding:10px 12px;font-family:var(--font-mono);font-size:0.55rem;color:var(--text-muted);letter-spacing:1.5px;text-transform:uppercase;border-bottom:1px solid var(--border);background:var(--bg-surface);">Action</th>
              <th style="text-align:left;padding:10px 12px;font-family:var(--font-mono);font-size:0.55rem;color:var(--text-muted);letter-spacing:1.5px;text-transform:uppercase;border-bottom:1px solid var(--border);background:var(--bg-surface);">Data Delta</th>
              <th style="text-align:left;padding:10px 12px;font-family:var(--font-mono);font-size:0.55rem;color:var(--text-muted);letter-spacing:1.5px;text-transform:uppercase;border-bottom:1px solid var(--border);background:var(--bg-surface);">Ref</th>
            </tr>
          </thead>
          <tbody id="auditTableBody">
            ${buildAuditRows(AUDIT_ENTRIES)}
          </tbody>
        </table>
      </div>
    </div>
  `;
}

function buildAuditRows(entries) {
  return entries.map(e => `
    <tr style="transition:var(--transition);" onmouseover="this.style.background='var(--bg-card-hover)'" onmouseout="this.style.background=''">
      <td style="padding:9px 12px;border-bottom:1px solid rgba(30,48,80,0.35);font-family:var(--font-mono);font-size:0.62rem;color:var(--text-muted);">${e.time}</td>
      <td style="padding:9px 12px;border-bottom:1px solid rgba(30,48,80,0.35);"><span style="font-family:var(--font-mono);font-size:0.58rem;font-weight:700;color:${e.agentColor};">${e.agent}</span></td>
      <td style="padding:9px 12px;border-bottom:1px solid rgba(30,48,80,0.35);font-size:0.72rem;color:var(--text-standard);">${e.action}</td>
      <td style="padding:9px 12px;border-bottom:1px solid rgba(30,48,80,0.35);"><span style="font-family:var(--font-mono);font-size:0.6rem;color:var(--green);background:var(--bg-surface);border:1px solid var(--border);border-radius:4px;padding:2px 6px;">${e.delta}</span></td>
      <td style="padding:9px 12px;border-bottom:1px solid rgba(30,48,80,0.35);font-family:var(--font-mono);font-size:0.62rem;color:var(--text-muted);">${e.ref}</td>
    </tr>`).join('');
}

function filterAuditLog(agent) {
  const entries = agent === 'all' ? AUDIT_ENTRIES : AUDIT_ENTRIES.filter(e => e.agent === agent);
  const tbody = document.getElementById('auditTableBody');
  if (tbody) tbody.innerHTML = buildAuditRows(entries);
}

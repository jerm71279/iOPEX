/**
 * HELIX — Safety Nets (3 legacy safeguards)
 */

const SAFEGUARDS = [
  {
    id: 'heuristic',
    num: '01',
    name: 'Heuristic Monitoring with Intentional Delay',
    status: 'active',
    color: 'var(--teal)',
    colorDim: 'var(--teal-dim)',
    badgeClass: 'badge-teal',
    statusLabel: 'ACTIVE',
    desc: 'Automated consistency checks run on a scheduled basis, with a programmed delay built in to allow standard asynchronous processing to complete before raising an alert.',
    purpose: 'Catches cascade failures that the real-time AI layer may have missed, or that occur outside of monitored trigger pathways. Acts as a safety net for batch-originated inconsistencies.',
    config: [
      { label: 'Check frequency',   value: 'Every 15 minutes' },
      { label: 'Intentional delay', value: '90 seconds post-trigger before asserting failure' },
      { label: 'Scope',             value: 'All 5 domains — field-level consistency scan' },
      { label: 'On failure',        value: 'Triggers Resolution Agent + logs to audit' },
    ],
    lastTriggered: '14:15:00',
    triggersToday: 2,
  },
  {
    id: 'complaint',
    num: '02',
    name: 'Customer Complaint Triggers',
    status: 'active',
    color: 'var(--amber)',
    colorDim: 'var(--amber-dim)',
    badgeClass: 'badge-amber',
    statusLabel: 'ACTIVE',
    desc: 'External signals from customers — such as "unable to login" reports — act as a secondary trigger to force immediate identity-profile alignment across all systems.',
    purpose: 'Provides a human-in-the-loop signal for failure cases that no automated monitoring catches. A customer experiencing an issue is a ground-truth signal that data inconsistency has reached user-visible impact.',
    config: [
      { label: 'Signal sources',      value: 'BT contact centre, MyBT app error reports, web chat' },
      { label: 'Trigger condition',   value: '"unable to login" or "account not found" complaint' },
      { label: 'Response',            value: 'Immediate identity-profile alignment scan — RPA Automation activated' },
      { label: 'Resolution target',   value: '< 30 seconds from complaint receipt to backend fix' },
    ],
    lastTriggered: '11:42:18',
    triggersToday: 0,
  },
  {
    id: 'audit',
    num: '03',
    name: 'Auditability — Full Action Logging',
    status: 'active',
    color: 'var(--blue)',
    colorDim: 'var(--blue-dim)',
    badgeClass: 'badge-blue',
    statusLabel: 'ACTIVE',
    desc: 'The Observability Agent creates a detailed log entry for every action taken — documenting the data delta, the destination repositories, the agent responsible, and the timestamp.',
    purpose: 'Provides a transparent, forensic audit trail for every healing event. Supports regulatory compliance, root cause analysis, and confidence in the autonomous system\'s behaviour.',
    config: [
      { label: 'Log format',         value: 'Structured JSON — field, old value, new value, target system, agent, timestamp' },
      { label: 'Retention',          value: '90 days — queryable via Audit Log page' },
      { label: 'Integrity',          value: 'SHA-256 hash chain — tamper-evident log sequence' },
      { label: 'Coverage',           value: '100% of all agent actions — no silent operations' },
    ],
    lastTriggered: '14:32:09',
    triggersToday: 47,
  },
];

function renderSafeguards() {
  const el = document.getElementById('safeguardsContent');
  if (!el) return;

  el.innerHTML = `
    <div class="callout bt" style="margin-bottom:20px;">
      <div class="callout-title">Legacy Safeguards — Preserved Alongside the AI Layer</div>
      <p>These three mechanisms existed before the AI intelligence layer was introduced. They are kept active as defence-in-depth — providing a safety net for edge cases and maintaining auditability of all autonomous operations.</p>
    </div>

    ${SAFEGUARDS.map(s => `
      <div class="panel" style="margin-bottom:20px;">
        <div class="panel-header">
          <div style="display:flex;align-items:center;gap:10px;">
            <div style="font-family:var(--font-mono);font-size:0.65rem;font-weight:700;color:${s.color};">${s.num}</div>
            <div class="panel-title">${s.name}</div>
          </div>
          <span class="badge ${s.badgeClass}">${s.statusLabel}</span>
        </div>
        <div class="panel-body">
          <p style="font-size:0.78rem;color:var(--text-standard);line-height:1.7;margin-bottom:12px;">${s.desc}</p>
          <div class="callout teal" style="margin-bottom:14px;">
            <div class="callout-title">Why This Matters</div>
            <p>${s.purpose}</p>
          </div>
          <div class="section-label">Configuration</div>
          ${s.config.map(c => `
            <div class="field-row">
              <div class="field-name">${c.label}</div>
              <div style="flex:1;font-size:0.72rem;color:var(--text-standard);">${c.value}</div>
            </div>`).join('')}
          <div style="display:flex;gap:12px;margin-top:14px;">
            <div class="stat-card" style="flex:1;padding:12px;">
              <div class="stat-label">Last Triggered</div>
              <div style="font-family:var(--font-mono);font-size:0.88rem;font-weight:700;color:${s.color};margin-top:4px;">${s.lastTriggered}</div>
            </div>
            <div class="stat-card" style="flex:1;padding:12px;">
              <div class="stat-label">Triggers Today</div>
              <div style="font-family:var(--font-mono);font-size:1.4rem;font-weight:800;color:${s.triggersToday > 0 ? s.color : 'var(--text-muted)'};margin-top:4px;">${s.triggersToday}</div>
            </div>
          </div>
        </div>
      </div>`).join('')}
  `;
}

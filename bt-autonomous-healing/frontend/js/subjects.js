/**
 * HELIX — Test Subjects
 */

const SUBJECTS = [
  {
    id: 'buck',
    name: 'Buck Barrow',
    ref: 'BB-0042',
    type: 'Identity Update Validation',
    color: 'var(--bt)',
    colorDim: 'var(--bt-dim)',
    badgeClass: 'badge-bt',
    scenario: 'Date of Birth update in DnP SQL — validate cross-system consistency',
    status: 'healing',
    statusLabel: 'HEALING IN PROGRESS',
    domains: [
      { name: 'DnP SQL',        field: 'DoB',                    value: '10/9/1981',  status: 'correct',  },
      { name: 'One View',       field: 'DoB',                    value: '10/9/1981',  status: 'correct',  },
      { name: 'SAF',            field: 'DoB',                    value: 'NULL → 10/9/1981', status: 'healing', },
      { name: 'Customer Hub',   field: 'DoB',                    value: 'NULL → 10/9/1981', status: 'healing', },
      { name: 'Excalibur',      field: 'N/A (no DoB field)',     value: '—',          status: 'ok',       },
    ],
    history: [
      { time: '14:31:51', event: 'Trigger fired — DoB update in DnP SQL' },
      { time: '14:31:52', event: 'One View updated successfully' },
      { time: '14:31:58', event: 'Cascade stall detected — SAF + Customer Hub not reached' },
      { time: '14:31:58', event: 'Observability Agent intercepted — delta captured' },
      { time: '14:32:04', event: 'Resolution Agent executing fix → SAF' },
      { time: '14:32:07', event: 'Resolution Agent executing fix → Customer Hub' },
    ],
  },
  {
    id: 'barbara',
    name: 'Barbara Hershey',
    ref: 'BH-0117',
    type: 'Mobile SIM Sequence Validation',
    color: 'var(--cyan)',
    colorDim: 'var(--cyan-dim)',
    badgeClass: 'badge-cyan',
    scenario: 'Mobile SIM sequence update — validate Excalibur + Customer Hub consistency',
    status: 'healthy',
    statusLabel: 'CONSISTENT',
    domains: [
      { name: 'DnP SQL',        field: 'SIM Sequence',  value: 'SEQ-4471-A',   status: 'correct', },
      { name: 'One View',       field: 'N/A',           value: '—',            status: 'ok', },
      { name: 'SAF',            field: 'SIM Sequence',  value: 'SEQ-4471-A',   status: 'correct', },
      { name: 'Customer Hub',   field: 'SIM Sequence',  value: 'SEQ-4471-A',   status: 'correct', },
      { name: 'Excalibur',      field: 'Mobile Record', value: 'SEQ-4471-A',   status: 'correct', },
    ],
    history: [
      { time: '12:14:02', event: 'SIM sequence update triggered in DnP SQL' },
      { time: '12:14:04', event: 'Cascade completed to SAF and Customer Hub — all confirmed' },
      { time: '12:14:09', event: 'Excalibur sync confirmed via BACS pathway' },
      { time: '12:14:09', event: 'Healing Agent: system consistency verified — no intervention required' },
    ],
  },
];

function renderSubjects() {
  const el = document.getElementById('subjectsContent');
  if (!el) return;

  el.innerHTML = `
    <div class="callout teal" style="margin-bottom:20px;">
      <div class="callout-title">Validation Targets</div>
      <p>These subjects are mapped for cross-system consistency verification. Each represents a known scenario type used to validate that the AI healing layer correctly resolves the full range of cascade failure patterns.</p>
    </div>

    ${SUBJECTS.map(s => `
      <div class="panel" style="margin-bottom:20px;">
        <div class="panel-header">
          <div style="display:flex;align-items:center;gap:10px;">
            <div class="health-dot ${s.status === 'healthy' ? 'dot-green' : s.status === 'healing' ? 'dot-amber' : 'dot-red'}"></div>
            <div>
              <div class="panel-title">${s.name} <span style="font-family:var(--font-mono);font-size:0.62rem;color:var(--text-muted);">${s.ref}</span></div>
              <div style="font-size:0.65rem;color:var(--text-muted);margin-top:2px;">${s.type}</div>
            </div>
          </div>
          <span class="badge ${s.badgeClass}">${s.statusLabel}</span>
        </div>
        <div class="panel-body">
          <div style="font-size:0.75rem;color:var(--text-muted);margin-bottom:14px;">${s.scenario}</div>

          <div class="section-label">Cross-System Field Consistency</div>
          ${s.domains.map(d => {
            const statusColor = d.status === 'correct' || d.status === 'ok' ? 'var(--green)' : d.status === 'healing' ? 'var(--amber)' : 'var(--red)';
            const statusLabel = d.status === 'correct' ? '✓ CORRECT' : d.status === 'ok' ? '— N/A' : d.status === 'healing' ? '⟳ HEALING' : '✗ STALE';
            return `<div class="field-row">
              <div class="field-name">${d.name}</div>
              <div style="flex:1;font-size:0.72rem;color:var(--text-standard);">${d.field}</div>
              <div style="font-family:var(--font-mono);font-size:0.68rem;color:${statusColor};">${d.value}</div>
              <div style="font-family:var(--font-mono);font-size:0.58rem;color:${statusColor};min-width:80px;text-align:right;">${statusLabel}</div>
            </div>`;
          }).join('')}

          <div class="section-label" style="margin-top:16px;">Event History</div>
          ${s.history.map(h => `
            <div class="audit-row">
              <div class="audit-time">${h.time}</div>
              <div class="audit-action">${h.event}</div>
            </div>`).join('')}
        </div>
      </div>`).join('')}
  `;
}

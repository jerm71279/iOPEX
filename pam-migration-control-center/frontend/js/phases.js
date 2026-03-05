/**
 * Phase Explorer page renderer.
 */

let expandedPhases = {};

async function renderPhaseExplorer() {
  const phases = await API.get('/phases');
  document.getElementById('phaseCards').innerHTML = phases.map(p => {
    const isOpen = expandedPhases[p.id] ? 'open' : '';
    const riskColor = { low: 'green', medium: 'amber', high: 'red' }[p.risk] || 'text-muted';
    return `
    <div class="phase-card ${isOpen}" id="pc-${p.id}">
      <div class="phase-card-header" onclick="togglePhase('${p.id}')">
        <div class="phase-num" style="background:var(--${riskColor}-dim,rgba(100,116,139,0.15));color:var(--${riskColor},var(--text-muted))">${p.id.toUpperCase()}</div>
        <div class="phase-card-title">${p.name}</div>
        <div class="phase-card-weeks">W${p.weeks}</div>
        <span class="badge ${riskBadgeClass(p.risk)}">${p.risk.toUpperCase()}</span>
        <div class="phase-expand">&#x25B6;</div>
      </div>
      <div class="phase-card-body">
        <div class="phase-card-content">
          <p style="font-size:0.78rem;color:var(--text-standard);margin-bottom:12px">${p.summary}</p>

          ${p.agents.length ? `
          <div class="section-label">Agents</div>
          <div style="display:flex;gap:6px;flex-wrap:wrap;margin-bottom:12px">
            ${p.agents.map(a => `
              <span class="badge ${a.status === 'complete' ? 'badge-green' : a.status === 'active' ? 'badge-amber' : 'badge-muted'}"
                    style="cursor:pointer" onclick="jumpToAgent('${a.num.replace('0','').replace('DX-0','dx')}')">${a.num} ${a.name}</span>
            `).join('')}
          </div>` : ''}

          <div class="section-label">Activities</div>
          ${p.activities.map(a => `<div class="activity-item">${a}</div>`).join('')}

          <div class="section-label" style="margin-top:14px">Deliverables</div>
          ${p.deliverables.map(d => `
            <div class="deliverable-item" onclick="drillDeliverable('${p.id}','${d.key}')">
              <span class="badge badge-teal" style="font-size:0.5rem">&#x25A0;</span>
              ${d.label} <span style="color:var(--text-muted);font-size:0.62rem">(Agent ${d.agent})</span>
            </div>
          `).join('')}

          ${p.gates.length ? `
          <div class="section-label" style="margin-top:14px">Gates</div>
          <div style="display:flex;gap:6px;flex-wrap:wrap">
            ${p.gates.map(g => `<span class="badge badge-amber">${g.toUpperCase()}</span>`).join('')}
          </div>` : ''}
        </div>
      </div>
    </div>`;
  }).join('');
}

function togglePhase(phaseId, forceOpen) {
  const card = document.getElementById('pc-' + phaseId);
  if (!card) return;
  if (forceOpen) {
    card.classList.add('open');
    expandedPhases[phaseId] = true;
  } else {
    card.classList.toggle('open');
    expandedPhases[phaseId] = card.classList.contains('open');
  }
  if (expandedPhases[phaseId]) {
    card.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
  }
}

function expandAllPhases() {
  document.querySelectorAll('.phase-card').forEach(c => {
    c.classList.add('open');
    const id = c.id.replace('pc-', '');
    expandedPhases[id] = true;
  });
}

function collapseAllPhases() {
  document.querySelectorAll('.phase-card').forEach(c => c.classList.remove('open'));
  expandedPhases = {};
}

async function drillDeliverable(phaseId, key) {
  const data = await API.get(`/deliverables/${phaseId}/${key}`);
  if (data && data.data) {
    const rendered = renderDeliverable(data.name, data.data, data.format, phaseId);
    openDrill(
      `${data.name} (Agent ${data.agent})`,
      `<div style="margin-bottom:14px;display:flex;gap:6px">
        <span class="badge badge-muted">${phaseId.toUpperCase()}</span>
        <span class="badge badge-teal">${data.format || 'JSON'}</span>
        <span class="badge badge-cyan">Agent ${data.agent}</span>
      </div>
      ${rendered}`
    );
  }
}

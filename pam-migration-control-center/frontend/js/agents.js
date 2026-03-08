/**
 * Agent Orchestration page renderer.
 */

let selectedAgentId = null;

async function renderAgentGrid() {
  const agents = await API.get('/agents');
  document.getElementById('agentGrid').innerHTML = agents.map(a => {
    const sel = a.id === selectedAgentId ? 'selected' : '';
    return `
    <div class="agent-card status-${a.status} ${sel}" onclick="selectAgent('${a.id}')">
      <div style="display:flex;justify-content:space-between;align-items:center">
        <div class="agent-num">AGENT ${a.num}</div>
        <div class="health-dot ${statusDotClass(a.status)}"></div>
      </div>
      <div class="agent-name">${a.name}</div>
      <div style="display:flex;gap:4px;flex-wrap:wrap;margin-bottom:6px">
        ${a.phases.map(p => `<span class="badge badge-muted">${p.toUpperCase()}</span>`).join('')}
        <span class="badge badge-cyan">${a.weeks}</span>
      </div>
      <div class="agent-desc">${a.desc.substring(0, 120)}${a.desc.length > 120 ? '...' : ''}</div>
    </div>`;
  }).join('');
}

async function selectAgent(agentId) {
  selectedAgentId = agentId;
  const a = await API.get(`/agents/${agentId}`);
  if (a.error) return;

  const detailEl = document.getElementById('agentDetail');
  detailEl.style.display = 'block';
  detailEl.innerHTML = `
    <div class="agent-detail">
      <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:12px">
        <div>
          <span class="agent-num" style="font-size:0.7rem">AGENT ${a.num}</span>
          <span style="font-size:1.1rem;font-weight:700;color:var(--text-bright);margin-left:10px">${a.name}</span>
        </div>
        <div>
          <span class="badge ${statusDotClass(a.status).replace('dot-','badge-')}">${a.status.toUpperCase()}</span>
          <button class="overlay-close" onclick="closeAgentDetail()" style="position:static;font-size:1rem;margin-left:10px">&times;</button>
        </div>
      </div>
      <div class="detail-row">
        <div class="detail-label">Description</div>
        <div class="detail-value">${a.desc}</div>
      </div>
      <div class="detail-row">
        <div class="detail-label">Phases</div>
        <div class="detail-value">${(a.phases || []).map(p => `<span class="badge badge-muted" style="cursor:pointer" onclick="jumpToPhase('${p}')">${p.toUpperCase()}</span>`).join(' ')}</div>
      </div>
      <div class="detail-row">
        <div class="detail-label">Weeks</div>
        <div class="detail-value">${a.weeks}</div>
      </div>
      <div class="detail-row">
        <div class="detail-label">Inputs</div>
        <div class="detail-value">${(a.inputs || []).map(i => `<div style="margin-bottom:2px">&#x2022; ${i}</div>`).join('')}</div>
      </div>
      <div class="detail-row">
        <div class="detail-label">Outputs</div>
        <div class="detail-value">${(a.outputs || []).map(o => `<div style="margin-bottom:2px">&#x2022; ${o}</div>`).join('')}</div>
      </div>
      ${a.api_calls && a.api_calls.length ? `
      <div class="detail-row">
        <div class="detail-label">API Calls</div>
        <div class="detail-value" style="font-family:var(--font-mono);font-size:0.68rem">${a.api_calls.map(c => `<div style="margin-bottom:2px;color:var(--cyan)">${c}</div>`).join('')}</div>
      </div>` : ''}
      ${a.blocked_by && a.blocked_by.length ? `
      <div class="detail-row">
        <div class="detail-label">Blocked By</div>
        <div class="detail-value">${a.blocked_by.map(b => `<span class="badge badge-red" style="cursor:pointer" onclick="selectAgent('${b}')">Agent ${b}</span>`).join(' ')}</div>
      </div>` : ''}
      ${a.gates && a.gates.length ? `
      <div class="detail-row">
        <div class="detail-label">Gates</div>
        <div class="detail-value">${a.gates.map(g => `<span class="badge badge-amber">${g.toUpperCase()}</span>`).join(' ')}</div>
      </div>` : ''}
      <div id="agentMLSection"></div>
      <div style="margin-top:14px">
        <button class="btn btn-sm btn-teal" onclick="viewAgentOutput('${agentId}')">View Output</button>
      </div>
    </div>
  `;

  // Inject ML sections for agents 04 and 12
  if (a.num === '04') {
    renderAgent04MLDetail().then(html => {
      const mlEl = document.getElementById('agentMLSection');
      if (mlEl) mlEl.innerHTML = html;
    });
  } else if (a.num === '12') {
    renderAgent12MLDetail().then(html => {
      const mlEl = document.getElementById('agentMLSection');
      if (mlEl) mlEl.innerHTML = html;
    });
  }

  // Re-render grid to update selection
  renderAgentGrid();
  detailEl.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
}

function closeAgentDetail() {
  selectedAgentId = null;
  document.getElementById('agentDetail').style.display = 'none';
  renderAgentGrid();
}

async function viewAgentOutput(agentId) {
  const result = await API.get(`/agents/${agentId}/output`);
  if (result.message) {
    openDrill(`Agent ${result.agent_name} — Output`, `
      <div class="callout amber">
        <div class="callout-title">No Output Available</div>
        <p>${result.message}</p>
        <p style="margin-top:8px">Import test data: <code>POST /api/import/deliverables</code> with a JSON file.</p>
      </div>
    `);
  } else {
    const outputs = result.outputs.map(o => {
      const rendered = renderDeliverable(o.name, o.data, o.format, o.phase);
      return `
        <div style="margin-bottom:24px;padding-bottom:24px;border-bottom:1px solid var(--border)">
          <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:14px">
            <div style="font-weight:700;font-size:0.88rem;color:var(--text-bright)">${o.name}</div>
            <div style="display:flex;gap:6px">
              <span class="badge badge-muted">${o.phase.toUpperCase()}</span>
              <span class="badge badge-teal">${o.format}</span>
            </div>
          </div>
          ${rendered}
        </div>
      `;
    }).join('');
    openDrill(`Agent ${result.agent_name} — Output`, outputs);
  }
}

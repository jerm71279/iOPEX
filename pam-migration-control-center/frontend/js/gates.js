/**
 * Gate Tracker page renderer + approval simulation.
 * Enhanced with descriptions, inputs/unlocks, and option-specific context.
 */

async function renderGateTracker() {
  const gates = await API.get('/gates');
  const option = API.option || 'a';

  document.getElementById('gateTimeline').innerHTML = gates.map(g => {
    const contextText = option === 'b' ? g.context_b : g.context_a;
    const contextLabel = option === 'b' ? 'CyberArk Cloud Context' : 'Delinea Context';
    const inputs = g.inputs || [];
    const unlocks = g.unlocks || '';

    return `
    <div class="gate-entry" style="display:block;padding:18px;margin-bottom:14px;">
      <div style="display:flex;gap:14px;align-items:flex-start;margin-bottom:12px">
        <div class="gate-dot ${statusDotClass(g.status)}" style="margin-top:4px"></div>
        <div style="flex:1">
          <div class="gate-name">${g.name}</div>
          <div class="gate-meta">
            <span class="badge badge-muted">${g.phase.toUpperCase()}</span>
            <span style="margin-left:6px">Week ${g.week}</span>
            <span style="margin-left:12px">Approvers: ${g.approvers.map(a => `<span class="badge badge-cyan" style="margin-left:2px">${a}</span>`).join('')}</span>
          </div>
        </div>
        ${g.status === 'active' ? `<button class="approve-btn" onclick="approveGate('${g.id}')">APPROVE</button>` : ''}
        ${g.status === 'pending' ? `<span class="badge badge-muted">PENDING</span>` : ''}
        ${g.status === 'passed' ? `<span class="badge badge-green">PASSED</span>` : ''}
      </div>

      ${g.description ? `
        <div class="callout teal" style="margin-bottom:12px">
          <div class="callout-title" style="color:var(--teal)">What Happens Here</div>
          <p>${g.description}</p>
        </div>
      ` : ''}

      ${inputs.length > 0 || unlocks ? `
        <div class="gate-context">
          ${inputs.length > 0 ? `
            <div class="gate-context-box">
              <div class="gate-context-label">Inputs (Deliverables)</div>
              ${inputs.map(inp => `
                <div class="gate-deliverable-link" onclick="viewDeliverableByName('${inp}')">
                  <span style="color:var(--teal)">&#9654;</span>
                  ${inp.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())}
                </div>
              `).join('')}
            </div>
          ` : ''}
          ${unlocks ? `
            <div class="gate-context-box">
              <div class="gate-context-label">Unlocks</div>
              <div style="font-size:0.72rem;color:var(--text-standard);line-height:1.5">${unlocks}</div>
            </div>
          ` : ''}
        </div>
      ` : ''}

      ${contextText ? `
        <div class="callout amber" style="margin-bottom:0">
          <div class="callout-title" style="color:var(--amber)">${contextLabel}</div>
          <p>${contextText}</p>
        </div>
      ` : ''}

      <div style="margin-top:12px;padding-top:12px;border-top:1px solid var(--border)">
        <div class="gate-context-label" style="margin-bottom:6px">Requirements</div>
        <div class="gate-req" style="margin-top:0">${g.requirements}</div>
      </div>
    </div>
    `;
  }).join('');
}

async function viewDeliverableByName(deliverableName) {
  // Search through all phases to find this deliverable
  const phaseIds = ['p0', 'p1', 'p2', 'p3', 'p4', 'p5', 'p6', 'p7'];
  for (const phaseId of phaseIds) {
    try {
      const deliverables = await API.get(`/deliverables/${phaseId}`);
      const match = deliverables.find(d => d.key === deliverableName);
      if (match && match.has_data) {
        const data = await API.get(`/deliverables/${phaseId}/${deliverableName}`);
        if (data && data.data) {
          const rendered = renderDeliverable(data.name, data.data, data.format, phaseId);
          openDrill(data.name, `
            <div style="margin-bottom:14px;display:flex;gap:6px">
              <span class="badge badge-muted">${phaseId.toUpperCase()}</span>
              <span class="badge badge-teal">${data.format || 'JSON'}</span>
              <span class="badge badge-cyan">Agent ${data.agent}</span>
            </div>
            ${rendered}
          `);
          return;
        }
      }
    } catch (e) {
      // Phase might not have deliverables, continue
    }
  }
  openDrill(deliverableName.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase()), `
    <div class="callout amber">
      <div class="callout-title">Deliverable Not Available</div>
      <p>The deliverable "${deliverableName.replace(/_/g, ' ')}" does not have data loaded. Import test data to populate.</p>
    </div>
  `);
}

async function approveGate(gateId) {
  const result = await API.post(`/gates/${gateId}/approve`);
  renderGateTracker();
  // Gate approval cascades agent/phase status — refresh related pages
  if (typeof renderMissionControl === 'function') renderMissionControl();
  if (result && result.activated_agents && result.activated_agents.length > 0) {
    console.log(`Gate ${gateId} activated agents: ${result.activated_agents.join(', ')}`);
  }
}

async function resetGates() {
  await API.post('/gates/reset');
  renderGateTracker();
  if (typeof renderMissionControl === 'function') renderMissionControl();
}

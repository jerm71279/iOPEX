/**
 * Gate Tracker page renderer + approval simulation.
 * Enhanced with descriptions, inputs/unlocks, and option-specific context.
 */

async function renderGateTracker() {
  const gates = await API.get('/gates');
  const option = API.option || 'a';

  document.getElementById('gateTimeline').innerHTML = gates.map(g => {
    const contextText = option === 'b' ? g.context_b : g.context_a;
    const contextLabel = option === 'c' ? 'MiniOrange Context' : option === 'b' ? 'Keeper Context' : 'Devolutions Context';
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

      ${g.sod ? `
        <div style="margin-top:12px;padding:12px 14px;background:var(--bg-surface);border:1px solid var(--border);border-left:3px solid var(--purple);border-radius:4px;">
          <div class="gate-context-label" style="color:var(--purple);margin-bottom:8px;letter-spacing:.05em;">&#x1F512; SEPARATION OF DUTIES</div>
          <div style="display:grid;grid-template-columns:1fr 1fr;gap:10px;font-size:0.67rem;line-height:1.7;margin-bottom:10px;">
            <div>
              <div style="font-size:0.58rem;font-family:var(--font-mono);color:var(--cyan);font-weight:700;margin-bottom:3px;">iOPEX — PERFORMS</div>
              <div style="color:var(--text-standard)">${g.sod.iOPEX}</div>
            </div>
            <div>
              <div style="font-size:0.58rem;font-family:var(--font-mono);color:var(--green);font-weight:700;margin-bottom:3px;">CISCO — APPROVES INDEPENDENTLY</div>
              <div style="color:var(--text-standard)">${g.sod.cisco}</div>
            </div>
          </div>
          <div style="padding:7px 10px;background:var(--red-dim);border:1px solid var(--red);border-radius:3px;font-size:0.65rem;color:var(--red);line-height:1.6;">
            <strong>&#x26D4; Cannot:</strong> ${g.sod.blocker}
          </div>
          <div style="margin-top:7px;font-size:0.64rem;color:var(--text-muted);font-style:italic;line-height:1.5;">Rule: ${g.sod.rule}</div>
        </div>
      ` : ''}

      ${contextText ? `
        <div class="callout amber" style="margin-bottom:0;margin-top:12px;">
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
  if (typeof renderMissionControl === 'function') renderMissionControl();

  // Show cascade notification
  if (result && result.status === 'approved') {
    // Fetch agent names for activated agents
    let agentLines = '';
    if (result.activated_agents && result.activated_agents.length > 0) {
      const agents = await API.get('/agents');
      const agentMap = {};
      agents.forEach(a => { agentMap[a.id] = a; });

      agentLines = result.activated_agents.map(aid => {
        const a = agentMap[aid];
        const label = a ? `Agent ${a.num} — ${a.name}` : `Agent ${aid}`;
        return `
          <div class="toast-cascade-item">
            <div class="toast-cascade-dot activated"></div>
            <div class="toast-cascade-label">Activated</div>
            <div class="toast-cascade-value" onclick="showPage('agents');setTimeout(()=>selectAgent('${aid}'),200)">${label}</div>
          </div>`;
      }).join('');
    }

    // Phase unlocked
    const phases = result.phases_unlocked || [];
    const newPhase = phases.length > 0 ? phases[phases.length - 1] : null;
    const phaseLine = newPhase ? `
      <div class="toast-cascade-item">
        <div class="toast-cascade-dot unlocked"></div>
        <div class="toast-cascade-label">Unlocked</div>
        <div class="toast-cascade-value" onclick="showPage('phases')">${newPhase.toUpperCase()} Phase</div>
      </div>` : '';

    // Next gate
    const nextLine = result.next_gate ? `
      <div class="toast-cascade-item">
        <div class="toast-cascade-dot next-gate"></div>
        <div class="toast-cascade-label">Next Gate</div>
        <div class="toast-cascade-value">${result.next_gate.toUpperCase()}</div>
      </div>` : '';

    const hasContent = agentLines || phaseLine || nextLine;

    showToast(`
      <div class="toast-header">
        <div class="toast-icon success">&#10003;</div>
        <div class="toast-title">${gateId.toUpperCase()} Approved</div>
        <button class="toast-close">&times;</button>
      </div>
      <div class="toast-body">
        ${hasContent ? `${agentLines}${phaseLine}${nextLine}` :
          '<div style="color:var(--text-muted)">Gate passed — no pending agents to activate at this stage.</div>'}
      </div>
    `, 10000);
  }
}

async function resetGates() {
  await API.post('/gates/reset');
  renderGateTracker();
  if (typeof renderMissionControl === 'function') renderMissionControl();
  showToast(`
    <div class="toast-header">
      <div class="toast-icon success">&#8635;</div>
      <div class="toast-title">State Reset</div>
      <button class="toast-close">&times;</button>
    </div>
    <div class="toast-body">
      All agents, gates, and phases reset to mid-migration snapshot (P0-P2 complete, P3 active).
    </div>
  `, 5000);
}

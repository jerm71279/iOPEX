/**
 * Gate Tracker page renderer + approval simulation.
 */

async function renderGateTracker() {
  const gates = await API.get('/gates');

  document.getElementById('gateTimeline').innerHTML = gates.map(g => `
    <div class="gate-entry">
      <div class="gate-dot ${statusDotClass(g.status)}"></div>
      <div class="gate-info">
        <div class="gate-name">${g.name}</div>
        <div class="gate-meta">
          <span class="badge badge-muted">${g.phase.toUpperCase()}</span>
          <span style="margin-left:6px">Week ${g.week}</span>
          <span style="margin-left:12px">Approvers: ${g.approvers.map(a => `<span class="badge badge-cyan" style="margin-left:2px">${a}</span>`).join('')}</span>
        </div>
        <div class="gate-req">${g.requirements}</div>
      </div>
      ${g.status === 'active' ? `<button class="approve-btn" onclick="approveGate('${g.id}')">APPROVE</button>` : ''}
      ${g.status === 'pending' ? `<span class="badge badge-muted">PENDING</span>` : ''}
      ${g.status === 'passed' ? `<span class="badge badge-green">PASSED</span>` : ''}
    </div>
  `).join('');
}

async function approveGate(gateId) {
  await API.post(`/gates/${gateId}/approve`);
  renderGateTracker();
  // Also update mission control if visible
  if (currentPage === 'mission') renderMissionControl();
}

async function resetGates() {
  await API.post('/gates/reset');
  renderGateTracker();
}

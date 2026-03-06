/**
 * App core — page switching, option toggle, initialization.
 */

let currentPage = 'mission';

function showPage(pageId, btn) {
  document.querySelectorAll('.page').forEach(p => p.classList.remove('active'));
  document.querySelectorAll('.nav-link').forEach(n => n.classList.remove('active'));
  document.getElementById('page-' + pageId).classList.add('active');
  if (btn) btn.classList.add('active');
  currentPage = pageId;

  // Render page content on switch
  switch (pageId) {
    case 'mission': renderMissionControl(); break;
    case 'phases': renderPhaseExplorer(); break;
    case 'agents': renderAgentGrid(); break;
    case 'waves': renderWaves(); break;
    case 'gates': renderGateTracker(); break;
    case 'yellow': renderYellowCheckpoints(); break;
    case 'compare': renderComparison(); break;
    case 'disclaimer': renderDisclaimer(); break;
  }
}

function switchOption(opt) {
  API.setOption(opt);
  document.querySelectorAll('.option-btn').forEach(b => b.classList.remove('active'));
  document.getElementById('opt-' + opt).classList.add('active');

  const ind = document.getElementById('optionIndicator');
  if (opt === 'a') {
    ind.textContent = 'DELINEA: SECRET SERVER + STRONGDM';
    ind.style.background = 'var(--blue-dim)';
    ind.style.color = 'var(--blue)';
  } else {
    ind.textContent = 'CYBERARK CLOUD: PRIVILEGE CLOUD';
    ind.style.background = 'var(--green-dim)';
    ind.style.color = 'var(--green)';
  }

  // Update week plan labels
  const weekLabel = document.getElementById('weekPlanLabel');
  const missionSub = document.getElementById('missionSubtitle');
  if (weekLabel) weekLabel.textContent = opt === 'a' ? '80-WEEK PLAN' : '50-WEEK PLAN';
  if (missionSub) missionSub.textContent = opt === 'a'
    ? '80-Week PAM Migration — Real-Time Dashboard'
    : '50-Week PAM Migration — Real-Time Dashboard';

  // Re-render current page with new option
  showPage(currentPage, document.querySelector('.nav-link.active'));
}

function openDrill(title, content) {
  document.getElementById('drillTitle').textContent = title;
  document.getElementById('drillContent').innerHTML = content;
  document.getElementById('drillOverlay').classList.add('visible');
}

function closeDrill() {
  document.getElementById('drillOverlay').classList.remove('visible');
}

function jumpToPhase(phaseId) {
  showPage('phases', document.querySelectorAll('.nav-link')[1]);
  setTimeout(() => togglePhase(phaseId, true), 100);
}

function jumpToAgent(agentId) {
  showPage('agents', document.querySelectorAll('.nav-link')[2]);
  setTimeout(() => selectAgent(agentId), 100);
}

function statusDotClass(status) {
  switch (status) {
    case 'complete': case 'passed': return 'dot-green';
    case 'active': return 'dot-amber';
    case 'blocked': return 'dot-red';
    default: return 'dot-gray';
  }
}

function riskBadgeClass(risk) {
  switch (risk) {
    case 'low': return 'badge-green';
    case 'medium': return 'badge-amber';
    case 'high': return 'badge-red';
    case 'critical': return 'badge-red';
    default: return 'badge-muted';
  }
}

function colorVar(color) {
  if (color.startsWith('--')) return `var(${color})`;
  return `var(--${color})`;
}

function colorDimVar(color) {
  const c = color.replace('--', '');
  return `var(--${c}-dim)`;
}

// ── Init ──
renderMissionControl();

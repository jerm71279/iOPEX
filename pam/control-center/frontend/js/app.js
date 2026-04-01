/**
 * App core — page switching and initialization.
 * KeeperPAM is the sole migration target — no option toggle.
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
    case 'accounts': renderAccountExplorer(); break;
    case 'gates': renderGateTracker(); break;
    case 'yellow': renderYellowCheckpoints(); break;
    case 'pamfile': break; // standalone iframe — no render needed
    case 'mcp': renderMcpDashboard(); break;
    case 'pmo': renderPMODashboard(); break;
    case 'securityqa': renderSecurityQA(); break;
    case 'guide': renderGuide(); break;
    case 'lab': renderLabShowcase(); break;
    case 'disclaimer': renderDisclaimer(); break;
  }
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

// ── Toast Notifications ──
function showToast(html, duration = 8000) {
  const container = document.getElementById('toastContainer');
  const toast = document.createElement('div');
  toast.className = 'toast toast-border-green';
  toast.innerHTML = html;
  container.appendChild(toast);

  // Close button
  const closeBtn = toast.querySelector('.toast-close');
  if (closeBtn) closeBtn.onclick = () => dismissToast(toast);

  // Animate in
  requestAnimationFrame(() => requestAnimationFrame(() => toast.classList.add('visible')));

  // Auto-dismiss
  if (duration > 0) {
    setTimeout(() => dismissToast(toast), duration);
  }
}

function dismissToast(toast) {
  toast.classList.remove('visible');
  toast.classList.add('exit');
  setTimeout(() => toast.remove(), 400);
}

// ── Init ──
renderMissionControl();

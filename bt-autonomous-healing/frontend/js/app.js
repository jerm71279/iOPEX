/**
 * HELIX — App core: page routing, option toggle, toast, overlay.
 */

let currentPage = 'mission';

function showPage(pageId, btn) {
  document.querySelectorAll('.page').forEach(p => p.classList.remove('active'));
  document.querySelectorAll('.nav-link').forEach(n => n.classList.remove('active'));
  document.getElementById('page-' + pageId).classList.add('active');
  if (btn) btn.classList.add('active');
  currentPage = pageId;

  switch (pageId) {
    case 'mission':      renderMissionControl(); break;
    case 'architecture': renderArchitecture(); break;
    case 'agents':       renderAgentGrid(); break;
    case 'cascade':      renderCascade(); break;
    case 'howitworks':   renderHowItWorks(); break;
    case 'subjects':     renderSubjects(); break;
    case 'safeguards':   renderSafeguards(); break;
    case 'audit':        renderAuditLog(); break;
    case 'guide':        renderGuide(); break;
  }
}

function switchOption(opt) {
  document.querySelectorAll('.option-btn').forEach(b => b.classList.remove('active'));
  document.getElementById('opt-' + opt).classList.add('active');

  const ind = document.getElementById('optionIndicator');
  const sub = document.getElementById('missionSubtitle');

  if (opt === 'a') {
    ind.textContent = 'CURRENT STATE — MANUAL INTERVENTION';
    ind.style.background = 'var(--amber-dim)';
    ind.style.color = 'var(--amber)';
    if (sub) sub.textContent = 'BT Current Architecture — Staff Response Bottleneck';
  } else if (opt === 'b') {
    ind.textContent = 'WITH AI LAYER — AUTONOMOUS HEALING';
    ind.style.background = 'var(--bt-dim)';
    ind.style.color = 'var(--bt)';
    if (sub) sub.textContent = 'iOPEX AI Intelligence Layer Active — 4 Agents Deployed';
  } else {
    ind.textContent = 'FULL HEALING — ZERO MANUAL INTERVENTION';
    ind.style.background = 'var(--green-dim)';
    ind.style.color = 'var(--green)';
    if (sub) sub.textContent = 'Target State — Fully Autonomous, Zero Staff Escalations';
  }

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

function showToast(html, type = 'green', duration = 7000) {
  const container = document.getElementById('toastContainer');
  const toast = document.createElement('div');
  toast.className = `toast toast-border-${type}`;
  toast.innerHTML = html + `<button class="toast-close" onclick="this.parentElement.remove()">×</button>`;
  container.appendChild(toast);
  requestAnimationFrame(() => requestAnimationFrame(() => toast.classList.add('visible')));
  if (duration > 0) {
    setTimeout(() => {
      toast.classList.remove('visible');
      toast.classList.add('exit');
      setTimeout(() => toast.remove(), 400);
    }, duration);
  }
}

function statusDot(status) {
  const map = { healthy: 'dot-green', active: 'dot-green', monitoring: 'dot-bt', standby: 'dot-amber', stale: 'dot-amber', failed: 'dot-red', rpa: 'dot-bt' };
  return map[status] || 'dot-gray';
}

// ── Init ──
renderMissionControl();

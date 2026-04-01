/**
 * MCP Servers page — server health, tool catalog, crash recovery, condition verification.
 */

let _mcpToolFilter = '';

async function renderMcpDashboard() {
  const el = document.getElementById('mcpContent');
  el.innerHTML = '<div style="color:var(--text-muted);padding:20px;">Loading MCP data...</div>';

  const [servers, tools, recovery, conditions] = await Promise.all([
    API.get('/mcp/servers'),
    API.get('/mcp/tools'),
    API.get('/mcp/crash-recovery'),
    API.get('/mcp/conditions'),
  ]);

  // Cache tools data for search filtering
  window._mcpToolsData = tools;

  el.innerHTML = '';
  el.appendChild(_renderServerHealth(servers));
  el.appendChild(_renderToolCatalog(tools));
  el.appendChild(_renderCrashRecovery(recovery));
  el.appendChild(_renderConditions(conditions));
}


/* ═══════════════════════════════════════════════════════════════
   Panel 1: Server Health
   ═══════════════════════════════════════════════════════════════ */

function _renderServerHealth(servers) {
  const panel = _mcpPanel('MCP Server Infrastructure', `<span class="badge badge-cyan">${servers.length} servers</span>`);
  const grid = document.createElement('div');
  grid.className = 'stats-grid';
  grid.style.padding = '14px';

  servers.forEach(s => {
    const statusColor = s.status === 'available' ? 'green' : 'amber';
    const condBadges = s.conditions.length
      ? s.conditions.map(c => `<span class="badge badge-purple" style="font-size:0.52rem;margin:1px;">${c}</span>`).join('')
      : '<span class="badge badge-muted" style="font-size:0.52rem;">Proxy only</span>';

    grid.innerHTML += `
      <div style="background:var(--bg-surface);border:1px solid var(--border);border-radius:var(--radius);padding:16px;min-width:280px;">
        <div style="display:flex;align-items:center;gap:8px;margin-bottom:10px;">
          <span class="health-dot dot-${statusColor}"></span>
          <span style="font-weight:700;color:var(--text-bright);font-size:0.82rem;">${s.name}</span>
        </div>
        <div style="font-size:0.68rem;color:var(--text-muted);margin-bottom:6px;">${s.description}</div>
        <div style="display:flex;gap:12px;font-size:0.65rem;color:var(--text-standard);margin-bottom:8px;">
          <span>Port: <strong style="color:var(--cyan)">${s.port}</strong></span>
          <span>Tools: <strong style="color:var(--green)">${s.tool_count}</strong></span>
          <span>Transport: <strong>${s.transport}</strong></span>
        </div>
        <div style="display:flex;gap:6px;font-size:0.6rem;color:var(--text-muted);margin-bottom:6px;">
          Docker: <code style="font-family:var(--font-mono);color:var(--teal);">${s.docker_service}</code>
        </div>
        <div style="display:flex;flex-wrap:wrap;gap:3px;margin-top:6px;">${condBadges}</div>
      </div>
    `;
  });

  panel.querySelector('.panel-body').appendChild(grid);
  return panel;
}


/* ═══════════════════════════════════════════════════════════════
   Panel 2: Tool Catalog
   ═══════════════════════════════════════════════════════════════ */

function _renderToolCatalog(data) {
  const panel = _mcpPanel('MCP Tool Catalog', `<span class="badge badge-green">${data.total} tools</span>`);
  const body = panel.querySelector('.panel-body');

  // Search input
  const searchDiv = document.createElement('div');
  searchDiv.style.cssText = 'padding:12px 14px 0;';
  searchDiv.innerHTML = `
    <input type="text" id="mcpToolSearch" placeholder="Search tools..."
      style="width:100%;background:var(--bg-surface);color:var(--text-standard);border:1px solid var(--border);border-radius:4px;padding:6px 10px;font-size:0.72rem;font-family:var(--font-sans);"
      oninput="_filterMcpTools(this.value)">
  `;
  body.appendChild(searchDiv);

  // Tool table
  const tableDiv = document.createElement('div');
  tableDiv.id = 'mcpToolTable';
  tableDiv.style.cssText = 'padding:10px 14px;max-height:500px;overflow-y:auto;';
  tableDiv.innerHTML = _buildToolTable(data, '');
  body.appendChild(tableDiv);

  return panel;
}

function _buildToolTable(data, filter) {
  const lc = filter.toLowerCase();
  let html = '';

  for (const [serverName, serverData] of Object.entries(data.servers)) {
    const tools = serverData.tools.filter(t =>
      !lc || t.name.toLowerCase().includes(lc) || t.description.toLowerCase().includes(lc)
    );
    if (tools.length === 0) continue;

    const serverColor = serverName === 'pam-migration-mcp' ? 'cyan' : 'blue';
    html += `
      <div style="margin-bottom:14px;">
        <div style="font-weight:700;font-size:0.72rem;color:var(--${serverColor});margin-bottom:6px;display:flex;align-items:center;gap:6px;">
          <span class="health-dot dot-green" style="width:6px;height:6px;"></span>
          ${serverName}
          <span class="badge badge-muted" style="font-size:0.5rem;">${tools.length} tools</span>
        </div>
        <table style="width:100%;border-collapse:collapse;font-size:0.65rem;">
          <thead>
            <tr style="color:var(--text-muted);text-align:left;border-bottom:1px solid var(--border);">
              <th style="padding:4px 8px;width:25%;">Tool</th>
              <th style="padding:4px 8px;">Description</th>
              <th style="padding:4px 8px;width:12%;">Safety</th>
              <th style="padding:4px 8px;width:12%;">Phases</th>
            </tr>
          </thead>
          <tbody>
            ${tools.map(t => `
              <tr style="border-bottom:1px solid var(--border-light);">
                <td style="padding:5px 8px;font-family:var(--font-mono);color:var(--text-bright);font-size:0.62rem;">${t.name}</td>
                <td style="padding:5px 8px;color:var(--text-standard);">${t.description}</td>
                <td style="padding:5px 8px;">${_safetyBadge(t.safety)}</td>
                <td style="padding:5px 8px;color:var(--text-muted);font-size:0.58rem;">${t.phases}</td>
              </tr>
            `).join('')}
          </tbody>
        </table>
      </div>
    `;
  }

  if (!html) {
    html = '<div style="color:var(--text-muted);padding:20px;text-align:center;">No tools match your search.</div>';
  }
  return html;
}

function _safetyBadge(level) {
  const map = {
    'READ-ONLY': 'badge-green',
    'LOW': 'badge-teal',
    'MEDIUM': 'badge-amber',
    'CRITICAL': 'badge-red',
    'RECOVERY': 'badge-purple',
  };
  return `<span class="badge ${map[level] || 'badge-muted'}" style="font-size:0.52rem;">${level}</span>`;
}

// Global for inline handler
window._mcpToolsData = null;
function _filterMcpTools(value) {
  if (!window._mcpToolsData) return;
  document.getElementById('mcpToolTable').innerHTML = _buildToolTable(window._mcpToolsData, value);
}


/* ═══════════════════════════════════════════════════════════════
   Panel 3: Crash Recovery (Condition 2)
   ═══════════════════════════════════════════════════════════════ */

function _renderCrashRecovery(data) {
  const panel = _mcpPanel('Crash Recovery — Condition 2', '<span class="badge badge-purple">C2</span>');
  const body = panel.querySelector('.panel-body');
  body.style.padding = '14px';

  const grid = document.createElement('div');
  grid.className = 'stats-grid';

  // Frozen Registry card
  grid.innerHTML += `
    <div style="background:var(--bg-surface);border:1px solid var(--border);border-radius:var(--radius);padding:14px;">
      <div style="font-weight:600;color:var(--text-bright);font-size:0.75rem;margin-bottom:8px;">Frozen Account Registry</div>
      <div style="display:flex;align-items:center;gap:6px;margin-bottom:6px;">
        <span class="health-dot dot-${data.frozen_registry.exists ? 'green' : 'red'}"></span>
        <span style="font-size:0.65rem;color:var(--text-standard);">${data.frozen_registry.exists ? 'Module deployed' : 'Module missing'}</span>
      </div>
      <div style="font-size:0.62rem;color:var(--text-muted);">Frozen accounts: <strong style="color:var(--${data.frozen_registry.frozen_count > 0 ? 'amber' : 'green'});">${data.frozen_registry.frozen_count}</strong></div>
      <div style="font-size:0.58rem;color:var(--text-muted);margin-top:4px;font-family:var(--font-mono);">${data.frozen_registry.path}</div>
    </div>
  `;

  // Watchdog card
  grid.innerHTML += `
    <div style="background:var(--bg-surface);border:1px solid var(--border);border-radius:var(--radius);padding:14px;">
      <div style="font-weight:600;color:var(--text-bright);font-size:0.75rem;margin-bottom:8px;">Watchdog Timer</div>
      <div style="display:flex;align-items:center;gap:6px;margin-bottom:6px;">
        <span class="health-dot dot-${data.watchdog.exists ? 'green' : 'red'}"></span>
        <span style="font-size:0.65rem;color:var(--text-standard);">${data.watchdog.exists ? 'Module deployed' : 'Module missing'}</span>
      </div>
      <div style="font-size:0.62rem;color:var(--text-muted);">Timeout: <strong style="color:var(--cyan);">${data.watchdog.timeout_minutes} min</strong></div>
      <div style="font-size:0.62rem;color:var(--text-muted);">Status: <strong style="color:var(--${data.watchdog.status === 'active' ? 'amber' : 'green'});">${data.watchdog.status}</strong></div>
    </div>
  `;

  // Signal handlers card
  grid.innerHTML += `
    <div style="background:var(--bg-surface);border:1px solid var(--border);border-radius:var(--radius);padding:14px;">
      <div style="font-weight:600;color:var(--text-bright);font-size:0.75rem;margin-bottom:8px;">Signal Handlers</div>
      <div style="display:flex;align-items:center;gap:6px;margin-bottom:6px;">
        <span class="health-dot dot-${data.signal_handlers.exists ? 'green' : 'red'}"></span>
        <span style="font-size:0.65rem;color:var(--text-standard);">${data.signal_handlers.exists ? 'Module deployed' : 'Module missing'}</span>
      </div>
      <div style="font-size:0.62rem;color:var(--text-muted);">Signals: ${data.signal_handlers.signals.map(s => `<code style="color:var(--teal);font-family:var(--font-mono);">${s}</code>`).join(', ')}</div>
    </div>
  `;

  body.appendChild(grid);

  // Shutdown behavior callout
  const callout = document.createElement('div');
  callout.className = 'callout callout-amber';
  callout.style.cssText = 'margin-top:12px;font-size:0.62rem;';
  callout.innerHTML = `
    <div style="font-weight:700;margin-bottom:6px;">Signal Handler Behavior (SIGTERM / SIGINT)</div>
    <ol style="margin:0;padding-left:18px;line-height:1.8;">
      ${data.signal_handlers.behavior.map(b => `<li>${b}</li>`).join('')}
    </ol>
  `;
  body.appendChild(callout);

  // Startup recovery flow
  const recoveryCallout = document.createElement('div');
  recoveryCallout.className = 'callout callout-teal';
  recoveryCallout.style.cssText = 'margin-top:10px;font-size:0.62rem;';
  recoveryCallout.innerHTML = `
    <div style="font-weight:700;margin-bottom:6px;">Startup Recovery Flow</div>
    <div style="display:flex;flex-wrap:wrap;gap:4px;align-items:center;">
      ${data.startup_recovery.flow.map((step, i) =>
        `<span style="background:var(--bg-card);border:1px solid var(--border);border-radius:4px;padding:3px 8px;color:var(--text-standard);">${i + 1}. ${step}</span>` +
        (i < data.startup_recovery.flow.length - 1 ? '<span style="color:var(--teal);">&#x2192;</span>' : '')
      ).join('')}
    </div>
  `;
  body.appendChild(recoveryCallout);

  return panel;
}


/* ═══════════════════════════════════════════════════════════════
   Panel 4: Condition Verification
   ═══════════════════════════════════════════════════════════════ */

function _renderConditions(data) {
  const panel = _mcpPanel('AI Council Condition Verification', '');

  // Count overall
  const allPass = Object.values(data).every(c => c.status === 'PASS');
  panel.querySelector('.panel-header').innerHTML += `
    <span class="badge ${allPass ? 'badge-green' : 'badge-red'}">${allPass ? 'ALL PASS' : 'ISSUES'}</span>
  `;

  const body = panel.querySelector('.panel-body');
  const grid = document.createElement('div');
  grid.className = 'stats-grid';
  grid.style.padding = '14px';

  for (const [key, cond] of Object.entries(data)) {
    const condNum = key.replace('condition_', 'C');
    const color = cond.status === 'PASS' ? 'green' : 'red';

    grid.innerHTML += `
      <div style="background:var(--bg-surface);border:1px solid var(--border);border-radius:var(--radius);padding:16px;min-width:260px;">
        <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:10px;">
          <span style="font-weight:700;color:var(--text-bright);font-size:0.78rem;">${condNum}: ${cond.name}</span>
          <span class="badge badge-${color}" style="font-size:0.55rem;">${cond.status} ${cond.passed}/${cond.total}</span>
        </div>
        <div style="font-size:0.6rem;color:var(--text-muted);margin-bottom:10px;">${cond.description}</div>
        <div style="display:flex;flex-direction:column;gap:5px;">
          ${cond.checks.map(c => `
            <div style="display:flex;align-items:center;gap:6px;font-size:0.62rem;">
              <span class="health-dot dot-${c.exists ? 'green' : 'red'}" style="width:6px;height:6px;"></span>
              <span style="color:var(--text-standard);font-family:var(--font-mono);">${c.name}</span>
            </div>
          `).join('')}
        </div>
      </div>
    `;
  }

  body.appendChild(grid);
  return panel;
}


/* ═══════════════════════════════════════════════════════════════
   Helpers
   ═══════════════════════════════════════════════════════════════ */

function _mcpPanel(title, badgeHtml) {
  const panel = document.createElement('div');
  panel.className = 'panel';
  panel.style.marginBottom = '16px';
  panel.innerHTML = `
    <div class="panel-header">
      <div class="panel-title">${title}</div>
      ${badgeHtml}
    </div>
    <div class="panel-body"></div>
  `;
  return panel;
}

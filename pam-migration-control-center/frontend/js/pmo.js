/**
 * S.H.I.F.T. PMO Intelligence Dashboard
 * Layer 0 — Management BI Interface
 *
 * Adapted from shift_pmo_dashboard.js for the SHIFT PAM Migration Control Center demo.
 * All data via /api/pmo/* endpoints (mock router — identical signatures to production RAG engine).
 *
 * Entry point: renderPMODashboard() — called by app.js showPage('pmo')
 */

class PMODashboard {
  constructor(apiBase = '') {
    this.apiBase = apiBase;
    this.currentPhase = 'P2';
    this.currentWeek = 14;
    this.pollInterval = null;
    this.queryInFlight = false;
    this.activePanel = 'executive';

    this.panels = {
      executive: { el: null, dirty: true },
      gatePipeline: { el: null, dirty: true },
      teamAccountability: { el: null, dirty: true },
      checkpointHistory: { el: null, dirty: true },
      weekOverWeek: { el: null, dirty: true },
      askProject: { el: null, dirty: false },
    };
  }

  // ── Bootstrap ─────────────────────────────────────────────────────────────

  async init(containerId) {
    const container = document.getElementById(containerId);
    if (!container) return;

    container.innerHTML = this._buildShell();
    this._bindNavigation();
    this._bindAskProject();

    await this.refreshAll();
    this._startPolling();
  }

  _buildShell() {
    return `
      <div class="pmo-dashboard">
        <div class="pmo-header">
          <div class="pmo-title">
            <span class="pmo-icon">&#x1F4CA;</span>
            <h2>PMO Intelligence Dashboard</h2>
            <span class="pmo-badge" id="pmo-corpus-badge">— events indexed</span>
          </div>
          <div class="pmo-phase-selector">
            <label>Phase</label>
            <select id="pmo-phase-select">
              ${['P0','P1','P2','P3','P4','P5','P6','P7'].map(p =>
                `<option value="${p}" ${p === this.currentPhase ? 'selected' : ''}>${p}</option>`
              ).join('')}
            </select>
          </div>
        </div>

        <nav class="pmo-nav">
          <button class="pmo-nav-btn active" data-panel="executive">Executive Summary</button>
          <button class="pmo-nav-btn" data-panel="gatePipeline">Gate Pipeline</button>
          <button class="pmo-nav-btn" data-panel="teamAccountability">Team Accountability</button>
          <button class="pmo-nav-btn" data-panel="checkpointHistory">Checkpoints</button>
          <button class="pmo-nav-btn" data-panel="weekOverWeek">Trends</button>
          <button class="pmo-nav-btn" data-panel="askProject">Ask the Project</button>
        </nav>

        <div class="pmo-content">
          <div id="pmo-panel-executive" class="pmo-panel active"></div>
          <div id="pmo-panel-gatePipeline" class="pmo-panel"></div>
          <div id="pmo-panel-teamAccountability" class="pmo-panel"></div>
          <div id="pmo-panel-checkpointHistory" class="pmo-panel"></div>
          <div id="pmo-panel-weekOverWeek" class="pmo-panel"></div>
          <div id="pmo-panel-askProject" class="pmo-panel"></div>
        </div>

        <div class="pmo-footer">
          <span id="pmo-last-refresh">–</span>
          <span class="pmo-corpus-info" id="pmo-corpus-info"></span>
        </div>
      </div>
    `;
  }

  // ── Navigation ────────────────────────────────────────────────────────────

  _bindNavigation() {
    document.querySelectorAll('.pmo-nav-btn').forEach(btn => {
      btn.addEventListener('click', () => {
        document.querySelectorAll('.pmo-nav-btn').forEach(b => b.classList.remove('active'));
        document.querySelectorAll('.pmo-panel').forEach(p => p.classList.remove('active'));
        btn.classList.add('active');
        document.getElementById(`pmo-panel-${btn.dataset.panel}`).classList.add('active');
        this.activePanel = btn.dataset.panel;
      });
    });

    document.getElementById('pmo-phase-select')?.addEventListener('change', (e) => {
      this.currentPhase = e.target.value;
      this.refreshAll();
    });
  }

  // ── Refresh ───────────────────────────────────────────────────────────────

  async refreshAll() {
    await Promise.allSettled([
      this._renderExecutiveSummary(),
      this._renderGatePipeline(),
      this._renderTeamAccountability(),
      this._renderCheckpointHistory(),
      this._renderWeekOverWeek(),
      this._updateCorpusStats(),
    ]);
    document.getElementById('pmo-last-refresh').textContent =
      `Last refresh: ${new Date().toLocaleTimeString()}`;
  }

  _startPolling() {
    if (this.pollInterval) clearInterval(this.pollInterval);
    this.pollInterval = setInterval(() => this.refreshAll(), 30000);
  }

  // ── Panel 1: Executive Summary ────────────────────────────────────────────

  async _renderExecutiveSummary() {
    const el = document.getElementById('pmo-panel-executive');
    if (!el) return;
    el.innerHTML = this._loading('Synthesizing executive summary...');

    try {
      const data = await this._get(`/api/pmo/metrics/executive-summary?phase=${this.currentPhase}`);

      const gateCounts = data.gate_summary || {};
      const cpData = data.checkpoint_summary || {};

      el.innerHTML = `
        <div class="pmo-section">
          <h3>Executive Summary &#x2014; Phase ${this.currentPhase}</h3>
          <div class="pmo-ai-answer">
            <div class="pmo-ai-icon">&#x1F916;</div>
            <div class="pmo-ai-text">${this._escapeHtml(data.answer)}</div>
          </div>
          <div class="pmo-citations">
            <span>Sources: ${(data.citations || []).length} project events</span>
            <span class="pmo-trace">Trace: ${data.trace_id?.slice(0,8)}</span>
          </div>
        </div>

        <div class="pmo-metrics-row">
          ${this._gateStatusCard('Gates Open', gateCounts.OPEN || 0, 'metric-neutral')}
          ${this._gateStatusCard('Gates Green', gateCounts.GREEN || 0, 'metric-green')}
          ${this._gateStatusCard('Gates Blocked', gateCounts.BLOCKED || 0, 'metric-red')}
          ${this._gateStatusCard('BLOCK Checkpoints', cpData.BLOCK?.count || 0, 'metric-amber')}
          ${this._gateStatusCard('CRITICAL Checkpoints', cpData.CRITICAL?.count || 0, 'metric-red')}
        </div>
      `;
    } catch (e) {
      el.innerHTML = this._error('Failed to load executive summary', e);
    }
  }

  // ── Panel 2: Gate Pipeline ────────────────────────────────────────────────

  async _renderGatePipeline() {
    const el = document.getElementById('pmo-panel-gatePipeline');
    if (!el) return;
    el.innerHTML = this._loading('Loading gate pipeline...');

    try {
      const data = await this._get(`/api/pmo/metrics/gate-pipeline?phase=${this.currentPhase}`);
      const gates = data.gates || [];
      const summary = data.summary || {};

      el.innerHTML = `
        <div class="pmo-section">
          <h3>Gate Pipeline &#x2014; Phase ${this.currentPhase}</h3>
          <div class="pmo-gate-summary">
            ${Object.entries(summary).map(([status, count]) =>
              `<div class="pmo-gate-pill pmo-gate-${status.toLowerCase()}">${count} ${status}</div>`
            ).join('')}
          </div>

          <div class="pmo-gate-list">
            ${gates.length === 0
              ? '<div class="pmo-empty">No gate events indexed yet</div>'
              : gates.map(g => this._gateRow(g)).join('')
            }
          </div>
        </div>
      `;

      // Wire drill-down clicks
      el.querySelectorAll('.pmo-gate-row').forEach(row => {
        row.addEventListener('click', () => this._drillDownGate(row.dataset.gateId));
      });

    } catch (e) {
      el.innerHTML = this._error('Failed to load gate pipeline', e);
    }
  }

  _gateRow(gate) {
    const statusClass = {
      GREEN: 'status-green', AMBER: 'status-amber', RED: 'status-red',
      BLOCKED: 'status-red', OPEN: 'status-neutral'
    }[gate.status] || 'status-neutral';

    return `
      <div class="pmo-gate-row" data-gate-id="${gate.gate_id}" title="Click to drill down">
        <span class="pmo-gate-num">G${gate.gate_id}</span>
        <span class="pmo-gate-status ${statusClass}">${gate.status}</span>
        <span class="pmo-gate-team">${gate.owner_team}</span>
        <span class="pmo-gate-time">${this._relativeTime(gate.last_event)}</span>
        <span class="pmo-gate-drill">&#x25B6;</span>
      </div>
    `;
  }

  async _drillDownGate(gateId) {
    const el = document.getElementById('pmo-panel-gatePipeline');
    let drillEl = el.querySelector('.pmo-drill-down');
    if (!drillEl) {
      drillEl = document.createElement('div');
      drillEl.className = 'pmo-drill-down';
      el.appendChild(drillEl);
    }
    drillEl.innerHTML = this._loading(`Loading Gate ${gateId} history...`);

    const result = await this._query(
      `Show the full history for Gate ${gateId} — all status changes, blockers, and resolution details.`,
      { gate_id: parseInt(gateId) },
      'technical'
    );

    drillEl.innerHTML = `
      <div class="pmo-drill-header">
        <h4>Gate ${gateId} &#x2014; Drill Down</h4>
        <button class="pmo-close-drill" onclick="this.closest('.pmo-drill-down').remove()">&#x2715;</button>
      </div>
      <div class="pmo-drill-answer">${this._escapeHtml(result.answer)}</div>
      <div class="pmo-drill-meta">Sources: ${result.sources_used} | Trace: ${result.trace_id?.slice(0,8)}</div>
    `;
  }

  // ── Panel 3: Team Accountability ──────────────────────────────────────────

  async _renderTeamAccountability() {
    const el = document.getElementById('pmo-panel-teamAccountability');
    if (!el) return;
    el.innerHTML = this._loading('Loading team accountability...');

    try {
      const data = await this._get('/api/pmo/metrics/team-accountability?weeks=4');
      const teams = data.teams || [];

      el.innerHTML = `
        <div class="pmo-section">
          <h3>Team Accountability &#x2014; Last ${data.weeks_analyzed} Weeks</h3>
          <div class="pmo-team-list">
            ${teams.length === 0
              ? '<div class="pmo-empty">No team data indexed yet</div>'
              : teams.map(t => this._teamRow(t)).join('')
            }
          </div>
        </div>
      `;

      teams.forEach(t => {
        el.querySelector(`[data-team="${t.team}"]`)?.addEventListener('click', () => {
          this._drillDownTeam(t.team);
        });
      });

    } catch (e) {
      el.innerHTML = this._error('Failed to load team accountability', e);
    }
  }

  _teamRow(team) {
    const rate = team.completion_rate || 0;
    const barClass = rate >= 80 ? 'bar-green' : rate >= 60 ? 'bar-amber' : 'bar-red';
    const flagIcon = rate < 60 ? ' &#x26A0;&#xFE0F;' : '';

    return `
      <div class="pmo-team-row" data-team="${team.team}" title="Click for details">
        <div class="pmo-team-name">${team.team}${flagIcon}</div>
        <div class="pmo-team-bar-wrap">
          <div class="pmo-team-bar ${barClass}" style="width:${rate}%"></div>
        </div>
        <div class="pmo-team-stats">
          <span>${rate}%</span>
          <span class="pmo-muted">${team.completed}/${team.total} items</span>
          ${team.blocked > 0 ? `<span class="pmo-blocked">${team.blocked} blocked</span>` : ''}
        </div>
      </div>
    `;
  }

  async _drillDownTeam(team) {
    const result = await this._query(
      `What are the outstanding action items, blockers, and recent activity for ${team}? What needs to happen next?`,
      { owner_team: team },
      'team_lead'
    );
    this._showDrillDown(`Team: ${team}`, result, 'pmo-panel-teamAccountability');
  }

  // ── Panel 4: Checkpoint History ───────────────────────────────────────────

  async _renderCheckpointHistory() {
    const el = document.getElementById('pmo-panel-checkpointHistory');
    if (!el) return;
    el.innerHTML = this._loading('Loading checkpoint history...');

    try {
      const data = await this._get(`/api/pmo/metrics/checkpoint-history?phase=${this.currentPhase}`);
      const cps = data.checkpoints || {};
      const severities = ['CRITICAL', 'BLOCK', 'WARN', 'INFO'];
      const maxCount = Math.max(...severities.map(s => cps[s]?.count || 0), 1);

      el.innerHTML = `
        <div class="pmo-section">
          <h3>Yellow Checkpoint History &#x2014; Phase ${this.currentPhase}</h3>
          <div class="pmo-cp-grid">
            ${severities.map(s => {
              const cp = cps[s] || { count: 0, resolve_rate: 0 };
              const barH = Math.round((cp.count / maxCount) * 80);
              const colorClass = { CRITICAL: 'cp-critical', BLOCK: 'cp-block', WARN: 'cp-warn', INFO: 'cp-info' }[s];
              return `
                <div class="pmo-cp-col" data-severity="${s}" title="Click to drill down">
                  <div class="pmo-cp-bar-wrap">
                    <div class="pmo-cp-bar ${colorClass}" style="height:${barH}px"></div>
                  </div>
                  <div class="pmo-cp-count">${cp.count}</div>
                  <div class="pmo-cp-label">${s}</div>
                  <div class="pmo-cp-resolve">${cp.resolve_rate}% resolved</div>
                </div>
              `;
            }).join('')}
          </div>
        </div>
      `;

      el.querySelectorAll('.pmo-cp-col').forEach(col => {
        col.addEventListener('click', () => this._drillDownCheckpoint(col.dataset.severity));
      });

    } catch (e) {
      el.innerHTML = this._error('Failed to load checkpoint history', e);
    }
  }

  async _drillDownCheckpoint(severity) {
    const result = await this._query(
      `Show all ${severity} checkpoints in Phase ${this.currentPhase} — what triggered them, resolution time, and who resolved them.`,
      { doc_types: ['yellow_checkpoint'], severity, phase: this.currentPhase },
      'technical'
    );
    this._showDrillDown(`${severity} Checkpoints`, result, 'pmo-panel-checkpointHistory');
  }

  // ── Panel 5: Week-over-Week Trend ─────────────────────────────────────────

  async _renderWeekOverWeek() {
    const el = document.getElementById('pmo-panel-weekOverWeek');
    if (!el) return;
    el.innerHTML = this._loading('Loading trend data...');

    try {
      const data = await this._get(
        `/api/pmo/metrics/week-over-week?current_week=${this.currentWeek}&lookback=3`
      );
      const trend = data.trend || [];

      const metrics = ['gates_closed', 'exec_success_rate', 'critical_checkpoints', 'open_blockers'];
      const labels = { gates_closed: 'Gates Closed', exec_success_rate: 'Exec Success %',
                       critical_checkpoints: 'Critical CPs', open_blockers: 'Open Blockers' };
      const arrows = { gates_closed: 'up', exec_success_rate: 'up',
                       critical_checkpoints: 'down', open_blockers: 'down' };

      el.innerHTML = `
        <div class="pmo-section">
          <h3>Week-over-Week Trend</h3>
          <div class="pmo-trend-table">
            <table>
              <thead>
                <tr>
                  <th>Metric</th>
                  ${trend.map(w => `<th>W${w.week}</th>`).join('')}
                  <th>Direction</th>
                </tr>
              </thead>
              <tbody>
                ${metrics.map(m => {
                  const values = trend.map(w => w[m]);
                  const first = values[0] || 0;
                  const last = values[values.length - 1] || 0;
                  const goodDirection = arrows[m] === 'up' ? last >= first : last <= first;
                  const dirIcon = last === first ? '&#x2192;' : (last > first ? '&#x2191;' : '&#x2193;');
                  const dirClass = goodDirection ? 'trend-good' : 'trend-bad';

                  return `
                    <tr>
                      <td class="pmo-metric-name">${labels[m]}</td>
                      ${values.map(v => `<td>${typeof v === 'number' && m.includes('rate') ? v + '%' : v}</td>`).join('')}
                      <td class="${dirClass}">${dirIcon}</td>
                    </tr>
                  `;
                }).join('')}
              </tbody>
            </table>
          </div>
        </div>
      `;
    } catch (e) {
      el.innerHTML = this._error('Failed to load trend data', e);
    }
  }

  // ── Panel 6: Ask the Project ──────────────────────────────────────────────

  _bindAskProject() {
    document.addEventListener('click', (e) => {
      if (e.target.id === 'pmo-ask-btn') this._submitAsk();
    });
    document.addEventListener('keydown', (e) => {
      if (e.key === 'Enter' && document.activeElement?.id === 'pmo-ask-input') {
        this._submitAsk();
      }
    });

    const panel = document.getElementById('pmo-panel-askProject');
    if (!panel) return;
    panel.innerHTML = `
      <div class="pmo-section">
        <h3>Ask the Project</h3>
        <p class="pmo-ask-hint">
          Ask any management question. The AI PMO will search all project history and synthesize an answer.
        </p>
        <div class="pmo-ask-examples">
          <strong>Examples:</strong>
          <span class="pmo-example" onclick="document.getElementById('pmo-ask-input').value=this.textContent">Why is Wave 1 delayed?</span>
          <span class="pmo-example" onclick="document.getElementById('pmo-ask-input').value=this.textContent">What is CLIENT_INFOSEC blocking?</span>
          <span class="pmo-example" onclick="document.getElementById('pmo-ask-input').value=this.textContent">Show Gate 4 full history</span>
          <span class="pmo-example" onclick="document.getElementById('pmo-ask-input').value=this.textContent">What are the top 3 risks right now?</span>
          <span class="pmo-example" onclick="document.getElementById('pmo-ask-input').value=this.textContent">Who owns the NHI wave?</span>
        </div>
        <div class="pmo-ask-row">
          <input id="pmo-ask-input" type="text" placeholder="Ask anything about this project..." />
          <select id="pmo-ask-audience">
            <option value="executive">Executive</option>
            <option value="team_lead">Team Lead</option>
            <option value="technical">Technical</option>
          </select>
          <button id="pmo-ask-btn">Ask</button>
        </div>
        <div id="pmo-ask-result"></div>
      </div>
    `;
  }

  async _submitAsk() {
    if (this.queryInFlight) return;
    const input = document.getElementById('pmo-ask-input');
    const audience = document.getElementById('pmo-ask-audience')?.value || 'executive';
    const question = input?.value?.trim();
    if (!question) return;

    this.queryInFlight = true;
    const resultEl = document.getElementById('pmo-ask-result');
    resultEl.innerHTML = this._loading('Searching project history...');

    try {
      const result = await this._query(question, {}, audience);
      resultEl.innerHTML = `
        <div class="pmo-ask-answer">
          <div class="pmo-ai-icon">&#x1F916;</div>
          <div class="pmo-ai-text">${this._escapeHtml(result.answer)}</div>
        </div>
        <div class="pmo-ask-meta">
          <span>${result.sources_used} sources</span>
          <span>Audience: ${audience}</span>
          <span>Trace: ${result.trace_id?.slice(0,8)}</span>
        </div>
        <div class="pmo-citations-list">
          ${(result.citations || []).slice(0, 5).map(c =>
            `<span class="pmo-citation-tag">${c}</span>`
          ).join('')}
        </div>
      `;
    } catch (e) {
      resultEl.innerHTML = this._error('Query failed', e);
    } finally {
      this.queryInFlight = false;
    }
  }

  // ── API Helpers ───────────────────────────────────────────────────────────

  async _get(path) {
    const res = await fetch(path);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return res.json();
  }

  async _query(question, filters = {}, audience = 'executive') {
    const res = await fetch('/api/pmo/query', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ question, audience, filters }),
    });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return res.json();
  }

  async _updateCorpusStats() {
    try {
      const data = await this._get('/api/pmo/corpus/stats');
      const badge = document.getElementById('pmo-corpus-badge');
      if (badge) badge.textContent = `${data.total_indexed} events indexed`;
      const info = document.getElementById('pmo-corpus-info');
      if (info) {
        info.textContent = Object.entries(data.by_type || {})
          .map(([t, c]) => `${t}: ${c}`).join(' · ');
      }
    } catch (_) {}
  }

  // ── Shared Utilities ──────────────────────────────────────────────────────

  _showDrillDown(title, result, panelId) {
    const panel = document.getElementById(panelId.startsWith('pmo-panel-') ? panelId : `pmo-panel-${panelId}`);
    if (!panel) return;
    let drillEl = panel.querySelector('.pmo-drill-down');
    if (!drillEl) {
      drillEl = document.createElement('div');
      drillEl.className = 'pmo-drill-down';
      panel.appendChild(drillEl);
    }
    drillEl.innerHTML = `
      <div class="pmo-drill-header">
        <h4>${title}</h4>
        <button onclick="this.closest('.pmo-drill-down').remove()">&#x2715;</button>
      </div>
      <div class="pmo-drill-answer">${this._escapeHtml(result.answer)}</div>
      <div class="pmo-drill-meta">
        Sources: ${result.sources_used} | Trace: ${result.trace_id?.slice(0,8)}
      </div>
    `;
    drillEl.scrollIntoView({ behavior: 'smooth' });
  }

  _gateStatusCard(label, value, cls) {
    return `<div class="pmo-metric-card ${cls}"><div class="pmo-metric-val">${value}</div><div class="pmo-metric-lbl">${label}</div></div>`;
  }

  _relativeTime(isoStr) {
    if (!isoStr) return '&#x2014;';
    const diff = Date.now() - new Date(isoStr).getTime();
    const days = Math.floor(diff / 86400000);
    if (days === 0) return 'Today';
    if (days === 1) return 'Yesterday';
    return `${days}d ago`;
  }

  _loading(msg) {
    return `<div class="pmo-loading"><span class="pmo-spinner">&#x27F3;</span> ${msg}</div>`;
  }

  _error(msg, err) {
    return `<div class="pmo-error">&#x26A0; ${msg}: ${err?.message || err}</div>`;
  }

  _escapeHtml(str) {
    if (!str) return '';
    return str.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;')
              .replace(/"/g,'&quot;').replace(/\n/g,'<br>');
  }
}

// ── CSS ───────────────────────────────────────────────────────────────────────

const PMO_STYLES = `
.pmo-dashboard { font-family: var(--font-sans, 'Inter', sans-serif); background: var(--bg-base, #0d1117); color: var(--text-standard, #e6edf3); border-radius: 8px; overflow: hidden; }
.pmo-header { display: flex; justify-content: space-between; align-items: center; padding: 16px 20px; background: var(--bg-surface, #161b22); border-bottom: 1px solid var(--border, #30363d); }
.pmo-title { display: flex; align-items: center; gap: 10px; }
.pmo-title h2 { margin: 0; font-size: 16px; font-weight: 600; }
.pmo-badge { background: var(--bg-card, #21262d); padding: 2px 8px; border-radius: 12px; font-size: 11px; color: var(--text-muted, #8b949e); }
.pmo-nav { display: flex; gap: 2px; padding: 8px 20px; background: var(--bg-surface, #161b22); border-bottom: 1px solid var(--border, #30363d); flex-wrap: wrap; }
.pmo-nav-btn { background: none; border: none; color: var(--text-muted, #8b949e); padding: 6px 14px; border-radius: 6px; cursor: pointer; font-size: 13px; transition: all 0.15s; }
.pmo-nav-btn:hover { background: var(--bg-card, #21262d); color: var(--text-bright, #e6edf3); }
.pmo-nav-btn.active { background: var(--blue, #1f6feb); color: #fff; }
.pmo-content { min-height: 400px; }
.pmo-panel { display: none; padding: 20px; }
.pmo-panel.active { display: block; }
.pmo-section h3 { margin: 0 0 16px; font-size: 15px; color: var(--text-bright, #e6edf3); }
.pmo-ai-answer { display: flex; gap: 12px; background: var(--bg-surface, #161b22); border: 1px solid var(--border, #30363d); border-radius: 8px; padding: 14px; margin-bottom: 12px; }
.pmo-ai-icon { font-size: 20px; flex-shrink: 0; }
.pmo-ai-text { font-size: 13px; line-height: 1.6; color: var(--text-standard, #c9d1d9); }
.pmo-citations { font-size: 11px; color: var(--text-muted, #6e7681); display: flex; gap: 16px; }
.pmo-trace { font-family: var(--font-mono, monospace); }
.pmo-metrics-row { display: flex; gap: 12px; flex-wrap: wrap; margin-top: 16px; }
.pmo-metric-card { background: var(--bg-surface, #161b22); border: 1px solid var(--border, #30363d); border-radius: 8px; padding: 14px 18px; min-width: 120px; text-align: center; }
.pmo-metric-val { font-size: 28px; font-weight: 700; }
.pmo-metric-lbl { font-size: 11px; color: var(--text-muted, #8b949e); margin-top: 4px; }
.metric-green .pmo-metric-val { color: var(--green, #3fb950); }
.metric-amber .pmo-metric-val { color: var(--amber, #d29922); }
.metric-red .pmo-metric-val { color: var(--red, #f85149); }
.metric-neutral .pmo-metric-val { color: var(--blue, #58a6ff); }
.pmo-gate-summary { display: flex; gap: 8px; margin-bottom: 16px; flex-wrap: wrap; }
.pmo-gate-pill { padding: 4px 10px; border-radius: 12px; font-size: 12px; font-weight: 500; }
.pmo-gate-green { background: var(--green-dim, #0d4429); color: var(--green, #3fb950); }
.pmo-gate-amber { background: var(--amber-dim, #341a00); color: var(--amber, #d29922); }
.pmo-gate-red, .pmo-gate-blocked { background: var(--red-dim, #3d1a1a); color: var(--red, #f85149); }
.pmo-gate-open { background: var(--bg-card, #21262d); color: var(--text-muted, #8b949e); }
.pmo-gate-list { display: flex; flex-direction: column; gap: 6px; }
.pmo-gate-row { display: grid; grid-template-columns: 40px 100px 1fr 80px 20px; align-items: center; gap: 12px; padding: 10px 14px; background: var(--bg-surface, #161b22); border: 1px solid var(--border, #30363d); border-radius: 6px; cursor: pointer; transition: border-color 0.15s; }
.pmo-gate-row:hover { border-color: var(--cyan, #58a6ff); }
.pmo-gate-num { font-weight: 700; font-family: var(--font-mono, monospace); color: var(--cyan, #58a6ff); }
.pmo-gate-team { font-size: 12px; color: var(--text-muted, #8b949e); }
.pmo-gate-time { font-size: 11px; color: var(--text-dim, #6e7681); }
.pmo-gate-drill { color: var(--border, #30363d); }
.status-green { color: var(--green, #3fb950); font-weight: 600; }
.status-amber { color: var(--amber, #d29922); font-weight: 600; }
.status-red { color: var(--red, #f85149); font-weight: 600; }
.status-neutral { color: var(--text-muted, #8b949e); font-weight: 600; }
.pmo-team-list { display: flex; flex-direction: column; gap: 10px; }
.pmo-team-row { background: var(--bg-surface, #161b22); border: 1px solid var(--border, #30363d); border-radius: 6px; padding: 12px 16px; cursor: pointer; transition: border-color 0.15s; }
.pmo-team-row:hover { border-color: var(--cyan, #58a6ff); }
.pmo-team-name { font-weight: 600; font-size: 13px; margin-bottom: 6px; }
.pmo-team-bar-wrap { background: var(--bg-card, #21262d); border-radius: 4px; height: 8px; margin-bottom: 6px; overflow: hidden; }
.pmo-team-bar { height: 100%; border-radius: 4px; transition: width 0.3s; }
.bar-green { background: var(--green, #3fb950); }
.bar-amber { background: var(--amber, #d29922); }
.bar-red { background: var(--red, #f85149); }
.pmo-team-stats { display: flex; gap: 12px; font-size: 12px; color: var(--text-muted, #8b949e); }
.pmo-blocked { color: var(--red, #f85149); }
.pmo-muted { color: var(--text-dim, #6e7681); }
.pmo-cp-grid { display: flex; gap: 20px; align-items: flex-end; padding: 20px 0; }
.pmo-cp-col { display: flex; flex-direction: column; align-items: center; gap: 4px; cursor: pointer; min-width: 80px; }
.pmo-cp-col:hover .pmo-cp-bar { opacity: 0.8; }
.pmo-cp-bar-wrap { display: flex; align-items: flex-end; height: 100px; }
.pmo-cp-bar { width: 48px; border-radius: 4px 4px 0 0; min-height: 4px; transition: height 0.3s; }
.cp-critical { background: var(--red, #f85149); }
.cp-block { background: var(--amber, #d29922); }
.cp-warn { background: var(--blue, #58a6ff); }
.cp-info { background: var(--green, #3fb950); }
.pmo-cp-count { font-size: 20px; font-weight: 700; }
.pmo-cp-label { font-size: 12px; color: var(--text-muted, #8b949e); font-weight: 600; }
.pmo-cp-resolve { font-size: 11px; color: var(--text-dim, #6e7681); }
.pmo-trend-table { overflow-x: auto; }
.pmo-trend-table table { width: 100%; border-collapse: collapse; font-size: 13px; }
.pmo-trend-table th, .pmo-trend-table td { padding: 10px 14px; border-bottom: 1px solid var(--bg-card, #21262d); text-align: center; }
.pmo-trend-table th { color: var(--text-muted, #8b949e); font-weight: 500; font-size: 12px; }
.pmo-metric-name { text-align: left; color: var(--text-standard, #c9d1d9); }
.trend-good { color: var(--green, #3fb950); font-weight: 700; font-size: 16px; }
.trend-bad { color: var(--red, #f85149); font-weight: 700; font-size: 16px; }
.pmo-ask-hint { color: var(--text-muted, #8b949e); font-size: 13px; margin-bottom: 12px; }
.pmo-ask-examples { font-size: 12px; color: var(--text-dim, #6e7681); margin-bottom: 14px; display: flex; gap: 8px; flex-wrap: wrap; align-items: center; }
.pmo-example { background: var(--bg-card, #21262d); padding: 4px 10px; border-radius: 12px; cursor: pointer; color: var(--cyan, #58a6ff); transition: background 0.15s; }
.pmo-example:hover { background: var(--border, #30363d); }
.pmo-ask-row { display: flex; gap: 8px; margin-bottom: 16px; }
#pmo-ask-input { flex: 1; background: var(--bg-surface, #161b22); border: 1px solid var(--border, #30363d); border-radius: 6px; padding: 10px 14px; color: var(--text-bright, #e6edf3); font-size: 14px; outline: none; }
#pmo-ask-input:focus { border-color: var(--cyan, #58a6ff); }
#pmo-ask-audience { background: var(--bg-surface, #161b22); border: 1px solid var(--border, #30363d); border-radius: 6px; padding: 10px 12px; color: var(--text-bright, #e6edf3); font-size: 13px; }
#pmo-ask-btn { background: var(--blue, #1f6feb); color: #fff; border: none; border-radius: 6px; padding: 10px 20px; cursor: pointer; font-size: 14px; font-weight: 500; transition: background 0.15s; }
#pmo-ask-btn:hover { background: var(--cyan, #388bfd); }
.pmo-ask-answer { display: flex; gap: 12px; background: var(--bg-surface, #161b22); border: 1px solid var(--blue, #1f6feb); border-radius: 8px; padding: 14px; margin-bottom: 8px; }
.pmo-ask-meta { font-size: 11px; color: var(--text-dim, #6e7681); display: flex; gap: 14px; margin-bottom: 8px; }
.pmo-citations-list { display: flex; gap: 6px; flex-wrap: wrap; }
.pmo-citation-tag { background: var(--bg-card, #21262d); font-family: var(--font-mono, monospace); font-size: 10px; padding: 2px 8px; border-radius: 4px; color: var(--text-muted, #8b949e); }
.pmo-drill-down { margin-top: 16px; background: var(--bg-base, #0d1117); border: 1px solid var(--cyan, #58a6ff); border-radius: 8px; padding: 16px; }
.pmo-drill-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px; }
.pmo-drill-header h4 { margin: 0; color: var(--cyan, #58a6ff); }
.pmo-drill-header button, .pmo-close-drill { background: none; border: none; color: var(--text-muted, #8b949e); cursor: pointer; font-size: 16px; }
.pmo-drill-answer { font-size: 13px; line-height: 1.6; color: var(--text-standard, #c9d1d9); }
.pmo-drill-meta { font-size: 11px; color: var(--text-dim, #6e7681); margin-top: 8px; }
.pmo-loading { color: var(--text-muted, #8b949e); font-size: 13px; padding: 24px; text-align: center; }
.pmo-spinner { display: inline-block; animation: pmo-spin 1s linear infinite; }
@keyframes pmo-spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }
.pmo-error { color: var(--red, #f85149); background: var(--red-dim, #3d1a1a); border-radius: 6px; padding: 12px; font-size: 13px; }
.pmo-empty { color: var(--text-dim, #6e7681); font-size: 13px; padding: 24px; text-align: center; }
.pmo-footer { padding: 10px 20px; background: var(--bg-surface, #161b22); border-top: 1px solid var(--border, #30363d); display: flex; justify-content: space-between; font-size: 11px; color: var(--text-dim, #6e7681); }
.pmo-phase-selector { display: flex; align-items: center; gap: 8px; font-size: 13px; }
.pmo-phase-selector select { background: var(--bg-card, #21262d); border: 1px solid var(--border, #30363d); border-radius: 6px; color: var(--text-bright, #e6edf3); padding: 4px 10px; }
`;

// Inject styles once
if (!document.getElementById('pmo-styles')) {
  const styleEl = document.createElement('style');
  styleEl.id = 'pmo-styles';
  styleEl.textContent = PMO_STYLES;
  document.head.appendChild(styleEl);
}

// ── Demo entry point ────────────────────────────────────────────────────────

window.PMODashboard = PMODashboard;

let _pmoDashboardInstance = null;

async function renderPMODashboard() {
  const el = document.getElementById('shift-pmo-dashboard');
  if (!el) return;

  if (!_pmoDashboardInstance) {
    _pmoDashboardInstance = new PMODashboard();
    await _pmoDashboardInstance.init('shift-pmo-dashboard');
  } else {
    await _pmoDashboardInstance.refreshAll();
  }
}

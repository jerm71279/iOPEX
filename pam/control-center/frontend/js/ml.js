/**
 * ML module rendering — ETL anomaly detection + NHI classification visibility.
 */

let _mlStatus = null;
let _mlClassifications = null;

async function fetchMLStatus() {
  if (!_mlStatus) _mlStatus = await API.get('/ml/status');
  return _mlStatus;
}

async function fetchMLClassifications() {
  if (!_mlClassifications) _mlClassifications = await API.get('/ml/classifications');
  return _mlClassifications;
}

function invalidateMLCache() { _mlStatus = null; _mlClassifications = null; }

// ── Mission Control: ML Model Status Panel ─────────────────────────
async function renderMLStatus() {
  const panel = document.getElementById('mlStatusPanel');
  const badge = document.getElementById('mlStatusBadge');
  if (!panel || !badge) return;

  const ml = await fetchMLStatus();
  if (!ml || !ml.enabled) {
    badge.textContent = 'DISABLED';
    badge.className = 'badge badge-muted';
    panel.innerHTML = '<div style="padding:14px;color:var(--text-muted);font-size:0.72rem;">ML module is disabled. Set <code>ml.enabled: true</code> in agent_config.json.</div>';
    return;
  }

  if (ml.mock_fallback) {
    badge.textContent = 'MOCK';
    badge.className = 'badge badge-amber';
    badge.title = ml.mock_reason || 'ML models unavailable — showing synthetic data';
  } else {
    badge.textContent = 'ACTIVE';
    badge.className = 'badge badge-green';
  }

  const etl = ml.etl_detector;
  const nhi = ml.nhi_classifier;

  const stateColor = s => s === 'warm' ? 'var(--green)' : s === 'cold_start' ? 'var(--amber)' : 'var(--text-muted)';

  panel.innerHTML = `
    <div style="display:grid;grid-template-columns:1fr 1fr;gap:12px;padding:14px;">
      <div style="background:var(--bg-surface);border:1px solid var(--border);border-radius:var(--radius);padding:14px;">
        <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:10px;">
          <span style="font-family:var(--font-mono);font-size:0.58rem;font-weight:700;letter-spacing:1px;color:var(--text-muted);">ETL ANOMALY DETECTOR</span>
          <span style="font-size:0.55rem;font-weight:700;color:${stateColor(etl.state)};font-family:var(--font-mono);">${etl.state.toUpperCase()}</span>
        </div>
        <div style="font-size:0.68rem;color:var(--text-standard);line-height:1.8;">
          <div>Model: <span style="color:var(--cyan);font-family:var(--font-mono);">${etl.model_type}</span></div>
          <div>Samples: <strong>${etl.training_samples}</strong></div>
          <div>Anomalies: <strong style="color:var(--amber)">${etl.anomalies_detected}</strong></div>
          <div>Blend: EWMA ${Math.round(etl.blend_weight_ewma*100)}% / IF ${Math.round(etl.blend_weight_if*100)}%</div>
          <div style="font-size:0.58rem;color:var(--text-muted);margin-top:4px;">Last retrained: ${new Date(etl.last_retrained).toLocaleDateString()}</div>
        </div>
      </div>
      <div style="background:var(--bg-surface);border:1px solid var(--border);border-radius:var(--radius);padding:14px;">
        <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:10px;">
          <span style="font-family:var(--font-mono);font-size:0.58rem;font-weight:700;letter-spacing:1px;color:var(--text-muted);">NHI CLASSIFIER</span>
          <span style="font-size:0.55rem;font-weight:700;color:${stateColor(nhi.state)};font-family:var(--font-mono);">${nhi.state.toUpperCase()}</span>
        </div>
        <div style="font-size:0.68rem;color:var(--text-standard);line-height:1.8;">
          <div>Model: <span style="color:var(--purple);font-family:var(--font-mono);">${nhi.model_type}</span></div>
          <div>Samples: <strong>${nhi.training_samples}</strong> (${nhi.human_corrections} corrections)</div>
          <div>Accuracy: <strong style="color:var(--green)">${Math.round(nhi.accuracy*100)}%</strong></div>
          <div>Blend: Rules ${Math.round(nhi.blend_weights.rules*100)}% / ML ${Math.round(nhi.blend_weights.ml*100)}%</div>
          <div style="font-size:0.58rem;color:var(--text-muted);margin-top:4px;">Last retrained: ${new Date(nhi.last_retrained).toLocaleDateString()}</div>
        </div>
      </div>
    </div>`;
}

// ── Wave Execution: ETL Anomaly Overlay ────────────────────────────
async function renderETLAnomalyOverlay(waveId) {
  const data = await API.get(`/ml/anomalies?wave=${waveId}`);
  if (!data || !data.steps) return;

  data.steps.forEach((step, i) => {
    const el = document.getElementById(`etl-step-${i}`);
    if (!el) return;
    if (step.flagged) {
      el.classList.add('ml-anomaly');
      el.title = `ANOMALY: EWMA z=${step.ewma_z} | IF=${step.if_score} | Blended=${step.blended}\n${step.explanation}`;
      // Add anomaly indicator dot
      if (!el.querySelector('.ml-anomaly-dot')) {
        const dot = document.createElement('div');
        dot.className = 'ml-anomaly-dot';
        dot.innerHTML = '&#x26A0;';
        dot.style.cssText = 'font-size:0.6rem;color:var(--amber);margin-top:4px;';
        el.appendChild(dot);
      }
    }
  });

  // Show anomaly summary below pipeline
  const resultEl = document.getElementById('etlResult');
  if (data.total_anomalies > 0 && resultEl) {
    const anomalyHtml = data.steps.filter(s => s.flagged).map(s => `
      <div style="display:flex;align-items:flex-start;gap:10px;padding:8px 0;border-bottom:1px solid var(--border);">
        <span class="badge badge-amber" style="min-width:70px;text-align:center;">${s.step}</span>
        <div style="flex:1;">
          <div style="display:flex;gap:12px;margin-bottom:4px;">
            <span style="font-family:var(--font-mono);font-size:0.58rem;color:var(--text-muted);">EWMA: <strong style="color:var(--amber)">${s.ewma_z.toFixed(1)}σ</strong></span>
            <span style="font-family:var(--font-mono);font-size:0.58rem;color:var(--text-muted);">IF: <strong style="color:var(--amber)">${s.if_score.toFixed(2)}</strong></span>
            <span style="font-family:var(--font-mono);font-size:0.58rem;color:var(--text-muted);">Blended: <strong style="color:var(--red)">${s.blended.toFixed(2)}</strong></span>
          </div>
          <div style="font-size:0.65rem;color:var(--text-standard);">${s.explanation}</div>
        </div>
      </div>
    `).join('');

    const existing = resultEl.innerHTML;
    resultEl.style.display = 'block';
    resultEl.innerHTML = existing + `
      <div class="callout amber" style="margin-top:10px;">
        <div class="callout-title">ML: ${data.total_anomalies} Anomal${data.total_anomalies === 1 ? 'y' : 'ies'} Detected (Wave ${waveId})</div>
        ${anomalyHtml}
      </div>`;
  }
}

// ── Account Explorer: ML Score Badge ───────────────────────────────
function mlScoreBadge(accountId, mlData) {
  if (!mlData) return '<span style="color:var(--text-muted);">—</span>';
  const d = mlData[accountId];
  if (!d) return '<span style="color:var(--text-muted);">—</span>';

  if (d.source === 'human_corrected') {
    return '<span class="badge ml-badge-human">Human &#x2713;</span>';
  }
  if (d.source === 'blended') {
    return `<span class="badge ml-badge-blend">Blend ${d.blended_score.toFixed(2)}</span>`;
  }
  // rule_only
  return `<span class="badge ml-badge-rule">Rule ${d.rule_score.toFixed(2)}</span>`;
}

// ── Account Profile: ML Classification Detail ──────────────────────
function mlProfileSection(accountId, mlData) {
  if (!mlData) return '';
  const d = mlData[accountId];
  if (!d) return '';

  const sourceLabel = { rule_only: 'Rule Only (ML Cold Start)', blended: 'Blended (ML Active)', human_corrected: 'Human Corrected' }[d.source] || d.source;
  const sourceColor = { rule_only: 'var(--blue)', blended: 'var(--purple)', human_corrected: 'var(--green)' }[d.source] || 'var(--text-muted)';

  let scoreBar = '';
  if (d.blended_score !== null) {
    const rPct = Math.round(d.rule_score * 100);
    const mPct = Math.round(d.ml_confidence * 100);
    scoreBar = `
      <div class="detail-row"><div class="detail-label">SCORE BAR</div><div class="detail-value">
        <div style="display:flex;align-items:center;gap:8px;">
          <span style="font-size:0.58rem;color:var(--blue);font-family:var(--font-mono);">Rules ${d.rule_score.toFixed(2)}</span>
          <div class="ml-score-bar" style="flex:1;max-width:200px;">
            <div class="ml-score-rules" style="width:${rPct}%"></div>
            <div class="ml-score-ml" style="width:${mPct}%"></div>
          </div>
          <span style="font-size:0.58rem;color:var(--purple);font-family:var(--font-mono);">ML ${d.ml_confidence.toFixed(2)}</span>
          <span style="font-size:0.62rem;color:var(--text-bright);font-weight:700;">&#x2192; ${d.blended_score.toFixed(2)}</span>
        </div>
      </div></div>`;
  }

  return `
    <div class="profile-section">
      <div class="section-label">ML CLASSIFICATION</div>
      <div class="detail-row"><div class="detail-label">SOURCE</div><div class="detail-value"><span style="color:${sourceColor};font-weight:600;">${sourceLabel}</span></div></div>
      <div class="detail-row"><div class="detail-label">RULE SCORE</div><div class="detail-value" style="font-family:var(--font-mono);">${d.rule_score.toFixed(2)}</div></div>
      <div class="detail-row"><div class="detail-label">ML CONFIDENCE</div><div class="detail-value" style="font-family:var(--font-mono);">${d.ml_confidence !== null ? d.ml_confidence.toFixed(2) : 'N/A — cold start'}</div></div>
      <div class="detail-row"><div class="detail-label">BLENDED SCORE</div><div class="detail-value" style="font-family:var(--font-mono);">${d.blended_score !== null ? d.blended_score.toFixed(2) : 'N/A'}</div></div>
      ${scoreBar}
    </div>`;
}

// ── Agent Detail: Agent 04 (ETL) ML Section ────────────────────────
async function renderAgent04MLDetail() {
  const ml = await fetchMLStatus();
  if (!ml || !ml.enabled) return '';

  const etl = ml.etl_detector;
  // Default to wave 3 which has anomalies
  const data = await API.get('/ml/anomalies?wave=3');
  const steps = data.steps || [];

  const maxBlended = Math.max(...steps.map(s => s.blended), 0.01);
  const stepBars = steps.map(s => {
    const pct = Math.round((s.blended / Math.max(maxBlended, 1)) * 100);
    const color = s.flagged ? 'var(--amber)' : 'var(--green)';
    const flag = s.flagged ? '<span style="color:var(--amber);font-weight:700;"> &#x26A0; ANOMALY</span>' : '<span style="color:var(--green);"> &#x2713;</span>';
    return `
      <div style="display:flex;align-items:center;gap:8px;padding:3px 0;">
        <span style="font-family:var(--font-mono);font-size:0.58rem;color:var(--text-muted);min-width:70px;">${s.step}</span>
        <div style="flex:1;height:6px;background:var(--bg-page);border-radius:3px;overflow:hidden;">
          <div style="width:${pct}%;height:100%;background:${color};border-radius:3px;"></div>
        </div>
        <span style="font-family:var(--font-mono);font-size:0.55rem;color:var(--text-muted);min-width:36px;text-align:right;">${s.blended.toFixed(2)}</span>
        ${flag}
      </div>`;
  }).join('');

  // Wave selector
  const waveOptions = [1,2,3,4,5].map(w => `<option value="${w}" ${w===3?'selected':''}>${w}</option>`).join('');

  return `
    <div style="margin-top:16px;padding:14px;background:var(--bg-surface);border:1px solid var(--border);border-radius:var(--radius);">
      <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:10px;">
        <span style="font-family:var(--font-mono);font-size:0.65rem;font-weight:700;color:var(--purple);letter-spacing:1px;">ML: ETL ANOMALY DETECTION</span>
        <select id="mlWaveSelect" style="background:var(--bg-card);color:var(--text-standard);border:1px solid var(--border);border-radius:4px;padding:3px 8px;font-size:0.62rem;" onchange="updateAgent04MLWave(this.value)">
          ${waveOptions}
        </select>
      </div>
      <div style="font-size:0.65rem;color:var(--text-standard);line-height:1.7;margin-bottom:10px;">
        Model: <span style="color:var(--cyan);font-family:var(--font-mono);">${etl.model_type}</span>
        &nbsp;|&nbsp; State: <span style="color:var(--green);">${etl.state}</span> (${etl.training_samples} samples)
        &nbsp;|&nbsp; Anomalies: <span style="color:var(--amber);">${etl.anomalies_detected}</span> across 5 waves
      </div>
      <div id="agent04MLStepBars">${stepBars}</div>
      <div style="font-size:0.55rem;color:var(--text-muted);margin-top:8px;font-family:var(--font-mono);">
        EWMA: ${Math.round(etl.blend_weight_ewma*100)}% weight | IF: ${Math.round(etl.blend_weight_if*100)}% weight | Threshold: blended &ge; 0.55
      </div>
    </div>`;
}

async function updateAgent04MLWave(waveId) {
  const data = await API.get(`/ml/anomalies?wave=${waveId}`);
  const steps = data.steps || [];
  const maxBlended = Math.max(...steps.map(s => s.blended), 0.01);

  const stepBars = steps.map(s => {
    const pct = Math.round((s.blended / Math.max(maxBlended, 1)) * 100);
    const color = s.flagged ? 'var(--amber)' : 'var(--green)';
    const flag = s.flagged ? '<span style="color:var(--amber);font-weight:700;"> &#x26A0; ANOMALY</span>' : '<span style="color:var(--green);"> &#x2713;</span>';
    return `
      <div style="display:flex;align-items:center;gap:8px;padding:3px 0;">
        <span style="font-family:var(--font-mono);font-size:0.58rem;color:var(--text-muted);min-width:70px;">${s.step}</span>
        <div style="flex:1;height:6px;background:var(--bg-page);border-radius:3px;overflow:hidden;">
          <div style="width:${pct}%;height:100%;background:${color};border-radius:3px;"></div>
        </div>
        <span style="font-family:var(--font-mono);font-size:0.55rem;color:var(--text-muted);min-width:36px;text-align:right;">${s.blended.toFixed(2)}</span>
        ${flag}
      </div>`;
  }).join('');

  const el = document.getElementById('agent04MLStepBars');
  if (el) el.innerHTML = stepBars;
}

// ── Agent Detail: Agent 12 (NHI Handler) ML Section ────────────────
async function renderAgent12MLDetail() {
  const ml = await fetchMLStatus();
  if (!ml || !ml.enabled) return '';

  const nhi = ml.nhi_classifier;
  const clsData = await fetchMLClassifications();
  const summary = clsData.summary || {};
  const cls = clsData.classifications || {};

  // Sample accounts for display
  const sampleIds = ['ACC-00038', 'ACC-00042', 'ACC-00044', 'ACC-00023'];
  const sampleRows = sampleIds.map(id => {
    const d = cls[id];
    if (!d) return '';
    const sourceColor = { rule_only: 'var(--blue)', blended: 'var(--purple)', human_corrected: 'var(--green)' }[d.source] || 'var(--text-muted)';
    const sourceLabel = { rule_only: 'Rule', blended: 'Blend', human_corrected: 'Human' }[d.source];
    return `
      <div style="display:flex;align-items:center;gap:8px;padding:4px 0;border-bottom:1px solid var(--border);font-size:0.6rem;">
        <span style="font-family:var(--font-mono);color:var(--text-muted);min-width:70px;">${id}</span>
        <span style="color:var(--blue);min-width:50px;">Rule:${d.rule_score.toFixed(2)}</span>
        <span style="color:var(--purple);min-width:50px;">ML:${d.ml_confidence !== null ? d.ml_confidence.toFixed(2) : 'N/A'}</span>
        <span style="color:var(--text-bright);min-width:50px;">&#x2192;${d.blended_score !== null ? d.blended_score.toFixed(2) : 'N/A'}</span>
        <span style="color:${sourceColor};font-weight:600;">${sourceLabel}</span>
      </div>`;
  }).join('');

  return `
    <div style="margin-top:16px;padding:14px;background:var(--bg-surface);border:1px solid var(--border);border-radius:var(--radius);">
      <div style="font-family:var(--font-mono);font-size:0.65rem;font-weight:700;color:var(--purple);letter-spacing:1px;margin-bottom:10px;">ML: NHI CLASSIFICATION BLENDING</div>
      <div style="font-size:0.65rem;color:var(--text-standard);line-height:1.7;margin-bottom:10px;">
        Model: <span style="color:var(--purple);font-family:var(--font-mono);">${nhi.model_type}</span>
        &nbsp;|&nbsp; State: <span style="color:var(--green);">${nhi.state}</span> (${nhi.training_samples} samples, ${nhi.human_corrections} corrections)
        &nbsp;|&nbsp; Accuracy: <span style="color:var(--green);font-weight:700;">${Math.round(nhi.accuracy*100)}%</span>
        &nbsp;|&nbsp; Blend: Rules ${Math.round(nhi.blend_weights.rules*100)}% / ML ${Math.round(nhi.blend_weights.ml*100)}%
      </div>
      <div style="display:flex;gap:12px;margin-bottom:12px;">
        <div style="background:var(--blue-dim);border:1px solid var(--blue);border-radius:var(--radius);padding:10px;flex:1;text-align:center;">
          <div style="font-size:1.1rem;font-weight:800;color:var(--blue);">${summary.rule_only || 0}</div>
          <div style="font-size:0.55rem;color:var(--text-muted);font-family:var(--font-mono);">RULE ONLY</div>
        </div>
        <div style="background:var(--purple-dim);border:1px solid var(--purple);border-radius:var(--radius);padding:10px;flex:1;text-align:center;">
          <div style="font-size:1.1rem;font-weight:800;color:var(--purple);">${summary.blended || 0}</div>
          <div style="font-size:0.55rem;color:var(--text-muted);font-family:var(--font-mono);">BLENDED</div>
        </div>
        <div style="background:var(--green-dim);border:1px solid var(--green);border-radius:var(--radius);padding:10px;flex:1;text-align:center;">
          <div style="font-size:1.1rem;font-weight:800;color:var(--green);">${summary.human_corrected || 0}</div>
          <div style="font-size:0.55rem;color:var(--text-muted);font-family:var(--font-mono);">HUMAN CORRECTED</div>
        </div>
      </div>
      <div style="font-family:var(--font-mono);font-size:0.55rem;color:var(--text-muted);letter-spacing:1px;margin-bottom:6px;">SAMPLE ACCOUNTS</div>
      ${sampleRows}
    </div>`;
}

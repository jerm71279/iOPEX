/**
 * Human-readable deliverable renderers.
 * Replaces raw JSON with structured HTML reports for non-technical stakeholders.
 */

// ── Master Dispatcher ─────────────────────────────────────────────

function renderDeliverable(name, data, format, phase) {
  if (!data || typeof data !== 'object') {
    return renderRawJSONOnly(data);
  }
  try {
    // A. Assertion/Checklist — validation reports with pass/fail checks
    if (data.assertions || (data.checks && Array.isArray(data.checks) && data.checks[0]?.passed !== undefined) ||
        (data.checks && Array.isArray(data.checks) && data.checks[0]?.status)) {
      return renderAssertion(name, data) + renderCollapsibleJSON(data);
    }

    // B. Pipeline/ETL — migration reports with batch steps
    if (data.batches && Array.isArray(data.batches) && data.batches[0]?.steps) {
      return renderPipeline(name, data) + renderCollapsibleJSON(data);
    }

    // C. Metrics/Dashboard — counts, scores, breakdowns
    if (data.summary || data.domains || data.by_risk || data.by_type ||
        (data.frameworks && Array.isArray(data.frameworks)) ||
        data.overall_score || data.traffic_progression) {
      return renderMetrics(name, data) + renderCollapsibleJSON(data);
    }

    // D. Table/List — tabular data, registries, logs
    if (data.top_dependencies || data.sequence || data.by_status ||
        data.lessons_learned || data.lost_permissions_impact ||
        data.code_packages || data.documentation_delivered ||
        data.pipeline_steps || data.discrepancy_details) {
      return renderTable(name, data) + renderCollapsibleJSON(data);
    }

    // E. Config/Status — simple key-value structures (catch-all)
    return renderConfig(name, data) + renderCollapsibleJSON(data);

  } catch (err) {
    console.error('Renderer error:', err, name, data);
    return `
      <div class="callout amber">
        <div class="callout-title">Rendering Notice</div>
        <p>Could not render structured view. Raw data shown below.</p>
      </div>
    ` + renderRawJSONOnly(data);
  }
}

// ── Renderer A: Assertion/Checklist ───────────────────────────────

function renderAssertion(name, data) {
  const items = data.assertions || data.checks || [];
  const passCount = items.filter(i => i.passed === true || i.passed === 'true' || i.status === 'pass').length;
  const failCount = items.length - passCount;
  const overall = data.overall_status || data.overall || (data.all_passed ? 'PASSED' : (failCount === 0 ? 'PASSED' : 'FAILED'));
  const isPassed = overall.toString().toUpperCase().includes('PASS');

  let html = `
    <div class="rpt-summary ${isPassed ? 'rpt-summary-pass' : 'rpt-summary-fail'}">
      <div class="rpt-summary-icon">${isPassed ? '\u2713' : '\u2717'}</div>
      <div>
        <div class="rpt-summary-status">${overall.toString().toUpperCase()}</div>
        <div class="rpt-summary-detail">${passCount} of ${items.length} checks passed${failCount > 0 ? ` \u2014 ${failCount} failed` : ''}</div>
      </div>
    </div>
  `;

  // Extra metrics if present
  if (data.sample_size || data.success_rate || data.total_accounts) {
    html += '<div class="rpt-metrics">';
    if (data.sample_size) html += metricCard('Sample Size', data.sample_size.toLocaleString());
    if (data.total_accounts) html += metricCard('Total Accounts', data.total_accounts.toLocaleString());
    if (data.migrated) html += metricCard('Migrated', data.migrated.toLocaleString(), 'var(--green)');
    if (data.excluded) html += metricCard('Excluded', data.excluded.toLocaleString(), 'var(--amber)');
    if (data.success_rate) html += metricCard('Success Rate', (data.success_rate * 100).toFixed(1) + '%', data.success_rate >= 0.95 ? 'var(--green)' : 'var(--amber)');
    html += '</div>';
  }

  html += '<div class="rpt-section-label">Validation Checks</div><div class="rpt-checklist">';

  items.forEach(item => {
    const passed = item.passed === true || item.passed === 'true' || item.status === 'pass';
    const label = item.name ? item.name.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase()) : item.agent ? `Agent ${item.agent} \u2014 ${item.name}` : '';
    html += `
      <div class="rpt-check-item">
        <div class="health-dot ${passed ? 'dot-green' : 'dot-red'}"></div>
        <div style="flex:1">
          <div class="rpt-check-name">${label}</div>
          <div class="rpt-check-detail">${item.detail || item.target || ''}</div>
        </div>
      </div>
    `;
  });

  html += '</div>';
  return html;
}

// ── Renderer B: Pipeline/ETL Steps ────────────────────────────────

function renderPipeline(name, data) {
  const total = data.total_accounts || 0;
  const migrated = data.migrated || 0;
  const failed = data.failed || 0;
  const rate = total > 0 ? ((migrated / total) * 100).toFixed(1) : '0';
  const duration = data.duration_minutes;

  let html = '<div class="rpt-metrics">';
  html += metricCard('Total Accounts', total.toLocaleString());
  html += metricCard('Migrated', migrated.toLocaleString(), 'var(--green)');
  html += metricCard('Failed', failed.toLocaleString(), failed > 0 ? 'var(--red)' : 'var(--text-muted)');
  html += metricCard('Success Rate', rate + '%', parseFloat(rate) >= 95 ? 'var(--green)' : 'var(--amber)');
  if (duration) html += metricCard('Duration', duration + ' min');
  html += '</div>';

  // Wave/status info
  if (data.wave) {
    html += `<div class="rpt-section-label">Wave ${data.wave} \u2014 ${(data.status || 'complete').toUpperCase()}</div>`;
  }

  // Batches
  data.batches.forEach(batch => {
    html += `
      <div class="panel" style="margin-bottom:14px;">
        <div class="panel-header">
          <div class="panel-title">Batch ${batch.batch_id} \u2014 ${batch.size} accounts</div>
          <span class="badge ${batch.failed > 0 ? 'badge-amber' : 'badge-green'}">${batch.success}/${batch.size} success</span>
        </div>
        <div class="panel-body" style="padding:14px;">
    `;
    batch.steps.forEach(step => {
      const pct = step.status === 'done' ? 100 : (step.status === 'active' ? 50 : 0);
      const durSec = (step.duration_ms / 1000).toFixed(1);
      html += `
        <div class="rpt-step">
          <div class="rpt-step-header">
            <span class="rpt-step-name">${step.step}</span>
            <span class="rpt-step-dur">${durSec}s</span>
          </div>
          <div class="rpt-progress"><div class="rpt-progress-fill" style="width:${pct}%"></div></div>
          <div class="rpt-step-detail">${step.detail}</div>
        </div>
      `;
    });
    html += '</div></div>';
  });

  // Failed accounts
  if (data.failed_accounts && data.failed_accounts.length > 0) {
    html += `
      <div class="callout amber" style="margin-top:8px;">
        <div class="callout-title">Failed Accounts (${data.failed_accounts.length})</div>
        <table class="rpt-table" style="margin-top:10px;">
          <thead><tr><th>Account ID</th><th>Name</th><th>Reason</th></tr></thead>
          <tbody>
    `;
    data.failed_accounts.forEach(a => {
      html += `<tr><td class="rpt-mono">${a.id}</td><td>${a.name}</td><td style="color:var(--amber)">${a.reason}</td></tr>`;
    });
    html += '</tbody></table></div>';
  }

  // Extra sections (integration updates, NHI rotation, reconciliation)
  if (data.integration_updates) {
    const iu = data.integration_updates;
    html += '<div class="rpt-section-label" style="margin-top:16px">Integration Updates</div><div class="rpt-metrics">';
    html += metricCard('Total Apps', iu.total_apps);
    html += metricCard('Code Generated', iu.code_generated);
    html += metricCard('Deployed', iu.deployed, 'var(--green)');
    html += metricCard('Pending', iu.pending_deploy, iu.pending_deploy > 0 ? 'var(--amber)' : 'var(--text-muted)');
    html += '</div>';
  }

  if (data.nhi_rotation_status) {
    const nr = data.nhi_rotation_status;
    html += '<div class="rpt-section-label" style="margin-top:16px">NHI Rotation Status</div><div class="rpt-metrics">';
    html += metricCard('Verified', nr.rotation_verified, 'var(--green)');
    html += metricCard('Pending', nr.rotation_pending, nr.rotation_pending > 0 ? 'var(--amber)' : 'var(--text-muted)');
    html += '</div>';
  }

  if (data.reconciliation) {
    const rc = data.reconciliation;
    html += `
      <div class="callout teal" style="margin-top:16px;">
        <div class="callout-title">Final Reconciliation</div>
        <p>Source: ${rc.source_total.toLocaleString()} \u2192 Target: ${rc.target_total.toLocaleString()} (${rc.coverage_pct}% coverage)</p>
        <p style="margin-top:6px">${rc.excluded} accounts excluded:</p>
        <div style="margin-top:6px">
    `;
    (rc.exclusion_reasons || []).forEach(r => {
      html += `<div class="rpt-check-detail" style="margin-bottom:2px">\u2022 ${r.reason} (${r.count})</div>`;
    });
    html += '</div></div>';
  }

  return html;
}

// ── Renderer C: Metrics/Dashboard ─────────────────────────────────

function renderMetrics(name, data) {
  let html = '';

  // Overall score callout
  if (data.overall_score !== undefined) {
    const score = data.overall_score;
    const color = score >= 8 ? 'teal' : score >= 6 ? 'amber' : 'red';
    html += `
      <div class="callout ${color}">
        <div class="callout-title">Overall Score: ${score} / 10</div>
      </div>
    `;
  }

  // Overall status
  if (data.overall_status && !data.overall_score) {
    const isPassed = data.overall_status.toUpperCase().includes('PASS') || data.overall_status.toUpperCase().includes('COMPLIANT');
    html += `
      <div class="rpt-summary ${isPassed ? 'rpt-summary-pass' : 'rpt-summary-fail'}">
        <div class="rpt-summary-icon">${isPassed ? '\u2713' : '\u2717'}</div>
        <div>
          <div class="rpt-summary-status">${data.overall_status.toUpperCase()}</div>
        </div>
      </div>
    `;
  }

  // Summary metrics
  if (data.summary) {
    html += '<div class="rpt-metrics">';
    Object.entries(data.summary).forEach(([key, value]) => {
      if (typeof value === 'number') {
        const label = key.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
        html += metricCard(label, value.toLocaleString());
      }
    });
    html += '</div>';
  }

  // Standalone numeric fields at top level
  if (!data.summary) {
    const numericKeys = Object.entries(data).filter(([k, v]) => typeof v === 'number' && !k.startsWith('overall'));
    if (numericKeys.length > 0 && numericKeys.length <= 8) {
      html += '<div class="rpt-metrics">';
      numericKeys.forEach(([key, value]) => {
        const label = key.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
        html += metricCard(label, value.toLocaleString());
      });
      html += '</div>';
    }
  }

  // Domains (gap analysis)
  if (data.domains) {
    html += '<div class="rpt-section-label">Domain Scores</div><div class="rpt-checklist">';
    data.domains.forEach(d => {
      const pct = ((d.score / d.max) * 100).toFixed(0);
      const dotClass = d.status === 'good' ? 'dot-green' : d.status === 'warning' ? 'dot-amber' : 'dot-red';
      html += `
        <div class="rpt-check-item">
          <div class="health-dot ${dotClass}"></div>
          <div style="flex:1">
            <div class="rpt-check-name">${d.name}</div>
            <div class="rpt-check-detail">${d.score}/${d.max} (${pct}%)</div>
          </div>
          <div style="width:100px">
            <div class="rpt-progress"><div class="rpt-progress-fill ${d.status === 'good' ? '' : d.status === 'warning' ? 'amber' : 'red'}" style="width:${pct}%"></div></div>
          </div>
        </div>
      `;
    });
    html += '</div>';
  }

  // Risk distribution
  if (data.by_risk) {
    html += '<div class="rpt-section-label">Risk Distribution</div><div class="rpt-metrics">';
    Object.entries(data.by_risk).forEach(([risk, count]) => {
      const color = (risk === 'critical' || risk === 'high') ? 'var(--red)' : risk === 'medium' ? 'var(--amber)' : 'var(--green)';
      html += metricCard(risk.toUpperCase(), count, color);
    });
    html += '</div>';
  }

  // Type distribution
  if (data.by_type && typeof data.by_type === 'object' && typeof Object.values(data.by_type)[0] === 'number') {
    html += '<div class="rpt-section-label">By Type</div><div class="rpt-metrics">';
    Object.entries(data.by_type).forEach(([type, count]) => {
      html += metricCard(type, count);
    });
    html += '</div>';
  }

  // Integration by_type (nested objects)
  if (data.by_type && typeof data.by_type === 'object' && typeof Object.values(data.by_type)[0] === 'object') {
    html += '<div class="rpt-section-label">Integration Breakdown</div>';
    html += '<table class="rpt-table"><thead><tr><th>Type</th><th>Total</th><th>Repointed</th><th>Pending</th></tr></thead><tbody>';
    Object.entries(data.by_type).forEach(([type, info]) => {
      html += `<tr><td class="rpt-mono">${type}</td><td>${info.total}</td><td style="color:var(--green)">${info.repointed}</td><td style="color:${info.pending > 0 ? 'var(--amber)' : 'var(--text-muted)'}">${info.pending}</td></tr>`;
    });
    html += '</tbody></table>';
  }

  // By strategy (NHI rotation)
  if (data.by_strategy) {
    html += '<div class="rpt-section-label">Rotation Strategies</div>';
    html += '<table class="rpt-table"><thead><tr><th>Strategy</th><th>Count</th><th>Active</th><th>Interval</th></tr></thead><tbody>';
    Object.entries(data.by_strategy).forEach(([strategy, info]) => {
      const label = strategy.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
      html += `<tr><td>${label}</td><td>${info.count}</td><td style="color:var(--green)">${info.active}</td><td>${info.interval_days} days</td></tr>`;
    });
    html += '</tbody></table>';
  }

  // Permission stats
  if (data.permission_stats) {
    html += '<div class="rpt-section-label">Permission Distribution</div><div class="rpt-metrics">';
    Object.entries(data.permission_stats).forEach(([role, count]) => {
      const label = role.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
      html += metricCard(label, count);
    });
    html += '</div>';
    if (data.escalation_flags) {
      html += `<div class="callout amber" style="margin-top:12px"><div class="callout-title">${data.escalation_flags} Escalation Flags</div><p>Members with permission changes that require security review.</p></div>`;
    }
  }

  // Compliance gaps
  if (data.compliance_gaps) {
    html += `<div class="callout red" style="margin-top:16px"><div class="callout-title">Compliance Gaps (${data.compliance_gaps.length})</div>`;
    data.compliance_gaps.forEach(g => {
      html += `
        <div style="margin-top:8px;padding:8px;background:var(--bg-surface);border-radius:var(--radius)">
          <span class="badge ${g.severity === 'high' ? 'badge-red' : 'badge-amber'}">${g.severity.toUpperCase()}</span>
          <strong style="margin-left:6px;font-size:0.72rem">${g.framework} \u2014 ${g.requirement}</strong>
          <div style="font-size:0.68rem;color:var(--text-muted);margin-top:4px">${g.desc}</div>
        </div>
      `;
    });
    html += '</div>';
  }

  // Compliance frameworks (array format)
  if (data.frameworks && Array.isArray(data.frameworks)) {
    html += '<div class="rpt-section-label">Compliance Frameworks</div>';
    data.frameworks.forEach(fw => {
      const color = fw.failed === 0 ? 'teal' : 'amber';
      html += `
        <div class="callout ${color}" style="margin-bottom:12px">
          <div class="callout-title">${fw.name}</div>
          <p>${fw.passed}/${fw.requirements_checked} requirements passed${fw.failed > 0 ? ` \u2014 <strong style="color:var(--amber)">${fw.failed} failed</strong>` : ''}</p>
      `;
      if (fw.key_findings) {
        html += '<div style="margin-top:10px">';
        fw.key_findings.forEach(f => {
          const icon = f.status === 'pass' ? '\u2713' : f.status === 'advisory' ? '\u26A0' : '\u2717';
          const color = f.status === 'pass' ? 'var(--green)' : f.status === 'advisory' ? 'var(--amber)' : 'var(--red)';
          html += `<div style="font-size:0.7rem;margin-bottom:4px"><span style="color:${color}">${icon}</span> <strong>${f.req}:</strong> ${f.evidence}</div>`;
        });
        html += '</div>';
      }
      html += '</div>';
    });
  }

  // Audit trail
  if (data.audit_trail) {
    const at = data.audit_trail;
    html += '<div class="rpt-section-label">Audit Trail</div><div class="rpt-metrics">';
    html += metricCard('Total Events', at.total_events?.toLocaleString());
    html += metricCard('SIEM Forwarded', at.siem_forwarded?.toLocaleString(), 'var(--green)');
    html += metricCard('Hash Chain', at.hash_chain_valid ? 'Valid' : 'INVALID', at.hash_chain_valid ? 'var(--green)' : 'var(--red)');
    html += '</div>';
  }

  // Traffic progression (parallel run)
  if (data.traffic_progression) {
    html += '<div class="rpt-section-label">Traffic Progression</div>';
    html += '<table class="rpt-table"><thead><tr><th>Week</th><th>Target %</th><th>Error Rate</th><th>Latency (p99)</th></tr></thead><tbody>';
    data.traffic_progression.forEach(t => {
      html += `<tr><td>W${t.week}</td><td style="font-weight:700;color:var(--text-bright)">${t.target_pct}%</td><td>${(t.error_rate * 100).toFixed(2)}%</td><td>${t.latency_p99_ms}ms</td></tr>`;
    });
    html += '</tbody></table>';
  }

  // Discrepancies
  if (data.discrepancy_details) {
    html += '<div class="rpt-section-label" style="margin-top:16px">Discrepancies</div>';
    html += '<table class="rpt-table"><thead><tr><th>Week</th><th>Type</th><th>Count</th><th>Resolution</th></tr></thead><tbody>';
    data.discrepancy_details.forEach(d => {
      html += `<tr><td>W${d.week}</td><td>${d.type.replace(/_/g, ' ')}</td><td>${d.count}</td><td style="color:var(--green)">${d.resolution}</td></tr>`;
    });
    html += '</tbody></table>';
  }

  // Recommendation
  if (data.recommendation) {
    html += `<div class="callout teal" style="margin-top:16px"><div class="callout-title">Recommendation</div><p>${data.recommendation}</p></div>`;
  }

  // Rotation policies
  if (data.rotation_policies) {
    html += '<div class="rpt-section-label">Rotation Policies</div>';
    html += '<table class="rpt-table"><thead><tr><th>Type</th><th>Interval</th><th>Strategy</th><th>Downtime</th></tr></thead><tbody>';
    data.rotation_policies.forEach(p => {
      html += `<tr><td>${p.type}</td><td>${p.interval_days} days</td><td>${p.strategy.replace(/_/g, ' ')}</td><td>${p.requires_downtime ? 'Yes' : 'No'}</td></tr>`;
    });
    html += '</tbody></table>';
  }

  // Pending details
  if (data.pending_details) {
    html += `<div class="callout amber" style="margin-top:12px"><div class="callout-title">Pending (${data.pending_details.length})</div>`;
    data.pending_details.forEach(p => {
      html += `<div style="font-size:0.7rem;margin-top:6px"><strong>${p.name}</strong> \u2014 ${p.reason}</div>`;
    });
    html += '</div>';
  }

  // First rotation results
  if (data.first_rotation_results) {
    const fr = data.first_rotation_results;
    html += '<div class="rpt-section-label" style="margin-top:16px">First Rotation Results</div><div class="rpt-metrics">';
    html += metricCard('Attempted', fr.attempted);
    html += metricCard('Success', fr.success, 'var(--green)');
    html += metricCard('Failed', fr.failed, fr.failed > 0 ? 'var(--red)' : 'var(--text-muted)');
    html += '</div>';
    if (fr.failures && fr.failures.length > 0) {
      html += '<table class="rpt-table" style="margin-top:8px"><thead><tr><th>ID</th><th>Name</th><th>Reason</th></tr></thead><tbody>';
      fr.failures.forEach(f => {
        html += `<tr><td class="rpt-mono">${f.id}</td><td>${f.name}</td><td style="color:var(--amber)">${f.reason}</td></tr>`;
      });
      html += '</tbody></table>';
    }
  }

  // Safes list (discovery manifest)
  if (data.safes) {
    html += '<div class="rpt-section-label">Top Safes</div>';
    html += '<table class="rpt-table"><thead><tr><th>Safe Name</th><th>Members</th><th>Accounts</th></tr></thead><tbody>';
    data.safes.forEach(s => {
      html += `<tr><td style="font-weight:600">${s.name}</td><td>${s.member_count}</td><td>${s.account_count}</td></tr>`;
    });
    html += '</tbody></table>';
  }

  // Platforms list
  if (data.platforms) {
    html += '<div class="rpt-section-label" style="margin-top:16px">Platforms</div>';
    html += '<table class="rpt-table"><thead><tr><th>Platform</th><th>ID</th><th>Accounts</th></tr></thead><tbody>';
    data.platforms.forEach(p => {
      html += `<tr><td>${p.name}</td><td class="rpt-mono">${p.id}</td><td>${p.count}</td></tr>`;
    });
    html += '</tbody></table>';
  }

  // NHIs detected
  if (data.nhis) {
    html += '<div class="rpt-section-label" style="margin-top:16px">Non-Human Identities Detected</div>';
    html += '<table class="rpt-table"><thead><tr><th>Name</th><th>Type</th><th>Safe</th><th>Confidence</th></tr></thead><tbody>';
    data.nhis.forEach(n => {
      html += `<tr><td class="rpt-mono">${n.name}</td><td><span class="badge badge-cyan">${n.type}</span></td><td>${n.safe}</td><td style="font-weight:700;color:${n.confidence >= 0.9 ? 'var(--green)' : 'var(--amber)'}">${(n.confidence * 100).toFixed(0)}%</td></tr>`;
    });
    html += '</tbody></table>';
  }

  // Integrations
  if (data.integrations) {
    html += '<div class="rpt-section-label" style="margin-top:16px">Integrations</div>';
    html += '<table class="rpt-table"><thead><tr><th>App</th><th>Type</th><th>Protocol</th><th>Auth</th></tr></thead><tbody>';
    data.integrations.forEach(i => {
      html += `<tr><td>${i.app_name}</td><td><span class="badge badge-muted">${i.type}</span></td><td>${i.protocol}</td><td>${i.auth}</td></tr>`;
    });
    html += '</tbody></table>';
  }

  // Warnings
  if (data.warnings) {
    html += `<div class="callout amber" style="margin-top:16px"><div class="callout-title">Warnings (${data.warnings.length})</div>`;
    data.warnings.forEach(w => {
      html += `<div style="font-size:0.7rem;margin-top:6px"><strong>${w.type.replace(/_/g, ' ')}</strong> (${w.count}) \u2014 ${w.detail}</div>`;
    });
    html += '</div>';
  }

  return html;
}

// ── Renderer D: Table/List ────────────────────────────────────────

function renderTable(name, data) {
  let html = '';

  // Summary numbers at top
  const summaryItems = [];
  if (data.total_dependencies) summaryItems.push(`${data.total_dependencies} dependencies mapped`);
  if (data.total_integrations) summaryItems.push(`${data.total_integrations} integrations tracked`);
  if (data.total_members) summaryItems.push(`${data.total_members} members audited`);
  if (data.total_applications) summaryItems.push(`${data.total_applications} applications`);
  if (data.cutover_complete) summaryItems.push(`${data.cutover_complete} cutover complete`);
  if (data.onboarded) summaryItems.push(`${data.onboarded} onboarded`);
  if (data.containers_created) summaryItems.push(`${data.containers_created} containers created`);
  if (data.project_status) summaryItems.push(data.project_status);

  if (summaryItems.length > 0) {
    html += `<div class="callout teal"><div class="callout-title">Summary</div><p>${summaryItems.join(' \u2022 ')}</p></div>`;
  }

  // Overall status
  if (data.overall && !data.overall_score) {
    const overall = data.overall.toString().toUpperCase();
    html += `<div class="rpt-summary rpt-summary-pass"><div class="rpt-summary-icon">\u2713</div><div><div class="rpt-summary-status">${overall}</div></div></div>`;
  }

  if (data.overall_status && data.overall_status !== 'PASSED') {
    const isGood = data.overall_status.includes('COMPLIANT') || data.overall_status.includes('COMPLETE');
    html += `<div class="rpt-summary ${isGood ? 'rpt-summary-pass' : 'rpt-summary-fail'}"><div class="rpt-summary-icon">${isGood ? '\u2713' : '\u2717'}</div><div><div class="rpt-summary-status">${data.overall_status}</div></div></div>`;
  }

  // Metrics
  const numFields = Object.entries(data).filter(([k, v]) => typeof v === 'number' && !['total_dependencies'].includes(k));
  if (numFields.length > 0 && numFields.length <= 8) {
    html += '<div class="rpt-metrics">';
    numFields.forEach(([key, value]) => {
      const label = key.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
      const color = key.includes('failed') || key.includes('escalation') ? 'var(--red)' : key.includes('success') || key.includes('verified') || key.includes('onboarded') ? 'var(--green)' : undefined;
      html += metricCard(label, value.toLocaleString(), color);
    });
    html += '</div>';
  }

  // Dependency types
  if (data.dependency_types) {
    html += '<div class="rpt-section-label">Dependency Types</div><div class="rpt-metrics">';
    Object.entries(data.dependency_types).forEach(([type, count]) => {
      html += metricCard(type.replace(/_/g, ' '), count);
    });
    html += '</div>';
  }

  // Top dependencies
  if (data.top_dependencies) {
    html += '<div class="rpt-section-label">Top Dependencies</div>';
    html += '<table class="rpt-table"><thead><tr><th>Account</th><th>Name</th><th>Consumers</th><th>Count</th></tr></thead><tbody>';
    data.top_dependencies.forEach(d => {
      html += `<tr><td class="rpt-mono">${d.account_id}</td><td style="font-weight:600">${d.name}</td><td style="font-size:0.68rem">${d.consumers.join(', ')}</td><td style="text-align:center;font-weight:700">${d.dep_count}</td></tr>`;
    });
    html += '</tbody></table>';
  }

  // Sequence (decommission log)
  if (data.sequence) {
    html += '<div class="rpt-section-label">Decommission Sequence</div>';
    data.sequence.forEach(s => {
      const dotClass = s.status === 'decommissioned' ? 'dot-green' : s.status === 'read-only-archive' ? 'dot-amber' : 'dot-blue';
      html += `
        <div class="rpt-check-item" style="margin-bottom:10px">
          <div class="health-dot ${dotClass}"></div>
          <div style="flex:1">
            <div class="rpt-check-name">${s.component}</div>
            <div class="rpt-check-detail">${s.status.replace(/-/g, ' ')} \u2014 ${s.date} \u2014 Approved by: ${s.approver}</div>
            <div class="rpt-check-detail" style="color:var(--text-standard)">${s.notes}</div>
          </div>
        </div>
      `;
    });
  }

  // Infrastructure freed
  if (data.infrastructure_freed) {
    const inf = data.infrastructure_freed;
    html += '<div class="rpt-section-label" style="margin-top:16px">Infrastructure Freed</div><div class="rpt-metrics">';
    html += metricCard('Servers', inf.servers);
    html += metricCard('vCPUs', inf.vcpus);
    html += metricCard('RAM', inf.ram_gb + ' GB');
    html += metricCard('Storage', inf.storage_tb + ' TB');
    html += metricCard('Annual Savings', '$' + inf.annual_savings_usd.toLocaleString(), 'var(--green)');
    html += '</div>';
  }

  // Lost permissions impact
  if (data.lost_permissions_impact) {
    html += '<div class="rpt-section-label">Permission Mapping Impact</div>';
    Object.entries(data.lost_permissions_impact).forEach(([perm, info]) => {
      const dotClass = info.risk === 'medium' ? 'dot-amber' : 'dot-green';
      html += `
        <div class="rpt-check-item" style="margin-bottom:8px">
          <div class="health-dot ${dotClass}"></div>
          <div style="flex:1">
            <div class="rpt-check-name">${perm.replace(/([A-Z])/g, ' $1').trim()}</div>
            <div class="rpt-check-detail">${info.affected_members} members affected \u2014 Risk: ${info.risk}</div>
            <div class="rpt-check-detail" style="color:var(--text-standard)">${info.mitigation}</div>
          </div>
        </div>
      `;
    });
  }

  // Escalation details
  if (data.escalation_details) {
    html += `<div class="callout amber" style="margin-top:16px"><div class="callout-title">Escalation Details (${data.escalation_details.length})</div>`;
    html += '<table class="rpt-table" style="margin-top:10px"><thead><tr><th>Member</th><th>Safe</th><th>Target Role</th><th>Risk</th></tr></thead><tbody>';
    data.escalation_details.forEach(e => {
      html += `<tr><td class="rpt-mono">${e.member}</td><td>${e.safe}</td><td><span class="badge badge-amber">${e.target_role}</span></td><td style="font-size:0.65rem;color:var(--amber)">${e.risk}</td></tr>`;
    });
    html += '</tbody></table></div>';
  }

  // Summary by role
  if (data.summary_by_role) {
    html += '<div class="rpt-section-label" style="margin-top:16px">Assignment Summary</div><div class="rpt-metrics">';
    Object.entries(data.summary_by_role).forEach(([role, count]) => html += metricCard(role, count));
    html += '</div>';
  }

  // By status (integration cutover)
  if (data.by_status) {
    html += '<div class="rpt-section-label">Application Status</div>';
    html += '<table class="rpt-table"><thead><tr><th>Application</th><th>Status</th><th>Sign-off</th><th>Rollback</th></tr></thead><tbody>';
    data.by_status.forEach(s => {
      const statusBadge = s.status === 'complete' ? 'badge-green' : 'badge-amber';
      html += `<tr><td style="font-weight:600">${s.app}</td><td><span class="badge ${statusBadge}">${s.status.toUpperCase()}</span></td><td>${s.signoff || '\u2014'}</td><td>${s.rollback_available ? '\u2713' : '\u2014'}</td></tr>`;
    });
    html += '</tbody></table>';
  }

  // Feature flag status
  if (data.feature_flag_status) {
    const ff = data.feature_flag_status;
    html += '<div class="rpt-section-label" style="margin-top:16px">Feature Flags</div><div class="rpt-metrics">';
    html += metricCard('Total Flags', ff.total_flags);
    html += metricCard('Pointing to Target', ff.pointing_to_target, 'var(--green)');
    html += metricCard('Pointing to Source', ff.pointing_to_source, ff.pointing_to_source > 0 ? 'var(--amber)' : 'var(--text-muted)');
    html += metricCard('Rollback Tested', ff.rollback_tested, 'var(--green)');
    html += '</div>';
  }

  // Pipeline steps (onboarding)
  if (data.pipeline_steps) {
    html += '<div class="rpt-section-label">Pipeline Steps</div>';
    data.pipeline_steps.forEach(s => {
      const total = s.success + s.failed;
      const pct = total > 0 ? (s.success / total * 100) : 100;
      html += `
        <div class="rpt-step">
          <div class="rpt-step-header">
            <span class="rpt-step-name">${s.step}</span>
            <span class="rpt-step-dur">${s.success}/${total}${s.failed > 0 ? ` <span style="color:var(--red)">(${s.failed} failed)</span>` : ''}</span>
          </div>
          <div class="rpt-progress"><div class="rpt-progress-fill ${pct < 100 ? 'amber' : ''}" style="width:${pct}%"></div></div>
        </div>
      `;
    });
  }

  // Pending apps
  if (data.pending_apps) {
    html += `<div class="callout amber" style="margin-top:16px"><div class="callout-title">Pending Review (${data.pending_apps.length})</div>`;
    data.pending_apps.forEach(a => {
      html += `<div style="font-size:0.7rem;margin-top:6px"><strong>${a.app}</strong> \u2014 ${a.reason}</div>`;
    });
    html += '</div>';
  }

  // Code packages
  if (data.code_packages) {
    html += '<div class="rpt-section-label" style="margin-top:16px">Code Packages</div>';
    html += '<table class="rpt-table"><thead><tr><th>Application</th><th>Language</th><th>Status</th><th>Rollback</th></tr></thead><tbody>';
    data.code_packages.forEach(p => {
      const statusBadge = p.status === 'deployed' ? 'badge-green' : 'badge-amber';
      html += `<tr><td style="font-weight:600">${p.app}</td><td><span class="badge badge-cyan">${p.language}</span></td><td><span class="badge ${statusBadge}">${p.status.toUpperCase()}</span></td><td>${p.rollback_flag ? '\u2713' : '\u2014'}</td></tr>`;
    });
    html += '</tbody></table>';
  }

  // Frameworks (dict format in final_compliance)
  if (data.frameworks && !Array.isArray(data.frameworks)) {
    html += '<div class="rpt-section-label">Compliance Frameworks</div>';
    html += '<table class="rpt-table"><thead><tr><th>Framework</th><th>Status</th><th>Requirements</th><th>Passed</th></tr></thead><tbody>';
    Object.entries(data.frameworks).forEach(([fw, info]) => {
      const statusBadge = info.status === 'pass' ? 'badge-green' : 'badge-red';
      html += `<tr><td style="font-weight:600">${fw}</td><td><span class="badge ${statusBadge}">${info.status.toUpperCase()}</span></td><td>${info.requirements}</td><td style="color:var(--green)">${info.passed}</td></tr>`;
    });
    html += '</tbody></table>';
  }

  // Risk acceptances
  if (data.risk_acceptances) {
    html += `<div class="callout amber" style="margin-top:16px"><div class="callout-title">Risk Acceptances (${data.risk_acceptances.length})</div>`;
    data.risk_acceptances.forEach(r => {
      html += `<div style="font-size:0.7rem;margin-top:8px;padding:8px;background:var(--bg-surface);border-radius:var(--radius)"><div style="font-weight:600">${r.risk}</div><div style="color:var(--text-muted);margin-top:2px">Accepted by: ${r.accepted_by} \u2014 ${r.date}</div></div>`;
    });
    html += '</div>';
  }

  // Evidence package
  if (data.evidence_package) {
    const ep = data.evidence_package;
    html += '<div class="rpt-section-label" style="margin-top:16px">Evidence Package</div><div class="rpt-metrics">';
    html += metricCard('Files', ep.files);
    html += metricCard('Size', ep.total_size_mb + ' MB');
    html += '</div>';
    if (ep.signed_by) {
      html += `<div style="font-size:0.68rem;color:var(--text-muted);margin-top:6px">Signed by: ${ep.signed_by.join(', ')}</div>`;
    }
  }

  // Migration summary (close-out)
  if (data.migration_summary) {
    const ms = data.migration_summary;
    html += '<div class="rpt-section-label">Migration Summary</div><div class="rpt-metrics">';
    html += metricCard('Source', ms.source || '');
    html += metricCard('Accounts', ms.total_accounts?.toLocaleString());
    html += metricCard('Migrated', ms.migrated?.toLocaleString(), 'var(--green)');
    html += metricCard('Success Rate', ((ms.success_rate || 0) * 100).toFixed(1) + '%', 'var(--green)');
    html += metricCard('Waves', ms.total_waves);
    html += metricCard('Gates Passed', ms.total_gates_passed);
    html += '</div>';
  }

  // Key metrics
  if (data.key_metrics) {
    html += '<div class="rpt-section-label" style="margin-top:16px">Key Metrics</div><div class="rpt-metrics">';
    Object.entries(data.key_metrics).forEach(([key, value]) => {
      const label = key.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
      html += metricCard(label, typeof value === 'number' ? value.toLocaleString() : value);
    });
    html += '</div>';
  }

  // Lessons learned
  if (data.lessons_learned) {
    html += '<div class="rpt-section-label" style="margin-top:16px">Lessons Learned</div>';
    html += '<div style="padding:0 4px">';
    data.lessons_learned.forEach((l, i) => {
      html += `<div style="font-size:0.72rem;margin-bottom:8px;padding:8px;background:var(--bg-surface);border-radius:var(--radius);border-left:3px solid var(--teal)"><strong>${i + 1}.</strong> ${l}</div>`;
    });
    html += '</div>';
  }

  // Recommendations
  if (data.recommendations) {
    html += '<div class="rpt-section-label" style="margin-top:16px">Recommendations</div>';
    html += '<div style="padding:0 4px">';
    data.recommendations.forEach((r, i) => {
      html += `<div style="font-size:0.72rem;margin-bottom:8px;padding:8px;background:var(--bg-surface);border-radius:var(--radius);border-left:3px solid var(--amber)"><strong>${i + 1}.</strong> ${r}</div>`;
    });
    html += '</div>';
  }

  // Documentation delivered
  if (data.documentation_delivered) {
    html += '<div class="rpt-section-label">Documentation Delivered</div>';
    data.documentation_delivered.forEach(d => {
      html += `<div class="rpt-check-item"><div class="health-dot dot-green"></div><div class="rpt-check-name">${d}</div></div>`;
    });
  }

  // Monitoring configured
  if (data.monitoring_configured) {
    html += '<div class="rpt-section-label" style="margin-top:16px">Monitoring Configured</div>';
    html += '<table class="rpt-table"><thead><tr><th>Check</th><th>Interval</th><th>Alert Channel</th></tr></thead><tbody>';
    data.monitoring_configured.forEach(m => {
      html += `<tr><td>${m.check}</td><td>${m.interval}</td><td><span class="badge badge-cyan">${m.alert}</span></td></tr>`;
    });
    html += '</tbody></table>';
  }

  // Knowledge transfer
  if (data.knowledge_transfer) {
    const kt = data.knowledge_transfer;
    html += '<div class="rpt-section-label" style="margin-top:16px">Knowledge Transfer</div><div class="rpt-metrics">';
    html += metricCard('Sessions', kt.sessions);
    html += metricCard('Total Hours', kt.total_hours);
    html += metricCard('Attendees', kt.attendees);
    html += '</div>';
    if (kt.topics) {
      kt.topics.forEach(t => {
        html += `<div class="rpt-check-item"><div class="health-dot dot-green"></div><div class="rpt-check-name">${t}</div></div>`;
      });
    }
  }

  // Custom platforms (platform validation)
  if (data.custom_platforms) {
    html += '<div class="rpt-section-label">Custom Platforms</div>';
    html += '<table class="rpt-table"><thead><tr><th>Source</th><th>Status</th><th>Template</th></tr></thead><tbody>';
    data.custom_platforms.forEach(p => {
      const statusBadge = p.status === 'template_created' ? 'badge-green' : 'badge-amber';
      html += `<tr><td class="rpt-mono">${p.source}</td><td><span class="badge ${statusBadge}">${p.status.replace(/_/g, ' ')}</span></td><td>${p.template || '\u2014'}</td></tr>`;
    });
    html += '</tbody></table>';
  }

  return html;
}

// ── Renderer E: Config/Status ─────────────────────────────────────

function renderConfig(name, data) {
  let html = '<div style="padding:4px 0">';

  Object.entries(data).forEach(([key, value]) => {
    const label = key.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());

    if (Array.isArray(value)) {
      html += `<div class="rpt-config-row"><div class="rpt-config-label">${label}</div><div class="rpt-config-value">`;
      value.forEach(v => {
        if (typeof v === 'object') {
          html += `<div style="margin-bottom:4px;padding:6px;background:var(--bg-surface);border-radius:var(--radius);font-size:0.68rem">`;
          Object.entries(v).forEach(([k2, v2]) => {
            html += `<span style="color:var(--text-muted)">${k2.replace(/_/g, ' ')}:</span> <strong>${v2}</strong> `;
          });
          html += '</div>';
        } else {
          html += `<div style="margin-bottom:2px;font-size:0.72rem">\u2022 ${v}</div>`;
        }
      });
      html += '</div></div>';
    } else if (typeof value === 'object' && value !== null) {
      html += `<div class="rpt-config-row" style="flex-direction:column;align-items:flex-start"><div class="rpt-config-label">${label}</div><div style="margin-left:16px;margin-top:6px;width:100%">`;
      Object.entries(value).forEach(([k2, v2]) => {
        const l2 = k2.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
        if (typeof v2 === 'object' && v2 !== null) {
          html += `<div class="rpt-config-row" style="flex-direction:column;align-items:flex-start;margin-bottom:6px"><div class="rpt-config-label">${l2}</div><div style="margin-left:16px">`;
          Object.entries(v2).forEach(([k3, v3]) => {
            const l3 = k3.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
            html += `<div class="rpt-config-row"><div class="rpt-config-label">${l3}</div><div class="rpt-config-value">${formatConfigValue(v3)}</div></div>`;
          });
          html += '</div></div>';
        } else {
          html += `<div class="rpt-config-row"><div class="rpt-config-label">${l2}</div><div class="rpt-config-value">${formatConfigValue(v2)}</div></div>`;
        }
      });
      html += '</div></div>';
    } else {
      html += `<div class="rpt-config-row"><div class="rpt-config-label">${label}</div><div class="rpt-config-value">${formatConfigValue(value)}</div></div>`;
    }
  });

  html += '</div>';
  return html;
}

function formatConfigValue(v) {
  if (typeof v === 'boolean') return v ? '<span style="color:var(--green)">\u2713 Yes</span>' : '<span style="color:var(--red)">\u2717 No</span>';
  if (typeof v === 'number') return `<strong>${v.toLocaleString()}</strong>`;
  if (v === null || v === undefined) return '<span style="color:var(--text-muted)">\u2014</span>';
  return String(v);
}

// ── Helpers ───────────────────────────────────────────────────────

function metricCard(label, value, color) {
  return `
    <div class="rpt-metric">
      <div class="rpt-metric-label">${label}</div>
      <div class="rpt-metric-value" ${color ? `style="color:${color}"` : ''}>${value}</div>
    </div>
  `;
}

function renderCollapsibleJSON(data) {
  return `
    <details class="rpt-raw-json">
      <summary>View Raw JSON Data</summary>
      <div class="json-viewer">${JSON.stringify(data, null, 2)}</div>
    </details>
  `;
}

function renderRawJSONOnly(data) {
  return `<div class="json-viewer">${JSON.stringify(data, null, 2)}</div>`;
}

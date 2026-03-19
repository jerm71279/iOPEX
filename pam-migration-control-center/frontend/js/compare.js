/**
 * Option Comparison page renderer.
 */

async function renderComparison() {
  const data = await API.get('/deliverables/compare/options');
  const rows = data.rows || [];
  const permMap = data.permission_mapping || {};
  const platMap = data.platform_template_map || [];

  let html = `
    <div class="panel">
      <div class="panel-header">
        <div class="panel-title">Side-by-Side Comparison — CyberArk → Target Options</div>
        <span class="badge badge-muted">CLIENT: CISCO</span>
      </div>
      <div style="overflow-x:auto">
        <table class="compare-table">
          <thead>
            <tr>
              <th style="width:160px">Category</th>
              <th style="color:var(--blue)">&#x25A3; Devolutions (Option A)</th>
              <th style="color:var(--cyan)">&#x25C8; Keeper (Option B)</th>
              <th style="color:var(--purple)">&#x2B21; MiniOrange (Option C)</th>
            </tr>
          </thead>
          <tbody>
            ${rows.map(r => `
            <tr>
              <td style="font-weight:600;color:var(--text-bright)">${r.category}</td>
              <td class="risk-${r.a.risk}">${r.a.value}</td>
              <td class="risk-${r.b ? r.b.risk : 'low'}">${r.b ? r.b.value : '—'}</td>
              <td class="risk-${r.c ? r.c.risk : 'medium'}">${r.c ? r.c.value : '—'}</td>
            </tr>`).join('')}
          </tbody>
        </table>
      </div>
    </div>

    <div class="panel" style="margin-top:20px">
      <div class="panel-header">
        <div class="panel-title">Permission Model Deep Dive</div>
      </div>
      <div class="panel-body">
        <div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:16px">
          <div>
            <div class="section-label" style="color:var(--blue)">Devolutions: ${permMap.option_a?.description || ''}</div>
            ${(permMap.option_a?.roles || []).map(r => `
              <div style="background:var(--bg-surface);border:1px solid var(--border);border-radius:var(--radius);padding:10px;margin-bottom:8px">
                <div style="font-weight:600;color:var(--blue);font-size:0.82rem">${r.role}</div>
                <div style="font-size:0.68rem;color:var(--text-muted);margin-top:2px">${r.requires}</div>
                <div style="font-size:0.62rem;color:var(--text-muted);margin-top:4px;font-family:var(--font-mono)">${r.cyberark_perms.join(', ')}</div>
              </div>
            `).join('')}
            <div class="callout red" style="margin-top:10px">
              <div class="callout-title" style="color:var(--red)">9 Permissions Lost</div>
              <p style="font-family:var(--font-mono);font-size:0.62rem">${(permMap.option_a?.lost_permissions || []).join(', ')}</p>
            </div>
          </div>
          <div>
            <div class="section-label" style="color:var(--cyan)">Keeper: ${permMap.option_b?.description || ''}</div>
            ${(permMap.option_b?.roles || []).map(r => `
              <div style="background:var(--bg-surface);border:1px solid var(--border);border-radius:var(--radius);padding:10px;margin-bottom:8px">
                <div style="font-weight:600;color:var(--cyan);font-size:0.82rem">${r.role}</div>
                <div style="font-size:0.68rem;color:var(--text-muted);margin-top:2px">${r.requires}</div>
                <div style="font-size:0.62rem;color:var(--text-muted);margin-top:4px;font-family:var(--font-mono)">${r.cyberark_perms.join(', ')}</div>
              </div>
            `).join('')}
            <div class="callout red" style="margin-top:10px">
              <div class="callout-title" style="color:var(--red)">${(permMap.option_b?.lost_permissions || []).length} Permissions Lost</div>
              <p style="font-family:var(--font-mono);font-size:0.62rem">${(permMap.option_b?.lost_permissions || []).join(', ')}</p>
            </div>
            <div class="callout teal" style="margin-top:8px">
              <div class="callout-title" style="color:var(--cyan)">Keeper Advantage</div>
              <p style="font-size:0.68rem">Zero-knowledge AES-256-GCM. FedRAMP High (March 2026). KSM replaces CCP/AAM with 40+ native integrations.</p>
            </div>
          </div>
          <div>
            <div class="section-label" style="color:var(--purple)">MiniOrange: ${permMap.option_c?.description || ''}</div>
            ${(permMap.option_c?.roles || []).map(r => `
              <div style="background:var(--bg-surface);border:1px solid var(--border);border-radius:var(--radius);padding:10px;margin-bottom:8px">
                <div style="font-weight:600;color:var(--purple);font-size:0.82rem">${r.role}</div>
                <div style="font-size:0.68rem;color:var(--text-muted);margin-top:2px">${r.requires}</div>
                <div style="font-size:0.62rem;color:var(--text-muted);margin-top:4px;font-family:var(--font-mono)">${r.cyberark_perms.join(', ')}</div>
              </div>
            `).join('')}
            <div class="callout red" style="margin-top:10px">
              <div class="callout-title" style="color:var(--red)">${(permMap.option_c?.lost_permissions || []).length} Permissions Lost</div>
              <p style="font-family:var(--font-mono);font-size:0.62rem">${(permMap.option_c?.lost_permissions || []).join(', ')}</p>
            </div>
          </div>
        </div>
      </div>
    </div>

    <div class="panel" style="margin-top:20px">
      <div class="panel-header">
        <div class="panel-title">Platform Mapping — CyberArk → Target</div>
        <span class="badge badge-muted">CISCO: IOS/NX-OS/ASA INCLUDED</span>
      </div>
      <div style="overflow-x:auto">
        <table class="compare-table">
          <thead>
            <tr>
              <th>CyberArk Platform</th>
              <th style="color:var(--blue)">Devolutions (A)</th>
              <th style="color:var(--cyan)">Keeper (B)</th>
              <th style="color:var(--purple)">MiniOrange (C)</th>
            </tr>
          </thead>
          <tbody>
            ${platMap.map(p => `
            <tr>
              <td style="font-family:var(--font-mono);font-size:0.72rem">${p.cyberark}</td>
              <td class="risk-${p.risk_a}">${p.option_a}</td>
              <td class="risk-${p.risk_b}">${p.option_b}</td>
              <td class="risk-${p.risk_c || 'medium'}">${p.option_c || '—'}</td>
            </tr>`).join('')}
          </tbody>
        </table>
      </div>
    </div>
  `;

  document.getElementById('comparisonContent').innerHTML = html;
}

function renderDisclaimer() {
  document.getElementById('disclaimerContent').innerHTML = `
    <div class="callout amber">
      <div class="callout-title" style="color:var(--amber)">Interactive Demo — Not Connected to Live PAM</div>
      <p>This control center uses <strong>mock data</strong> to demonstrate the migration journey. It is not connected to any live CyberArk, Devolutions, Keeper, or MiniOrange instance.</p>
    </div>

    <div class="panel" style="margin-top:16px">
      <div class="panel-header"><div class="panel-title">What's Built</div></div>
      <div class="panel-body">
        <div class="health-grid" style="padding:0">
          ${[
            'FastAPI backend with 15+ REST endpoints',
            'Mock data matching real agent output formats',
            'Data import capability (POST /api/import/{type})',
            '7-page interactive frontend with drill-down',
            'Option A/B/C toggle — Devolutions / Keeper / MiniOrange',
            'ETL pipeline simulation with animation',
            'Gate approval simulation',
            'Agent output viewer (JSON drill-down)',
            'Full Java/Spring Boot Portal Builder scaffold (separate)',
            'PamVendorAdapter interface + 3 adapter stubs',
          ].map(item => `
            <div class="health-item">
              <div class="health-dot dot-green"></div>
              <div class="health-name" style="font-size:0.72rem">${item}</div>
            </div>
          `).join('')}
        </div>
      </div>
    </div>

    <div class="panel" style="margin-top:16px">
      <div class="panel-header"><div class="panel-title">What's Needed for Production</div></div>
      <div class="panel-body">
        <div class="health-grid" style="padding:0">
          ${[
            'Wire API stubs to real coordinator.py agent calls',
            'CyberArk PVWA REST API integration (Agent 11, 01, 04)',
            'Devolutions Server REST API integration (Agent 04, 05, 10)',
            'Keeper Gateway integration (rotation, heartbeat, KSM)',
            'OAuth2/OIDC provider integration (enterprise IdP)',
            'Database persistence (PostgreSQL for state)',
            'WebSocket support for real-time agent status',
            'Production TLS / certificate management',
            'CI/CD pipeline (GitHub Actions or Jenkins)',
            'Load testing with 20K+ accounts',
            'Security audit and penetration testing',
            'Dual-backend parallel mode (P6 traffic shifting)',
          ].map(item => `
            <div class="health-item">
              <div class="health-dot dot-amber"></div>
              <div class="health-name" style="font-size:0.72rem">${item}</div>
            </div>
          `).join('')}
        </div>
      </div>
    </div>

    <div class="panel" style="margin-top:16px">
      <div class="panel-header"><div class="panel-title">Importing Your Own Test Data</div></div>
      <div class="panel-body">
        <p style="font-size:0.78rem;margin-bottom:10px">Upload JSON files to override mock data with your own test data:</p>
        <div class="json-viewer" style="color:var(--cyan)">
# Import discovery manifest
curl -X POST http://localhost:8080/api/import/discovery \\
  -F "file=@my_discovery.json"

# Import custom agent data
curl -X POST http://localhost:8080/api/import/agents \\
  -F "file=@my_agents.json"

# Check what's imported
curl http://localhost:8080/api/import/status

# Clear imported data (revert to mock)
curl -X DELETE http://localhost:8080/api/import/discovery
        </div>
      </div>
    </div>

    <div class="panel" style="margin-top:16px">
      <div class="panel-header"><div class="panel-title">Production Milestone Timeline</div></div>
      <div class="panel-body">
        ${[
          { weeks: 'W10-20', label: 'Scaffold & adapter stubs', status: 'done' },
          { weeks: 'W20-34', label: 'First vendor adapter live — read-only listing', status: 'todo' },
          { weeks: 'W34-58', label: 'Full CRUD, session proxy, audit forwarding', status: 'todo' },
          { weeks: 'W58-74', label: 'Dual-backend parallel, pen testing', status: 'todo' },
          { weeks: 'W74-76', label: 'Production cutover with rollback plan', status: 'todo' },
        ].map(m => `
          <div style="display:flex;align-items:center;gap:10px;margin-bottom:6px">
            <span class="badge ${m.status === 'done' ? 'badge-green' : 'badge-amber'}" style="min-width:60px;text-align:center">${m.weeks}</span>
            <span style="font-size:0.78rem">${m.label}</span>
          </div>
        `).join('')}
      </div>
    </div>
  `;
}

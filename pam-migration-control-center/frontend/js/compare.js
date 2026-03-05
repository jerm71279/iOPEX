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
        <div class="panel-title">Side-by-Side Comparison</div>
      </div>
      <div style="overflow-x:auto">
        <table class="compare-table">
          <thead>
            <tr>
              <th style="width:160px">Category</th>
              <th>Option A — Secret Server + StrongDM</th>
              <th>Option B — Privilege Cloud</th>
            </tr>
          </thead>
          <tbody>
            ${rows.map(r => `
            <tr>
              <td style="font-weight:600;color:var(--text-bright)">${r.category}</td>
              <td class="risk-${r.a.risk}">${r.a.value}</td>
              <td class="risk-${r.b.risk}">${r.b.value}</td>
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
        <div style="display:grid;grid-template-columns:1fr 1fr;gap:20px">
          <div>
            <div class="section-label" style="color:var(--blue)">Option A: ${permMap.option_a?.description || ''}</div>
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
            <div class="section-label" style="color:var(--green)">Option B: ${permMap.option_b?.description || ''}</div>
            <div class="callout teal">
              <div class="callout-title" style="color:var(--green)">1:1 Parity</div>
              <p>${permMap.option_b?.note || 'All 22 permissions map directly.'}</p>
            </div>
          </div>
        </div>
      </div>
    </div>

    <div class="panel" style="margin-top:20px">
      <div class="panel-header">
        <div class="panel-title">Platform / Template Mapping</div>
      </div>
      <div style="overflow-x:auto">
        <table class="compare-table">
          <thead>
            <tr>
              <th>CyberArk Platform</th>
              <th>Option A (SS Template)</th>
              <th>Option B (PC Platform)</th>
            </tr>
          </thead>
          <tbody>
            ${platMap.map(p => `
            <tr>
              <td style="font-family:var(--font-mono);font-size:0.72rem">${p.cyberark}</td>
              <td class="risk-${p.risk_a}">${p.option_a}</td>
              <td class="risk-${p.risk_b}">${p.option_b}</td>
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
      <p>This control center uses <strong>mock data</strong> to demonstrate the migration journey. It is not connected to any live CyberArk, Secret Server, or StrongDM instance.</p>
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
            'Option A/B toggle affecting all pages',
            'ETL pipeline simulation with animation',
            'Gate approval simulation',
            'Agent output viewer (JSON drill-down)',
            'Full Java/Spring Boot DX Portal scaffold (separate)',
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
            'Secret Server REST API integration (Agent 04, 05, 10)',
            'StrongDM SDK integration (session proxy, Cedar policies)',
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

/**
 * HELIX — Architecture page
 */

function renderArchitecture() {
  const el = document.getElementById('architectureContent');
  if (!el) return;

  el.innerHTML = `
    <div class="callout bt" style="margin-bottom:20px;">
      <div class="callout-title">Design Principle</div>
      <p>No changes are made to any existing BT component. The AI intelligence layer operates entirely on top of the current architecture — intercepting, observing, and healing without modifying source systems.</p>
    </div>

    <!-- AI Intelligence Layer -->
    <div class="arch-layer">
      <div class="arch-layer-header arch-layer-ai">&#x2B21; AI INTELLIGENCE LAYER — iOPEX (NEW)</div>
      <div class="arch-nodes">
        <div class="arch-node ai-agent" onclick="showPage('agents',document.querySelectorAll('.nav-link')[2])">
          <div class="arch-node-label">Agent 1</div>
          <div class="arch-node-name">Observability</div>
          <div class="arch-node-desc">Monitors cascade events, intercepts stall after partial success, captures data delta</div>
        </div>
        <div class="arch-node ai-agent" onclick="showPage('agents',document.querySelectorAll('.nav-link')[2])">
          <div class="arch-node-label">Agent 2</div>
          <div class="arch-node-name">Resolution</div>
          <div class="arch-node-desc">Executes targeted fixes for specific field mismatches across distributed stores</div>
        </div>
        <div class="arch-node ai-agent" onclick="showPage('agents',document.querySelectorAll('.nav-link')[2])">
          <div class="arch-node-label">Agent 3</div>
          <div class="arch-node-name">Healing</div>
          <div class="arch-node-desc">Orchestrates full multi-database restoration to a verified consistent state</div>
        </div>
        <div class="arch-node ai-agent" onclick="showPage('agents',document.querySelectorAll('.nav-link')[2])">
          <div class="arch-node-label">Agent 4</div>
          <div class="arch-node-name">RPA Automation</div>
          <div class="arch-node-desc">Application-layer recovery — restores user login access after backend fix completes</div>
        </div>
      </div>
    </div>

    <div class="arch-flow-arrow">&#x2193; intercepts &amp; heals without modifying</div>

    <!-- Existing BT Architecture -->
    <div class="arch-layer">
      <div class="arch-layer-header arch-layer-existing">&#x25A3; EXISTING BT COMPONENTS — UNCHANGED</div>
      <div class="arch-nodes">
        <div class="arch-node">
          <div class="arch-node-label">Source</div>
          <div class="arch-node-name">DnP SQL</div>
          <div class="arch-node-desc">Identity source of truth. Triggers cascade on updates (DoB, name, address)</div>
        </div>
        <div class="arch-node">
          <div class="arch-node-label">Broadband</div>
          <div class="arch-node-name">One View</div>
          <div class="arch-node-desc">First downstream target in cascade. Usually updates successfully</div>
        </div>
        <div class="arch-node">
          <div class="arch-node-label">Digital Identity</div>
          <div class="arch-node-name">SAF</div>
          <div class="arch-node-desc">Second downstream target. Stalls at this point in the Partial Success Trap</div>
        </div>
        <div class="arch-node">
          <div class="arch-node-label">Profile Store</div>
          <div class="arch-node-name">Customer Hub</div>
          <div class="arch-node-desc">MongoDB profile store. Third downstream target — also stale during cascade failure</div>
        </div>
        <div class="arch-node">
          <div class="arch-node-label">Mobile / BACS</div>
          <div class="arch-node-name">Excalibur</div>
          <div class="arch-node-desc">Delinquent account management &amp; debt collection. Separate sync pathway via BACS</div>
        </div>
      </div>
    </div>

    <div style="margin-top:24px;">
      <div class="section-label">Cascade Flow — Trigger to Distributed Update</div>
      <div class="panel" style="overflow:visible;">
        <div class="panel-body">
          <div style="display:flex;align-items:center;gap:0;flex-wrap:wrap;padding:4px 0;">
            ${[
              { name: 'DnP SQL', label: 'Trigger', color: 'var(--blue)' },
              { name: 'One View', label: 'Step 1', color: 'var(--green)' },
              { name: 'SAF', label: 'Step 2', color: 'var(--amber)' },
              { name: 'Customer Hub', label: 'Step 3', color: 'var(--amber)' },
              { name: 'Excalibur', label: 'Step 4', color: 'var(--teal)' },
            ].map((s, i, arr) => `
              <div style="padding:10px 14px;border:2px solid ${s.color};border-radius:var(--radius);background:${s.color}22;text-align:center;min-width:100px;">
                <div style="font-family:var(--font-mono);font-size:0.5rem;color:var(--text-muted);text-transform:uppercase;letter-spacing:1px;">${s.label}</div>
                <div style="font-weight:700;font-size:0.78rem;color:${s.color};">${s.name}</div>
              </div>
              ${i < arr.length - 1 ? '<div style="color:var(--text-muted);font-size:1.1rem;padding:0 8px;">&rarr;</div>' : ''}`
            ).join('')}
          </div>
          <div style="margin-top:12px;font-size:0.72rem;color:var(--text-muted);line-height:1.6;">
            <span style="color:var(--amber);">&#x26A0;</span>&nbsp;
            <strong style="color:var(--amber);">Partial Success Trap:</strong>
            One View typically updates, but SAF and Customer Hub frequently stall — leaving the identity in an inconsistent state across systems.
          </div>
        </div>
      </div>
    </div>

    <div style="margin-top:8px;">
      <div class="section-label">Team Ownership</div>
      <div class="stats-grid" style="margin-top:8px;">
        ${[
          { name: 'Neil', role: 'Solution Architect', color: 'var(--bt)' },
          { name: 'Manoj', role: 'QA Manager', color: 'var(--cyan)' },
          { name: 'Jiayi Zhang', role: 'Dev Manager', color: 'var(--teal)' },
          { name: 'Product Owners', role: 'Operational Governance', color: 'var(--text-muted)' },
          { name: 'Data Agents', role: 'Data Landscape', color: 'var(--text-muted)' },
          { name: 'Healer/Observer', role: 'Autonomous Logic Evolution', color: 'var(--bt)' },
        ].map(p => `
          <div class="stat-card">
            <div class="stat-label">${p.role}</div>
            <div style="font-size:0.95rem;font-weight:700;color:${p.color};margin-top:4px;">${p.name}</div>
          </div>`).join('')}
      </div>
    </div>
  `;
}

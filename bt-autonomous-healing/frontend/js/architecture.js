/**
 * HELIX — Architecture page (CIA-25802 + CIA-48107 accurate flows)
 */

function renderArchitecture() {
  const el = document.getElementById('architectureContent');
  if (!el) return;

  el.innerHTML = `
    <div class="callout bt" style="margin-bottom:20px;">
      <div class="callout-title">Design Principle</div>
      <p>No changes are made to any existing BT component. The AI intelligence layer operates on top of the current architecture — intercepting, observing, and healing without modifying source systems.</p>
    </div>

    <!-- AI Intelligence Layer -->
    <div class="arch-layer" style="margin-bottom:8px;">
      <div class="arch-layer-header arch-layer-ai">&#x2B21; AI INTELLIGENCE LAYER — iOPEX (NEW)</div>
      <div class="arch-nodes">
        ${[
          { num:'01', name:'Observability Agent', alias:'The Interceptor', desc:'Monitors EEDSP event bus + TMF API responses. Intercepts stalls in PartyManagement or UserRolesAndPermissions sync within 30s threshold.' },
          { num:'02', name:'Resolution Agent',    alias:'The Precision Fixer', desc:'Executes targeted re-push of data delta via TMF PATCH endpoints to SAF and Customer Hub. Field-level precision — no full resync.' },
          { num:'03', name:'Healing Agent',        alias:'The System Restorer', desc:'Full consistency scan across all 5 domains + EEDSP layer. Coordinates restoration sequence via On Prem API Gateway.' },
          { num:'04', name:'RPA Automation',       alias:'The User Advocate', desc:'Application-layer recovery via POST /v3/digital-identity/Assisted — restores SAF username and clears stale auth state after backend fix.' },
        ].map(a => `
          <div class="arch-node ai-agent" onclick="showPage('agents',document.querySelectorAll('.nav-link')[2])">
            <div class="arch-node-label">AGENT ${a.num}</div>
            <div class="arch-node-name">${a.name}</div>
            <div class="arch-node-desc" style="font-size:0.6rem;margin-top:4px;">${a.alias}</div>
            <div class="arch-node-desc">${a.desc}</div>
          </div>`).join('')}
      </div>
    </div>

    <div class="arch-flow-arrow">&#x2193; observes &amp; heals — no changes to existing components</div>

    <!-- Middleware Layer -->
    <div class="arch-layer" style="margin-bottom:8px;">
      <div class="arch-layer-header arch-layer-existing" style="color:var(--cyan);">&#x25C8; MIDDLEWARE LAYER — EEDSP + TMF APIS (EXISTING, UNCHANGED)</div>
      <div class="arch-nodes">
        <div class="arch-node" style="border-color:var(--cyan);min-width:180px;">
          <div class="arch-node-label">APP20717</div>
          <div class="arch-node-name" style="color:var(--cyan);">EEDSP Platform</div>
          <div class="arch-node-desc">EE Digital Service Platform<br>Common Microservice + Customer Auth &amp; Filtering MS</div>
        </div>
        <div class="arch-node">
          <div class="arch-node-label">APP13680</div>
          <div class="arch-node-name">API Gateway (EE)</div>
          <div class="arch-node-desc">EE-facing API gateway — routes Excalibur profile management requests</div>
        </div>
        <div class="arch-node">
          <div class="arch-node-label">APP13590</div>
          <div class="arch-node-name">On Prem API Gateway</div>
          <div class="arch-node-desc">On-premise gateway → Microservices Layer (APP15042) → Directory &amp; Profile (APP04910)</div>
        </div>
        <div class="arch-node" style="border-color:var(--purple);">
          <div class="arch-node-label">TMF APIS</div>
          <div class="arch-node-name" style="color:var(--purple);">SVC14123 / 14352 / 14353</div>
          <div class="arch-node-desc">
            TMF632 PartyManagement<br>
            TMF669 PartyRoleManagement<br>
            TMF672 UserRolesAndPermissions
          </div>
        </div>
        <div class="arch-node">
          <div class="arch-node-label">APIFN-DNP-LINK</div>
          <div class="arch-node-name">DNP-Link</div>
          <div class="arch-node-desc">Routes DnP permission changes → SAF (QuickSearchPermissions) → Customer Hub via PATCH /tmf/digitalIdentity/digital-permissions</div>
        </div>
      </div>
    </div>

    <div class="arch-flow-arrow">&#x2193;</div>

    <!-- Existing BT Systems -->
    <div class="arch-layer">
      <div class="arch-layer-header arch-layer-existing">&#x25A3; EXISTING BT COMPONENTS — UNCHANGED</div>
      <div class="arch-nodes">
        ${[
          { label:'SOURCE', id:'DnP SQL', desc:'Identity source of truth. Triggers cascade on updates (DoB, name, address). Permissions route via APIFN-DNP-LINK.' },
          { label:'BROADBAND', id:'One View', desc:'First downstream target in the standard cascade. Typically updates successfully via direct sync.' },
          { label:'DIGITAL ID', id:'SAF', desc:'Single Authentication Framework (CIAM:APP20586). Receives identity via EEDSP. Username creation via POST /v3/digital-identity/Assisted [Autoprovision].' },
          { label:'PROFILE (MONGODB)', id:'Customer Hub', desc:'Document store. Polls events via Amazon SQS/SNS: IndividualCreateEvent, PermissionCreateEvent, IndividualAttributeValueChangeEvent.' },
          { label:'MOBILE / BACS', id:'Excalibur', desc:'Calls POST /bt-consumer/v1/excalibur-profile-management → EEDSP. Match logic: primary email = SAF username AND first name + last name + DoB.' },
        ].map(s => `
          <div class="arch-node">
            <div class="arch-node-label">${s.label}</div>
            <div class="arch-node-name">${s.id}</div>
            <div class="arch-node-desc">${s.desc}</div>
          </div>`).join('')}
      </div>
    </div>

    <!-- CIA-48107 Flow -->
    <div style="margin-top:24px;">
      <div class="section-label">CIA-48107 — Excalibur → Customer Hub Sync (Customer Hub First)</div>
      <div class="panel">
        <div class="panel-body" style="padding:16px;">
          <div style="font-size:0.72rem;color:var(--text-muted);margin-bottom:14px;line-height:1.6;">
            Excalibur initiates profile sync via <code style="background:var(--bg-surface);padding:2px 6px;border-radius:4px;font-family:var(--font-mono);font-size:0.65rem;">POST /bt-consumer/v1/excalibur-profile-management</code>.
            Match logic: link to existing Customer Hub profile when <strong style="color:var(--text-bright);">primary email = SAF username</strong> AND <strong style="color:var(--text-bright);">first name + last name + DoB match</strong>. Create new profile if no match.
          </div>
          <div style="display:flex;align-items:center;gap:0;flex-wrap:wrap;">
            ${[
              { name:'Excalibur', label:'TRIGGER', color:'var(--teal)' },
              { arrow:'→' },
              { name:'API Gateway (EE)\nAPP13680', label:'GATEWAY', color:'var(--blue)' },
              { arrow:'→' },
              { name:'EEDSP\nAPP20717', label:'PLATFORM', color:'var(--cyan)' },
              { arrow:'→' },
              { name:'TMF APIs\nSVC14123/14352/14353', label:'SERVICES', color:'var(--purple)' },
              { arrow:'→' },
              { name:'Customer Hub\n(MongoDB)', label:'TARGET', color:'var(--amber)' },
              { arrow:'→' },
              { name:'SAF\nUsername Creation', label:'IDENTITY', color:'var(--green)' },
            ].map(s => s.arrow
              ? `<div style="color:var(--text-muted);font-size:1.1rem;padding:0 6px;">${s.arrow}</div>`
              : `<div style="padding:10px 12px;border:2px solid ${s.color};border-radius:var(--radius);background:${s.color}22;text-align:center;min-width:90px;">
                   <div style="font-family:var(--font-mono);font-size:0.48rem;color:var(--text-muted);text-transform:uppercase;letter-spacing:1px;margin-bottom:4px;">${s.label}</div>
                   <div style="font-weight:700;font-size:0.68rem;color:${s.color};white-space:pre-line;">${s.name}</div>
                 </div>`
            ).join('')}
          </div>
          <div style="margin-top:12px;">
            <div class="section-label" style="margin-top:12px;">Customer Hub Polling Events (Amazon SQS/SNS)</div>
            <div style="display:flex;gap:8px;flex-wrap:wrap;margin-top:6px;">
              ${['IndividualCreateEvent','PermissionCreateEvent','IndividualAttributeValueChangeEvent','PermissionAttributeValueChangeEvent'].map(e =>
                `<span class="badge badge-bt" style="font-size:0.6rem;">${e}</span>`
              ).join('')}
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- CIA-25802 Flow -->
    <div style="margin-top:8px;">
      <div class="section-label">CIA-25802 — DnP → Customer Hub Permissions Re-Sync</div>
      <div class="panel">
        <div class="panel-body" style="padding:16px;">
          <div style="font-size:0.72rem;color:var(--text-muted);margin-bottom:14px;line-height:1.6;">
            Permission changes in DnP route through <strong style="color:var(--text-bright);">APIFN-DNP-LINK</strong> → SAF (QuickSearchPermissions) → Customer Hub via
            <code style="background:var(--bg-surface);padding:2px 6px;border-radius:4px;font-family:var(--font-mono);font-size:0.65rem;">PATCH /tmf/digitalIdentity/digital-permissions</code>.
          </div>
          <div style="display:flex;align-items:center;gap:0;flex-wrap:wrap;">
            ${[
              { name:'DnP SQL', label:'PERMISSIONS SOURCE', color:'var(--blue)' },
              { arrow:'→' },
              { name:'APIFN-DNP-LINK', label:'ROUTER', color:'var(--bt)' },
              { arrow:'→' },
              { name:'SAF\nQuickSearchPermissions', label:'DIGITAL ID', color:'var(--amber)' },
              { arrow:'→' },
              { name:'Customer Hub\nPATCH permissions', label:'TARGET', color:'var(--green)' },
            ].map(s => s.arrow
              ? `<div style="color:var(--text-muted);font-size:1.1rem;padding:0 6px;">${s.arrow}</div>`
              : `<div style="padding:10px 12px;border:2px solid ${s.color};border-radius:var(--radius);background:${s.color}22;text-align:center;min-width:100px;">
                   <div style="font-family:var(--font-mono);font-size:0.48rem;color:var(--text-muted);text-transform:uppercase;letter-spacing:1px;margin-bottom:4px;">${s.label}</div>
                   <div style="font-weight:700;font-size:0.68rem;color:${s.color};white-space:pre-line;">${s.name}</div>
                 </div>`
            ).join('')}
          </div>
        </div>
      </div>
    </div>

    <!-- Team Ownership -->
    <div style="margin-top:8px;">
      <div class="section-label">Team Ownership</div>
      <div class="stats-grid" style="margin-top:8px;">
        ${[
          { name:'Neil', role:'Solution Architect', color:'var(--bt)' },
          { name:'Manoj', role:'QA Manager', color:'var(--cyan)' },
          { name:'Jiayi Zhang', role:'Dev Manager', color:'var(--teal)' },
          { name:'Product Owners', role:'Operational Governance', color:'var(--text-muted)' },
          { name:'Data Agents', role:'Data Landscape', color:'var(--text-muted)' },
          { name:'Healer/Observer', role:'Autonomous Logic Evolution', color:'var(--bt)' },
        ].map(p => `
          <div class="stat-card">
            <div class="stat-label">${p.role}</div>
            <div style="font-size:0.95rem;font-weight:700;color:${p.color};margin-top:4px;">${p.name}</div>
          </div>`).join('')}
      </div>
    </div>
  `;
}

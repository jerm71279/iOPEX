/**
 * Guide & FAQ page — comprehensive reference for the SHIFT Migration Control Center.
 */

function renderGuide() {
  const el = document.getElementById('guideContent');
  if (!el) return;

  el.innerHTML = _guideSection('&#x1F3D7; Customer Current Architecture — CyberArk PAS + Conjur', `

    <p style="margin-bottom:18px;font-size:0.72rem;color:var(--text-standard);line-height:1.7;">
      The customer's existing environment is a full CyberArk deployment split into two pillars:
      <strong>Core PAS</strong> (vaults, password rotation, session management for human admins)
      and <strong>Conjur</strong> (machine identity — secrets for Kubernetes, CI/CD pipelines, and app workloads).
      This is the <em>current state</em> that SHIFT migrates from.
    </p>

    <!-- Architecture diagram -->
    <div style="background:var(--bg-surface);border:1px solid var(--border);border-radius:8px;padding:24px;overflow-x:auto;">

      <!-- Top row: Cyber Admins -->
      <div style="text-align:center;margin-bottom:16px;">
        <div style="font-size:0.58rem;font-family:var(--font-mono);color:var(--text-muted);letter-spacing:2px;margin-bottom:8px;">CYBER ADMINS</div>
        <div style="display:inline-flex;gap:12px;justify-content:center;">
          <div style="background:var(--bg-card);border:1px solid var(--border);border-radius:6px;padding:8px 14px;text-align:center;">
            <div style="font-size:1rem;">&#x1F464;</div>
            <div style="font-size:0.62rem;color:var(--text-standard);margin-top:3px;">Ops</div>
          </div>
          <div style="background:var(--bg-card);border:1px solid var(--border);border-radius:6px;padding:8px 14px;text-align:center;">
            <div style="font-size:1rem;">&#x1F465;</div>
            <div style="font-size:0.62rem;color:var(--text-standard);margin-top:3px;">Engineering</div>
          </div>
          <div style="background:var(--bg-card);border:1px solid var(--border);border-radius:6px;padding:8px 14px;text-align:center;">
            <div style="font-size:1rem;">&#x1F465;</div>
            <div style="font-size:0.62rem;color:var(--text-standard);margin-top:3px;">Platform</div>
          </div>
        </div>
        <div style="text-align:center;color:var(--border);margin:8px 0;font-size:0.9rem;">&#x25BC;</div>
      </div>

      <!-- Middle row: User | CyberArk Platform | Targets -->
      <div style="display:grid;grid-template-columns:80px 1fr 200px;gap:20px;align-items:start;">

        <!-- User -->
        <div style="text-align:center;padding-top:40px;">
          <div style="font-size:1.6rem;">&#x1F464;</div>
          <div style="font-size:0.62rem;color:var(--text-muted);margin-top:4px;font-family:var(--font-mono);">USER</div>
          <div style="margin-top:8px;color:var(--border);font-size:0.9rem;">&rarr;</div>
        </div>

        <!-- CyberArk Platform (Core PAS + Conjur) -->
        <div style="border:2px solid var(--blue);border-radius:8px;padding:14px;">
          <div style="font-size:0.6rem;font-family:var(--font-mono);color:var(--blue);letter-spacing:2px;margin-bottom:12px;text-align:center;">CYBERARK</div>

          <div style="display:grid;grid-template-columns:1fr 1fr;gap:12px;">

            <!-- Core PAS -->
            <div style="background:var(--bg-card);border:1px solid var(--cyan);border-radius:6px;padding:12px;">
              <div style="font-size:0.6rem;font-family:var(--font-mono);color:var(--cyan);letter-spacing:1.5px;margin-bottom:8px;text-align:center;">CORE PAS</div>
              <div style="display:flex;flex-direction:column;gap:5px;">
                <div class="badge badge-cyan" style="text-align:center;font-size:0.62rem;">&#x1F3DB; Vaults</div>
                <div class="badge badge-cyan" style="text-align:center;font-size:0.62rem;">&#x1F504; Password Rotation</div>
                <div class="badge badge-cyan" style="text-align:center;font-size:0.62rem;">&#x25B6; Session Management</div>
                <div class="badge badge-cyan" style="text-align:center;font-size:0.62rem;">&#x2630; Others</div>
              </div>
            </div>

            <!-- Conjur -->
            <div style="background:var(--bg-card);border:1px solid var(--purple);border-radius:6px;padding:12px;">
              <div style="font-size:0.6rem;font-family:var(--font-mono);color:var(--purple);letter-spacing:1.5px;margin-bottom:8px;text-align:center;">CONJUR</div>
              <div style="font-size:0.62rem;color:var(--text-standard);text-align:center;line-height:1.6;margin-bottom:8px;">Stores &amp; retrieves<br>Credentials</div>
              <div style="font-size:0.58rem;font-family:var(--font-mono);color:var(--purple);text-align:center;letter-spacing:1px;">FOR PLATFORM<br>PROVISIONS</div>
            </div>

          </div>

          <!-- Bottom accounts row -->
          <div style="display:grid;grid-template-columns:1fr 1fr;gap:12px;margin-top:12px;">
            <div style="text-align:center;">
              <div style="font-size:0.9rem;margin-bottom:4px;">&#x1F465;</div>
              <div style="font-size:0.6rem;font-family:var(--font-mono);color:var(--text-muted);">ADMINS</div>
              <div style="font-size:0.58rem;color:var(--text-muted);margin-top:2px;">Privileged Accounts</div>
            </div>
            <div style="text-align:center;">
              <div style="font-size:0.9rem;margin-bottom:4px;">&#x1F9D1;&#x200D;&#x1F4BB;</div>
              <div style="font-size:0.6rem;font-family:var(--font-mono);color:var(--text-muted);">DEVELOPERS</div>
              <div style="font-size:0.58rem;color:var(--text-muted);margin-top:2px;">Cluster / Service · App Accounts</div>
            </div>
          </div>
        </div>

        <!-- Target examples -->
        <div>
          <div style="font-size:0.58rem;font-family:var(--font-mono);color:var(--text-muted);letter-spacing:2px;margin-bottom:8px;text-align:center;">TARGET EXAMPLES</div>

          <!-- Core PAS targets -->
          <div style="background:var(--bg-card);border:1px solid var(--cyan);border-radius:6px;padding:10px;margin-bottom:8px;">
            <div style="font-size:0.58rem;font-family:var(--font-mono);color:var(--cyan);letter-spacing:1.5px;margin-bottom:6px;">CORE PAS</div>
            <div style="display:flex;flex-wrap:wrap;gap:4px;">
              <span class="badge badge-cyan" style="font-size:0.58rem;">Windows</span>
              <span class="badge badge-cyan" style="font-size:0.58rem;">UNIX</span>
              <span class="badge badge-cyan" style="font-size:0.58rem;">Database</span>
              <span class="badge badge-cyan" style="font-size:0.58rem;">Network</span>
              <span class="badge badge-cyan" style="font-size:0.58rem;">Web Apps</span>
            </div>
          </div>

          <!-- Conjur targets -->
          <div style="background:var(--bg-card);border:1px solid var(--purple);border-radius:6px;padding:10px;">
            <div style="font-size:0.58rem;font-family:var(--font-mono);color:var(--purple);letter-spacing:1.5px;margin-bottom:6px;">CONJUR</div>
            <div style="display:flex;flex-wrap:wrap;gap:4px;">
              <span class="badge badge-purple" style="font-size:0.58rem;">Kubernetes</span>
              <span class="badge badge-purple" style="font-size:0.58rem;">Database</span>
              <span class="badge badge-purple" style="font-size:0.58rem;">OpenShift</span>
              <span class="badge badge-purple" style="font-size:0.58rem;">CI/CD Pipeline</span>
            </div>
          </div>
        </div>

      </div><!-- /middle grid -->
    </div><!-- /diagram -->

    <div class="callout blue" style="margin-top:16px;font-size:0.68rem;line-height:1.6;">
      <div class="callout-title">Migration Scope</div>
      <p><strong>Core PAS</strong> accounts migrate via the 15-agent SHIFT orchestrator (Phases P1–P7).
      <strong>Conjur</strong> secrets require platform re-architecture — app teams update their SDK calls;
      the Conjur migrator handles policy translation. The SHIFT Agent 11 (Multi-Vendor Source Adapter)
      handles both pillars as separate source streams.</p>
    </div>

  `) +

  _guideSection('What Is This Control Center?', `
    <p><strong>Executive summary:</strong> The SHIFT Migration Control Center is a real-time operational dashboard for managing Cisco's large-scale CyberArk PAM migration. It provides visibility into every phase, agent, gate, and risk factor across three evaluated target platforms: <strong style="color:var(--blue)">Devolutions</strong> (44w), <strong style="color:var(--cyan)">Keeper Security</strong> (36w), and <strong style="color:var(--purple)">MiniOrange</strong> (32w). CyberArk is owned by a Cisco competitor — Cisco requires a clean, full migration off CyberArk to a vendor-neutral PAM platform.</p>
    <p><strong>Technical overview:</strong> The frontend is a single-page app (Vanilla JS, no frameworks) served by a FastAPI backend. All data flows through the 15-agent AI orchestrator. Each page visualizes a different slice of the orchestrator's output — from high-level phase timelines down to individual account-level ETL results. The two MCP servers (pam-migration-mcp and SHIFT Portal) provide Model Context Protocol integration for AI-assisted operations.</p>
    <p>This control center is a <strong>demonstration/proposal tool</strong> — it uses mock data to show how the migration would be managed. In production, the backend connects to live CyberArk PVWA and target platform APIs.</p>
  `) +

  _guideSection('SHIFT Architecture — Framework-Agnostic Design', `
    <p style="margin-bottom:14px;">SHIFT is a <strong>methodology, tooling, and agent design pattern</strong> — not an SDK. The underlying orchestration engine is swappable. This makes SHIFT portable and platform-independent.</p>

    <div style="margin-bottom:20px;">
      <div style="font-weight:700;color:var(--text-bright);margin-bottom:10px;font-size:0.72rem;letter-spacing:.05em;">THREE-LAYER COORDINATION MODEL</div>
      <div style="display:flex;flex-direction:column;gap:0;">
        <div class="shift-arch-layer" style="background:var(--amber-dim);border-color:var(--amber);">
          <div class="shift-arch-label" style="color:var(--amber);">LAYER 0 — PMO INTELLIGENCE</div>
          <div class="shift-arch-desc">
            <strong style="color:var(--amber)">iOPEX PMO Engine</strong> (PMO Brain) generates weekly PMO Directive JSON payloads — action items, gate readiness, blocked items, team accountability. RAG corpus ingests all project events (gates, checkpoints, directives, execution results) into ChromaDB + SQLite. BI Dashboard surfaces 6-panel management view.
          </div>
          <div style="font-size:0.52rem;color:var(--amber);margin-top:6px;font-family:var(--font-mono);letter-spacing:1px;">MANAGEMENT INTELLIGENCE — WHAT NEEDS TO HAPPEN &amp; WHY</div>
        </div>
        <div class="shift-arch-arrow">&#x25BC;</div>
        <div class="shift-arch-layer" style="background:var(--teal-dim);border-color:var(--teal);">
          <div class="shift-arch-label" style="color:var(--teal);">LAYER 1 — EXECUTION ENGINE</div>
          <div class="shift-arch-desc">
The <strong style="color:var(--teal)">Execution Engine</strong> receives PMO Directives, routes action items to the 15 SHIFT LangGraph agents, emits structured Execution Result payloads back to iOPEX PMO Engine. Each result is ingested into the RAG corpus, closing the weekly PMO cycle.
          </div>
          <div style="font-size:0.52rem;color:var(--teal);margin-top:6px;font-family:var(--font-mono);letter-spacing:1px;">EXECUTION ROUTING — 15 AGENTS · PHASE GATES · ETL PIPELINE</div>
        </div>
        <div class="shift-arch-arrow">&#x25BC;</div>
        <div class="shift-arch-layer" style="background:var(--cyan-dim);border-color:var(--cyan);">
          <div class="shift-arch-label" style="color:var(--cyan);">LAYER 2 — SHIFT CONTROL CENTER</div>
          <div class="shift-arch-desc">
            <strong style="color:var(--cyan)">This demo</strong> — real-time operational dashboard for gates, waves, checkpoints, agents, and migration phases. In production: backend connects to live CyberArk PVWA and target platform APIs (Devolutions / Keeper / MiniOrange).
          </div>
          <div style="font-size:0.52rem;color:var(--cyan);margin-top:6px;font-family:var(--font-mono);letter-spacing:1px;">VISIBILITY LAYER — GATES · WAVES · PHASES · ML · CHECKPOINTS</div>
        </div>
      </div>
      <div class="callout amber" style="margin-top:12px;font-size:0.67rem;line-height:1.6;">
        <div class="callout-title" style="color:var(--amber);font-size:0.7rem;">PMO Cycle (Weekly)</div>
        <p style="margin:0;">iOPEX PMO Engine synthesizes project state &rarr; emits PMO Directive &rarr; Execution Engine routes to agents &rarr; agents execute &rarr; Execution Results emitted &rarr; iOPEX PMO Engine ingests results &rarr; RAG corpus updated &rarr; Dashboard refreshes. Gate events and Yellow Checkpoints are ingested in real-time as they occur.</p>
      </div>
    </div>

    <div style="font-weight:700;color:var(--text-bright);margin-bottom:10px;font-size:0.72rem;letter-spacing:.05em;">FRAMEWORK-AGNOSTIC ORCHESTRATION</div>
    <div style="display:flex;flex-direction:column;gap:0;margin:14px 0;">
      <div class="shift-arch-layer" style="background:var(--teal-dim);border-color:var(--teal);">
        <div class="shift-arch-label" style="color:var(--teal);">SHIFT METHODOLOGY LAYER</div>
        <div class="shift-arch-desc">Agent patterns, phase gates, ETL pipeline design, NHI classification rules, ML feedback loops</div>
        <div style="font-size:0.52rem;color:var(--teal);margin-top:6px;font-family:var(--font-mono);letter-spacing:1px;">PORTABLE ACROSS ANY ORCHESTRATION ENGINE</div>
      </div>
      <div class="shift-arch-arrow">&#x25BC;</div>
      <div class="shift-arch-layer" style="background:var(--purple-dim);border-color:var(--purple);">
        <div class="shift-arch-label" style="color:var(--purple);">ORCHESTRATION ENGINE LAYER (SWAPPABLE)</div>
        <div class="shift-arch-desc">
          <span class="badge badge-purple" style="margin:2px;">LangGraph</span>
          <span class="badge badge-purple" style="margin:2px;">CrewAI</span>
          <span class="badge badge-purple" style="margin:2px;">AutoGen</span>
          <span class="badge badge-purple" style="margin:2px;">Custom Python</span>
          <span class="badge badge-purple" style="margin:2px;">n8n</span>
        </div>
        <div style="font-size:0.52rem;color:var(--purple);margin-top:6px;font-family:var(--font-mono);letter-spacing:1px;">CLIENT CHOOSES BASED ON EXISTING STACK</div>
      </div>
      <div class="shift-arch-arrow">&#x25BC;</div>
      <div class="shift-arch-layer" style="background:var(--cyan-dim);border-color:var(--cyan);">
        <div class="shift-arch-label" style="color:var(--cyan);">INFRASTRUCTURE LAYER</div>
        <div class="shift-arch-desc">PAM APIs (CyberArk source, Devolutions, Keeper, MiniOrange) &middot; MCP Servers &middot; State Store &middot; Audit Logger</div>
        <div style="font-size:0.52rem;color:var(--cyan);margin-top:6px;font-family:var(--font-mono);letter-spacing:1px;">VENDOR-AGNOSTIC ADAPTERS</div>
      </div>
    </div>

    <div style="margin-top:16px;">
      <div style="font-weight:700;color:var(--text-bright);margin-bottom:8px;font-size:0.72rem;">What SHIFT Defines</div>
      <ul style="margin:0;padding-left:18px;line-height:2;font-size:0.68rem;">
        <li><strong>15 agent contracts</strong> — inputs, outputs, gates, dependencies</li>
        <li><strong>8-phase lifecycle</strong> — P0 through P7 with duration estimates</li>
        <li><strong>ETL pipeline spec</strong> — 7-step FREEZE&rarr;UNFREEZE with crash recovery</li>
        <li><strong>ML feedback loop</strong> — EWMA + Isolation Forest anomaly detection, LightGBM + rule blending for NHI classification</li>
        <li><strong>Yellow checkpoint state machine</strong> — 6-state lifecycle with SLA windows</li>
        <li><strong>Human gate protocol</strong> — 17 approval gates with evidence requirements</li>
      </ul>
    </div>

    <div style="margin-top:14px;">
      <div style="font-weight:700;color:var(--text-bright);margin-bottom:8px;font-size:0.72rem;">What SHIFT Does NOT Define</div>
      <ul style="margin:0;padding-left:18px;line-height:2;font-size:0.68rem;">
        <li>Which LLM framework runs the agents</li>
        <li>Which cloud hosts the infrastructure</li>
        <li>Which CI/CD deploys it</li>
      </ul>
    </div>

    <div class="callout teal" style="margin-top:14px;font-size:0.68rem;line-height:1.6;">
      <div class="callout-title" style="font-size:0.72rem;">Why This Matters</div>
      <p>The client is not locked into a vendor SDK. If CrewAI sunsets or LangGraph changes pricing, swap the engine layer — agent logic, phase gates, and ML models carry over unchanged. The same agent specs run on LangGraph (graph-based), CrewAI (role-based), AutoGen (multi-agent chat), or plain Python coordinator (current implementation).</p>
    </div>
  `) +

  _guideSection('The 8 Migration Phases (P0-P7)', `
    <table style="width:100%;border-collapse:collapse;font-size:0.68rem;">
      <thead>
        <tr style="border-bottom:2px solid var(--border);color:var(--text-muted);text-align:left;">
          <th style="padding:6px 8px;">Phase</th>
          <th style="padding:6px 8px;">Name</th>
          <th style="padding:6px 8px;">Duration</th>
          <th style="padding:6px 8px;">Key Focus</th>
          <th style="padding:6px 8px;">Agents</th>
        </tr>
      </thead>
      <tbody>
        ${[
          ['P0', 'Environment Setup', '2-3 weeks', 'Infrastructure provisioning, network, credentials', 'Manual'],
          ['P1', 'Discovery & Assessment', '3-4 weeks', 'Full environment scan, NHI classification, gap analysis', '11, 01, 09, 12, 02, 03'],
          ['P2', 'Infrastructure & Staging', '2-3 weeks', 'Target platform config, template validation, staging tests', '13, 10'],
          ['P3', 'Structure Migration', '2-3 weeks', 'Safe/folder creation, permission mapping, app onboarding setup', '03, 14'],
          ['P4', 'Pilot Migration', '1-2 weeks', 'Small batch ETL, validate end-to-end pipeline', '04, 05'],
          ['P5', 'Production Migration', '4-6 weeks', '5-wave production batches, integrations, compliance evidence', '04, 05, 06, 14, 07'],
          ['P6', 'Parallel Running', '4-6 weeks', 'Dual-system validation, traffic shifting, cutover', '15, 05, 06, 07'],
          ['P7', 'Decommission', '2-3 weeks', 'Source teardown, final audit, project close-out', '07'],
        ].map(r => `
          <tr style="border-bottom:1px solid var(--border-light);">
            <td style="padding:5px 8px;font-weight:700;color:var(--cyan);font-family:var(--font-mono);">${r[0]}</td>
            <td style="padding:5px 8px;color:var(--text-bright);">${r[1]}</td>
            <td style="padding:5px 8px;color:var(--text-muted);">${r[2]}</td>
            <td style="padding:5px 8px;color:var(--text-standard);">${r[3]}</td>
            <td style="padding:5px 8px;font-family:var(--font-mono);color:var(--teal);">${r[4]}</td>
          </tr>
        `).join('')}
      </tbody>
    </table>
    <p style="margin-top:10px;font-size:0.62rem;color:var(--text-muted);">Each phase is gated — human approvals (gates) must pass before advancing. Phase durations are estimates that vary by environment complexity and account volume.</p>
  `) +

  _guideSection('15 AI Agents Explained', `
    <p style="margin-bottom:10px;">Each agent is a specialized Python module in the orchestrator. Agents execute in a deterministic sequence within each phase. Earlier agents feed data to later ones.</p>
    <table style="width:100%;border-collapse:collapse;font-size:0.65rem;">
      <thead>
        <tr style="border-bottom:2px solid var(--border);color:var(--text-muted);text-align:left;">
          <th style="padding:5px 8px;">#</th>
          <th style="padding:5px 8px;">Name</th>
          <th style="padding:5px 8px;">Purpose</th>
          <th style="padding:5px 8px;">Phases</th>
          <th style="padding:5px 8px;">Key Dependencies</th>
        </tr>
      </thead>
      <tbody>
        ${[
          ['01', 'Discovery', 'Scans full CyberArk environment via Applications API', 'P1', 'Agent 11 source data'],
          ['02', 'Gap Analysis', '10-domain maturity assessment across 4 compliance frameworks', 'P1', 'Agent 01 discovery output'],
          ['03', 'Permissions', 'Maps 22 CyberArk permissions to target model', 'P1, P3', 'Agent 01 safe members data'],
          ['04', 'ETL', '7-step ETL pipeline with crash recovery and watchdog', 'P4, P5', 'Agent 10 staging validation'],
          ['05', 'Heartbeat', '10-check post-migration validation', 'P4-P6', 'Agent 04 migrated accounts'],
          ['06', 'Integration', 'CCP/AAM code scanning and repointing', 'P5, P6', 'Agent 04 completed accounts'],
          ['07', 'Compliance', 'PCI-DSS, NIST 800-53, HIPAA, SOX evidence collection', 'P5-P7', 'Agent 05 validation results'],
          ['08', 'Runbook', 'Phase gate management and decommission procedures', 'P6, P7', 'All previous agents'],
          ['09', 'Dependency Mapper', '6 scanners: IIS, Windows services, tasks, Jenkins, scripts, configs', 'P1', 'Agent 01 discovery output'],
          ['10', 'Staging', '10-assertion validation against staging instance', 'P2', 'Agent 13 platform validation'],
          ['11', 'Source Adapter', 'Multi-vendor extraction: CyberArk, BeyondTrust, SS, HashiCorp, cloud', 'P1', 'Config + credentials'],
          ['12', 'NHI Handler', 'Weighted multi-signal classification for non-human identities', 'P1', 'Agent 01 + Agent 11 data'],
          ['13', 'Platform Plugins', 'Validates/exports/imports custom platforms and templates', 'P2', 'Agent 02 gap analysis'],
          ['14', 'Onboarding Factory', '10-step pipeline for new service account onboarding', 'P3, P5', 'Agent 03 permission map'],
          ['15', 'Hybrid Fleet', 'Parallel-run traffic shift management (on-prem + cloud)', 'P6', 'Agent 05 heartbeat data'],
        ].map(r => `
          <tr style="border-bottom:1px solid var(--border-light);">
            <td style="padding:4px 8px;font-weight:700;color:var(--cyan);font-family:var(--font-mono);">${r[0]}</td>
            <td style="padding:4px 8px;color:var(--text-bright);">${r[1]}</td>
            <td style="padding:4px 8px;color:var(--text-standard);">${r[2]}</td>
            <td style="padding:4px 8px;font-family:var(--font-mono);color:var(--teal);">${r[3]}</td>
            <td style="padding:4px 8px;color:var(--text-muted);font-size:0.6rem;">${r[4]}</td>
          </tr>
        `).join('')}
      </tbody>
    </table>
    <p style="margin-top:10px;font-size:0.62rem;color:var(--text-muted);">Two additional SHIFT agents handle documentation generation and portal operations but are not part of the core migration orchestrator.</p>
  `) +

  _guideSection('AI Predictions — 3-Tier Feedback Loop', `
    <p>Predictions are not static rules — they emerge from a 3-tier cross-referencing model that correlates agent outputs through yellow checkpoints.</p>
    <div style="margin:12px 0;">
      <div style="font-weight:700;color:var(--text-bright);margin-bottom:8px;font-size:0.72rem;">Tier 1: Agent Detection</div>
      <p>Each of the 15 agents monitors its domain. When an agent detects an anomaly (e.g., extraction latency exceeding benchmark, permission escalations above threshold), it flags the condition.</p>

      <div style="font-weight:700;color:var(--text-bright);margin:12px 0 8px;font-size:0.72rem;">Tier 2: Yellow Checkpoint Cross-Reference</div>
      <p>If the condition exceeds a threshold, the agent fires a <strong>yellow checkpoint</strong>. Each checkpoint includes a <code style="font-family:var(--font-mono);color:var(--teal);">cross_system_context</code> field that explicitly references OTHER agents' data. For example, checkpoint yc-a01 (source extraction latency) cross-references Agent 09 (dependency mapper) and Agent 12 (NHI handler) to assess whether the latency affects downstream operations.</p>

      <div style="font-weight:700;color:var(--text-bright);margin:12px 0 8px;font-size:0.72rem;">Tier 3: Prediction Engine + Feedback</div>
      <p>The prediction engine correlates multiple checkpoints' cross-references to identify <strong>compounding risks</strong>. A single checkpoint might be informational, but when two or more checkpoints from different phases reference overlapping agents, the engine projects forward impact. Each prediction includes affected phases, affected agents, predicted impact, and a recommended remediation.</p>
      <p>The feedback loop: when a prediction triggers remediation, the affected agent re-executes with the fix applied. This generates new checkpoint data, which feeds back into the prediction engine — creating a continuous improvement cycle.</p>
    </div>
    <p style="font-size:0.62rem;color:var(--text-muted);">See the Predictive Intelligence Flow animation on Mission Control for an interactive walkthrough of this process with three real examples.</p>
  `) +

  _guideSection('Yellow Checkpoints — AI Contextual Awareness', `
    <p>Yellow checkpoints are the orchestrator's mechanism for cross-phase contextual awareness. They are NOT simple alerts — they carry structured context that enables the prediction engine.</p>
    <div style="margin:10px 0;">
      <div style="font-weight:700;color:var(--amber);margin-bottom:6px;font-size:0.72rem;">Two Types</div>
      <ul style="margin:0;padding-left:18px;line-height:2;">
        <li><strong>Procedural</strong> — Mandatory phase gate checks (e.g., "staging validation must pass before P4")</li>
        <li><strong>AI Detected</strong> — Orchestrator-identified conflicts, decisions, or forecasted errors</li>
      </ul>
    </div>
    <div style="margin:10px 0;">
      <div style="font-weight:700;color:var(--amber);margin-bottom:6px;font-size:0.72rem;">State Machine (6 States)</div>
      <p><code style="font-family:var(--font-mono);color:var(--teal);">FIRE</code> &rarr; <code style="font-family:var(--font-mono);color:var(--teal);">CLASSIFY</code> &rarr; <code style="font-family:var(--font-mono);color:var(--teal);">NOTIFY</code> &rarr; <code style="font-family:var(--font-mono);color:var(--teal);">WINDOW</code> &rarr; <code style="font-family:var(--font-mono);color:var(--teal);">BOUNDARY</code> &rarr; <code style="font-family:var(--font-mono);color:var(--teal);">RESOLVE</code></p>
      <p>Each checkpoint has an SLA window (configurable per severity). If the window expires without resolution, the checkpoint escalates to RED, halting the pipeline.</p>
    </div>
    <div style="margin:10px 0;">
      <div style="font-weight:700;color:var(--amber);margin-bottom:6px;font-size:0.72rem;">Accumulation Thresholds</div>
      <p>Each phase has a maximum number of open checkpoints. When the threshold is reached, the phase is blocked until checkpoints are resolved. This prevents checkpoint fatigue.</p>
    </div>
  `) +

  _guideSection('Wave Execution & ETL Pipeline', `
    <p>Phase 5 (Production Migration) executes in 5 waves, each processing a batch of accounts through the 7-step ETL pipeline.</p>
    <div style="margin:10px 0;">
      <div style="font-weight:700;color:var(--text-bright);margin-bottom:6px;font-size:0.72rem;">5 Waves</div>
      <table style="width:100%;border-collapse:collapse;font-size:0.65rem;">
        <thead>
          <tr style="border-bottom:1px solid var(--border);color:var(--text-muted);text-align:left;">
            <th style="padding:4px 8px;">Wave</th>
            <th style="padding:4px 8px;">Focus</th>
            <th style="padding:4px 8px;">Volume</th>
          </tr>
        </thead>
        <tbody>
          ${[
            ['1', 'Low-risk service accounts', '~200'],
            ['2', 'Standard privileged accounts', '~350'],
            ['3', 'NHI + complex dependencies', '~550'],
            ['4', 'High-risk + compliance-sensitive', '~400'],
            ['5', 'Remaining + cleanup', '~200'],
          ].map(r => `
            <tr style="border-bottom:1px solid var(--border-light);">
              <td style="padding:4px 8px;font-weight:700;color:var(--cyan);font-family:var(--font-mono);">${r[0]}</td>
              <td style="padding:4px 8px;color:var(--text-standard);">${r[1]}</td>
              <td style="padding:4px 8px;color:var(--text-muted);">${r[2]}</td>
            </tr>
          `).join('')}
        </tbody>
      </table>
    </div>
    <div style="margin:10px 0;">
      <div style="font-weight:700;color:var(--text-bright);margin-bottom:6px;font-size:0.72rem;">7-Step ETL Pipeline</div>
      <ol style="margin:0;padding-left:18px;line-height:2;font-size:0.68rem;">
        <li><strong>FREEZE</strong> — Lock source accounts (CPM disabled, rotations paused)</li>
        <li><strong>EXPORT</strong> — Extract account data + retrieve passwords via PVWA API</li>
        <li><strong>TRANSFORM</strong> — Map fields, resolve platform/template, slug usernames</li>
        <li><strong>SAFE/FOLDER CREATION</strong> — Create target containers with permissions</li>
        <li><strong>IMPORT</strong> — Create accounts/secrets in target platform</li>
        <li><strong>HEARTBEAT</strong> — Validate imported accounts can connect</li>
        <li><strong>UNFREEZE</strong> — Re-enable CPM/rotation on source (rollback safety)</li>
      </ol>
    </div>
    <div style="margin:10px 0;">
      <div style="font-weight:700;color:var(--text-bright);margin-bottom:6px;font-size:0.72rem;">Safety Features</div>
      <ul style="margin:0;padding-left:18px;line-height:2;font-size:0.68rem;">
        <li><strong>Watchdog timer</strong> — Auto-unfreezes accounts if pipeline stalls (default 120 min)</li>
        <li><strong>Crash recovery</strong> — Frozen account registry + signal handlers for safe shutdown</li>
        <li><strong>Startup recovery</strong> — On restart, detects frozen accounts and initiates emergency unfreeze</li>
      </ul>
    </div>
  `) +

  _guideSection('Option A vs Option B', `
    <table style="width:100%;border-collapse:collapse;font-size:0.65rem;">
      <thead>
        <tr style="border-bottom:2px solid var(--border);color:var(--text-muted);text-align:left;">
          <th style="padding:6px 8px;">Aspect</th>
          <th style="padding:6px 8px;color:var(--blue);">Option A: Devolutions</th>
          <th style="padding:6px 8px;color:var(--cyan);">Option B: Keeper</th>
          <th style="padding:6px 8px;color:var(--purple);">Option C: MiniOrange</th>
        </tr>
      </thead>
      <tbody>
        ${[
          ['Timeline', '44 weeks', '36 weeks', '32 weeks'],
          ['Permission Model', '22 &rarr; Vault roles (LOSSY)', '22 &rarr; 4 axes (LOSSY)', '22 &rarr; 3 levels (most loss)'],
          ['Data Structure', 'Safe &rarr; Vault Entry (flat)', 'Safe &rarr; 3-tier (PAM Config/Resource/User)', 'Safe &rarr; Resource Group'],
          ['Platforms', 'Platform &rarr; Entry Type', 'Platform &rarr; PAM Template', 'Platform &rarr; Policy Template'],
          ['API Surface', 'REST + RDM Agent API', 'Keeper REST + KSM SDK', 'REST API only'],
          ['Audit Logs', 'Do NOT transfer', 'Do NOT transfer', 'Do NOT transfer'],
          ['PSM Recordings', 'Cannot migrate — RDM sessions new', 'Cannot migrate — KCM sessions new', 'Cannot migrate'],
          ['Integration Rework', 'CCP/AAM &rarr; RDM Agent scripts', 'CCP/AAM &rarr; KSM (40+ integrations)', 'CCP/AAM &rarr; REST API only'],
          ['Rotation', 'RDM Agent scripts (~custom per platform)', 'Gateway scripts (~25-30 platforms)', 'Basic scripts (~15-20 platforms)'],
          ['Risk Level', 'Medium — flat model reduces structural risk', 'Medium — 3-tier rebuild + Cisco gear gap', 'Higher — lowest PAM depth at Cisco scale'],
        ].map(r => `
          <tr style="border-bottom:1px solid var(--border-light);">
            <td style="padding:5px 8px;font-weight:600;color:var(--text-bright);">${r[0]}</td>
            <td style="padding:5px 8px;color:var(--blue);">${r[1]}</td>
            <td style="padding:5px 8px;color:var(--cyan);">${r[2]}</td>
            <td style="padding:5px 8px;color:var(--purple);">${r[3] || '—'}</td>
          </tr>
        `).join('')}
      </tbody>
    </table>
    <p style="margin-top:10px;font-size:0.62rem;color:var(--text-muted);">Toggle between Option A, B, and C using the sidebar switch. All pages update to show the appropriate data, checkpoints, predictions, and timelines for each option.</p>
  `) +

  _guideSection('Secret Migration — CyberArk Account Object vs Target', `
    <p style="margin-bottom:12px;">The <strong>CyberArk Account Object</strong> is the atomic unit of migration. Every account stored in a Safe has a structured JSON object. The Target PAM platform may use a completely different schema — and the SHIFT ETL Transform step (Agent 04) handles this translation automatically.</p>

    <h4 style="color:var(--cyan);font-family:var(--font-mono);font-size:0.72rem;margin:14px 0 8px;">CyberArk Account Object — Fields</h4>
    <table style="width:100%;border-collapse:collapse;font-size:0.65rem;margin-bottom:14px;">
      <thead><tr style="border-bottom:1px solid var(--border);">
        <th style="padding:6px 8px;text-align:left;color:var(--text-muted);font-weight:600;">Field</th>
        <th style="padding:6px 8px;text-align:left;color:var(--text-muted);font-weight:600;">Type</th>
        <th style="padding:6px 8px;text-align:left;color:var(--text-muted);font-weight:600;">Description</th>
      </thead>
      <tbody>
        <tr style="border-bottom:1px solid var(--border);"><td style="padding:5px 8px;font-family:var(--font-mono);color:var(--cyan);">name</td><td style="padding:5px 8px;color:var(--text-muted);">string</td><td style="padding:5px 8px;color:var(--text-standard);">Unique account name within the safe</td></tr>
        <tr style="border-bottom:1px solid var(--border);"><td style="padding:5px 8px;font-family:var(--font-mono);color:var(--cyan);">address</td><td style="padding:5px 8px;color:var(--text-muted);">string</td><td style="padding:5px 8px;color:var(--text-standard);">Target system hostname or IP</td></tr>
        <tr style="border-bottom:1px solid var(--border);"><td style="padding:5px 8px;font-family:var(--font-mono);color:var(--cyan);">userName</td><td style="padding:5px 8px;color:var(--text-muted);">string</td><td style="padding:5px 8px;color:var(--text-standard);">Account username on the target system</td></tr>
        <tr style="border-bottom:1px solid var(--border);"><td style="padding:5px 8px;font-family:var(--font-mono);color:var(--cyan);">platformId</td><td style="padding:5px 8px;color:var(--text-muted);">string</td><td style="padding:5px 8px;color:var(--text-standard);">CyberArk platform type (e.g., OracleDB, WinDomain, UnixSSH)</td></tr>
        <tr style="border-bottom:1px solid var(--border);"><td style="padding:5px 8px;font-family:var(--font-mono);color:var(--cyan);">safeName</td><td style="padding:5px 8px;color:var(--text-muted);">string</td><td style="padding:5px 8px;color:var(--text-standard);">Safe containing this account</td></tr>
        <tr style="border-bottom:1px solid var(--border);"><td style="padding:5px 8px;font-family:var(--font-mono);color:var(--cyan);">platformAccountProperties</td><td style="padding:5px 8px;color:var(--text-muted);">object</td><td style="padding:5px 8px;color:var(--text-standard);">Platform-specific fields (e.g., Port, Database, Domain)</td></tr>
        <tr style="border-bottom:1px solid var(--border);"><td style="padding:5px 8px;font-family:var(--font-mono);color:var(--cyan);">secretType</td><td style="padding:5px 8px;color:var(--text-muted);">string</td><td style="padding:5px 8px;color:var(--text-standard);">Always "password" for managed accounts</td></tr>
        <tr><td style="padding:5px 8px;font-family:var(--font-mono);color:var(--cyan);">secret</td><td style="padding:5px 8px;color:var(--text-muted);">string</td><td style="padding:5px 8px;color:var(--text-standard);">Write-only — retrieved via separate Retrieve API call</td></tr>
      </tbody>
    </table>

    <h4 style="color:var(--cyan);font-family:var(--font-mono);font-size:0.72rem;margin:14px 0 8px;">Target: Keeper — 3-Tier Hierarchy (Structural Delta)</h4>
    <p style="font-size:0.68rem;color:var(--text-standard);line-height:1.7;margin-bottom:10px;">Keeper uses a 3-tier hierarchy: <code style="font-family:var(--font-mono);color:var(--cyan);">PAM Config → PAM Resource → PAM User</code>. A single CyberArk Account maps to a <code style="font-family:var(--font-mono);color:var(--cyan);">pamUser</code> record linked to a <code style="font-family:var(--font-mono);color:var(--cyan);">pamMachine</code> or <code style="font-family:var(--font-mono);color:var(--cyan);">pamDatabase</code> resource. The cyberark-import tool handles bulk import (~20% of work); the remaining 80% is post-import transformation to build the correct 3-tier linkage. Each CyberArk Safe may become 2 Keeper Shared Folders (one for credentials, one for PAM resources).</p>

    <h4 style="color:var(--blue);font-family:var(--font-mono);font-size:0.72rem;margin:14px 0 8px;">Target: Devolutions — Vault Entry Model</h4>
    <table style="width:100%;border-collapse:collapse;font-size:0.65rem;margin-bottom:14px;">
      <thead><tr style="border-bottom:1px solid var(--border);">
        <th style="padding:6px 8px;text-align:left;color:var(--text-muted);font-weight:600;">CyberArk Field</th>
        <th style="padding:6px 8px;text-align:left;color:var(--text-muted);font-weight:600;">Devolutions Field</th>
        <th style="padding:6px 8px;text-align:left;color:var(--text-muted);font-weight:600;">Notes</th>
      </thead>
      <tbody>
        <tr style="border-bottom:1px solid var(--border);"><td style="padding:5px 8px;font-family:var(--font-mono);color:var(--cyan);">safeName</td><td style="padding:5px 8px;font-family:var(--font-mono);color:var(--amber);">folderId (int)</td><td style="padding:5px 8px;color:var(--text-standard);">Safe → Folder hierarchy, resolved via folder map built in P3</td></tr>
        <tr style="border-bottom:1px solid var(--border);"><td style="padding:5px 8px;font-family:var(--font-mono);color:var(--cyan);">platformId</td><td style="padding:5px 8px;font-family:var(--font-mono);color:var(--amber);">secretTemplateId (int)</td><td style="padding:5px 8px;color:var(--text-standard);">Platform → Secret Template, resolved via template map (Agent 13)</td></tr>
        <tr style="border-bottom:1px solid var(--border);"><td style="padding:5px 8px;font-family:var(--font-mono);color:var(--cyan);">platformAccountProperties</td><td style="padding:5px 8px;font-family:var(--font-mono);color:var(--amber);">items[] array</td><td style="padding:5px 8px;color:var(--text-standard);">Object flattened into fieldName/itemValue pairs per template definition</td></tr>
        <tr style="border-bottom:1px solid var(--border);"><td style="padding:5px 8px;font-family:var(--font-mono);color:var(--cyan);">userName + address</td><td style="padding:5px 8px;font-family:var(--font-mono);color:var(--amber);">items[] fields</td><td style="padding:5px 8px;color:var(--text-standard);">Username and Server become items with fieldName matching template</td></tr>
        <tr><td style="padding:5px 8px;font-family:var(--font-mono);color:var(--cyan);">secret</td><td style="padding:5px 8px;font-family:var(--font-mono);color:var(--amber);">items[].itemValue (password field)</td><td style="padding:5px 8px;color:var(--text-standard);">Retrieved separately via Retrieve API, then set as password item value</td></tr>
      </tbody>
    </table>

    <h4 style="color:var(--teal);font-family:var(--font-mono);font-size:0.72rem;margin:14px 0 8px;">What SHIFT Does</h4>
    <ul style="font-size:0.68rem;color:var(--text-standard);line-height:1.8;padding-left:18px;">
      <li>Builds <strong>folder map</strong> during P3 (Safe name → folder ID) before ETL begins</li>
      <li>Builds <strong>template map</strong> during P2 via Agent 13 (platformId → secretTemplateId)</li>
      <li>Retrieves passwords via <code style="font-family:var(--font-mono);color:var(--teal);">POST /Accounts/{id}/Password/Retrieve</code> during EXPORT step</li>
      <li>Constructs <code style="font-family:var(--font-mono);color:var(--teal);">items[]</code> array during TRANSFORM step by flattening platformAccountProperties</li>
      <li>Skips accounts where password retrieval fails — flagged in audit log for manual review</li>
    </ul>

    <div class="callout amber" style="margin-top:14px;">
      <div class="callout-title">Audit Log Discontinuity</div>
      CyberArk audit history does <strong>NOT</strong> migrate to any of the three target platforms (Devolutions, Keeper, MiniOrange). The audit trail restarts at the migration date. For compliance continuity, export and archive CyberArk audit logs before decommissioning — Agent 07 handles this automatically as part of the P7 Close-Out phase.
    </div>
  `) +

  _guideSection('Password Rotation Connectors — CPM vs RPC vs Native', `
    <p style="margin-bottom:12px;">Password rotation is the most operationally critical connector. <strong>CyberArk CPM</strong> (Central Policy Manager) handles rotation in the source system. Each target platform uses a different rotation mechanism, and migration effort varies significantly.</p>

    <table style="width:100%;border-collapse:collapse;font-size:0.65rem;margin-bottom:16px;">
      <thead><tr style="border-bottom:1px solid var(--border);">
        <th style="padding:6px 8px;text-align:left;color:var(--text-muted);font-weight:600;">Connector</th>
        <th style="padding:6px 8px;text-align:left;color:var(--text-muted);font-weight:600;">Platform</th>
        <th style="padding:6px 8px;text-align:left;color:var(--text-muted);font-weight:600;">How It Works</th>
        <th style="padding:6px 8px;text-align:left;color:var(--text-muted);font-weight:600;">Migration Path</th>
      </thead>
      <tbody>
        <tr style="border-bottom:1px solid var(--border);"><td style="padding:5px 8px;font-family:var(--font-mono);color:var(--cyan);">CPM</td><td style="padding:5px 8px;color:var(--text-standard);">CyberArk PAS (source)</td><td style="padding:5px 8px;color:var(--text-standard);">Reads platform .ini file, connects to target system, generates new password, pushes to vault</td><td style="padding:5px 8px;color:var(--amber);">Paused during FREEZE step, re-enabled after UNFREEZE</td></tr>
        <tr style="border-bottom:1px solid var(--border);"><td style="padding:5px 8px;font-family:var(--font-mono);color:var(--blue);">RDM Agent</td><td style="padding:5px 8px;color:var(--text-standard);">Devolutions (Option A)</td><td style="padding:5px 8px;color:var(--text-standard);">Script-based via Devolutions RDM Agent. Custom rotation scripts per Entry type. No native .ini plugin format.</td><td style="padding:5px 8px;color:var(--amber);">Must be written per platform — Cisco IOS/NX-OS/ASA require custom scripts</td></tr>
        <tr style="border-bottom:1px solid var(--border);"><td style="padding:5px 8px;font-family:var(--font-mono);color:var(--cyan);">Gateway</td><td style="padding:5px 8px;color:var(--text-standard);">Keeper (Option B)</td><td style="padding:5px 8px;color:var(--text-standard);">Keeper Gateway handles rotation (~25-30 platforms). Custom scripts for non-standard platforms. Docker container, 4CPU/16GB RAM.</td><td style="padding:5px 8px;color:var(--red);">Cisco network gear (IOS, NX-OS, ASA, Meraki) requires custom Gateway scripts — critical gap for Cisco</td></tr>
        <tr><td style="padding:5px 8px;font-family:var(--font-mono);color:var(--purple);">Agent</td><td style="padding:5px 8px;color:var(--text-standard);">MiniOrange (Option C)</td><td style="padding:5px 8px;color:var(--text-standard);">MiniOrange Agent handles ~15-20 platforms. Very limited Cisco network gear support.</td><td style="padding:5px 8px;color:var(--red);">Highest gap — most Cisco platform types unsupported natively</td></tr>
      </tbody>
    </table>

    <h4 style="color:var(--teal);font-family:var(--font-mono);font-size:0.72rem;margin:14px 0 8px;">Rotation During Migration — FREEZE / UNFREEZE</h4>
    <p style="font-size:0.68rem;color:var(--text-standard);line-height:1.7;margin-bottom:10px;">
      During ETL, accounts are <strong>frozen</strong> by disabling CPM management:
      <code style="font-family:var(--font-mono);color:var(--cyan);">PUT /Accounts/{id}</code> with <code style="font-family:var(--font-mono);color:var(--cyan);">automaticManagementEnabled: false</code>.
      After successful migration and heartbeat validation, UNFREEZE re-enables rotation via <code style="font-family:var(--font-mono);color:var(--cyan);">true</code>.
      If the pipeline crashes mid-migration, the Watchdog timer automatically unfreezes all accounts within <strong>120 minutes</strong> — preventing accounts from being permanently locked out of rotation.
    </p>

    <div class="callout teal" style="margin-top:14px;">
      <div class="callout-title">Oracle DB Rotation — CPM vs RPC Detail</div>
      <strong>CyberArk CPM (source):</strong> Uses the built-in <code style="font-family:var(--font-mono);color:var(--teal);">OracleDB</code> platform with <code style="font-family:var(--font-mono);color:var(--teal);">Process.ini</code> that executes <code style="font-family:var(--font-mono);color:var(--teal);">ALTER USER {username} IDENTIFIED BY {new_password}</code> via the Oracle thin JDBC driver.<br><br>
      <strong>Devolutions (Option A):</strong> Must be implemented as a PowerShell or Python script registered as an RDM Agent rotation script. Uses <code style="font-family:var(--font-mono);color:var(--blue);">Oracle.ManagedDataAccess.Client</code> (.NET managed driver). Agent 13 flags this as required custom work during P2.<br><br>
      <strong>Keeper (Option B):</strong> Keeper Gateway includes a pre-built Oracle rotation plugin. Requires Gateway node connectivity to Oracle listener port. Validate in staging — Agent 13 checks Oracle template mapping.<br><br>
      <strong>MiniOrange (Option C):</strong> Oracle rotation requires custom agent script. MiniOrange has no native Oracle.ManagedDataAccess plugin. Manual verification required.
    </div>
  `) +

  _guideSection('&#x1F3AF; Cisco Vendor Recommendation — Devolutions / Keeper / MiniOrange', `
    <p style="margin-bottom:12px;font-size:0.72rem;color:var(--text-standard);line-height:1.7;">
      Cisco is migrating <strong>off CyberArk entirely</strong> (vendor is now owned by a Cisco competitor).
      Delinea was evaluated and turned down. The three front-runners are assessed below for Cisco's scale of
      <strong>50,000–250,000 accounts</strong> across Windows, Unix/Linux, databases, cloud IAM, and
      Cisco-proprietary network gear (IOS, NX-OS, ASA, Meraki, Catalyst).
    </p>

    <div class="callout teal" style="margin-bottom:16px;">
      <div class="callout-title" style="color:var(--cyan)">&#x2714; Primary Recommendation: Keeper Security (Option B)</div>
      <p style="font-size:0.72rem;line-height:1.7;">
        <strong>Zero-knowledge AES-256-GCM</strong> encryption — server never sees plaintext secrets.<br>
        <strong>FedRAMP High</strong> authorized (March 2026) — relevant for Cisco government engagements.<br>
        <strong>KSM (Keeper Secrets Manager)</strong> — 40+ native integrations replace CCP/AAM: Kubernetes, Terraform, Ansible, GitHub Actions, AWS Secrets Manager, Azure Key Vault, Vault-compatible.<br>
        <strong>KCM (Keeper Connection Manager)</strong> — Apache Guacamole session recording, browser-native, no Windows RDS licensing.<br>
        <strong style="color:var(--amber)">Key gap:</strong> ~25-30 rotation platforms vs. CyberArk 225+. Cisco IOS/NX-OS/ASA require custom Gateway scripts. Gateway HA cluster required at 250K+ accounts (4 CPU / 16GB per node).
      </p>
    </div>

    <div class="callout" style="border-color:var(--blue);background:var(--blue-dim);margin-bottom:16px;">
      <div class="callout-title" style="color:var(--blue)">&#x25A3; Secondary Recommendation: Devolutions (Option A)</div>
      <p style="font-size:0.72rem;line-height:1.7;">
        <strong>Strongest session management</strong> of the three: RDM built-in (RDP, SSH, VNC, 100+ protocols), rich session recording, no extra licensing.<br>
        <strong>Flat data model</strong> (Vault → Entry) similar to CyberArk — lower structural migration risk than Keeper's 3-tier rebuild.<br>
        <strong>Mid-market heritage</strong> — validate at 100K+ accounts before committing as sole PAM. Architecture review recommended for Cisco's 250K scale.<br>
        <strong>Best use:</strong> Session management layer for on-prem/hybrid Cisco infrastructure. Pair with Keeper for secrets/DevOps layer.
      </p>
    </div>

    <div class="callout amber" style="margin-bottom:16px;">
      <div class="callout-title" style="color:var(--amber)">&#x26A0; Complementary Only: MiniOrange (Option C)</div>
      <p style="font-size:0.72rem;line-height:1.7;">
        <strong>IAM-native</strong> — best positioned as MFA/SSO enforcement layer on top of Keeper or Devolutions.<br>
        <strong>Lowest cost</strong> of the three, but PAM feature depth is unproven at Cisco's 250K scale.<br>
        <strong>Not recommended</strong> as standalone PAM replacement for Cisco's full privileged account estate.<br>
        <strong>Best use:</strong> MFA front-door for Cisco's identity layer. Not a CyberArk vault replacement.
      </p>
    </div>

    <div style="overflow-x:auto;margin-top:16px;">
      <table style="width:100%;border-collapse:collapse;font-size:0.68rem;">
        <thead>
          <tr style="border-bottom:1px solid var(--border);">
            <th style="padding:6px 8px;text-align:left;color:var(--text-muted);">Dimension</th>
            <th style="padding:6px 8px;color:var(--blue);">Devolutions (A)</th>
            <th style="padding:6px 8px;color:var(--cyan);">Keeper (B) &#x2713;</th>
            <th style="padding:6px 8px;color:var(--purple);">MiniOrange (C)</th>
          </tr>
        </thead>
        <tbody>
          ${[
            ['Timeline', '44 weeks', '36 weeks', '32 weeks'],
            ['Zero-Knowledge', '✗ Server-side', '✓ AES-256-GCM', '✗ Server-side'],
            ['FedRAMP', '✗ None', '✓ High (March 2026)', '✗ None'],
            ['Session Mgmt', '✓ RDM (strongest)', '✓ KCM (Guacamole)', '⚠ Basic only'],
            ['DevOps/NHI', '⚠ REST API only', '✓ KSM 40+ integrations', '✗ REST API only'],
            ['Cisco Network Gear', '⚠ Custom scripts', '⚠ Custom Gateway scripts', '✗ Very limited'],
            ['Scale at 250K', '⚠ Validate needed', '⚠ HA Gateway cluster', '✗ Untested'],
            ['Permission Loss', '22→Vault roles', '22→4 axes', '22→3 levels (most loss)'],
            ['Audit Continuity', '✗ Manual export', '✗ Manual export', '✗ Manual export'],
            ['Recommendation', 'SESSION LAYER', 'PRIMARY PAM', 'MFA/SSO ONLY'],
          ].map(row => `
            <tr style="border-bottom:1px solid var(--border);">
              <td style="padding:5px 8px;font-weight:600;color:var(--text-bright)">${row[0]}</td>
              <td style="padding:5px 8px;color:var(--text-standard)">${row[1]}</td>
              <td style="padding:5px 8px;color:var(--text-standard)">${row[2]}</td>
              <td style="padding:5px 8px;color:var(--text-standard)">${row[3]}</td>
            </tr>`).join('')}
        </tbody>
      </table>
    </div>
  `) +

  _guideSection('&#x1F512; Separation of Duties — iOPEX as Migration Integrator', `
    <p style="margin-bottom:14px;font-size:0.72rem;color:var(--text-standard);line-height:1.7;">
      iOPEX operates as the migration integrator throughout all phases — building, operating, and running the
      15-agent orchestration platform. Cisco retains accountability for every approval gate.
      The core principle is simple: <strong>the team that performs the work cannot also sign off on it.</strong>
      This is enforced mechanically through Agent 08 gate logic and is visible on every gate card in the Gate Tracker tab.
    </p>

    <div style="font-size:0.65rem;font-family:var(--font-mono);color:var(--text-muted);margin-bottom:10px;text-transform:uppercase;letter-spacing:.06em;">The 6 Core Separation Rules</div>

    <div style="display:grid;gap:8px;margin-bottom:20px;">
      ${[
        ['1', 'var(--purple)', 'iOPEX Runs — Cisco Approves Every Gate',
         'iOPEX Migration Engineers execute all agent runs, ETL waves, and deliverable production. No gate in the program can be approved by iOPEX. Every gate requires a named Cisco approver who is independent of the team that performed the work. This applies from g1 (Kick-off) through g14 (Final Sign-off).',
         'Agent 08 enforces this mechanically — a gate cannot reach APPROVED status without the required Cisco approver roles signing off.'],

        ['2', 'var(--red)', 'Permission Mapping Approval is Cisco Security Only (PCI-DSS 7.1)',
         'Agent 03 produces the permission escalation and loss report. iOPEX has zero approval authority over this output. Cisco Security Architect must independently review every escalation flag before Phase 3 proceeds. This is a PCI-DSS Requirement 7.1 dual-control: the team that performs a control cannot also approve it.',
         'Gate g5 (Structure Approval) hard-blocks Phase 4 until Cisco Security sign-off is recorded. No delegation to iOPEX is permitted under any circumstances.'],

        ['3', 'var(--amber)', 'NHI Ownership Can Only Be Declared by App Owners',
         'iOPEX agents classify non-human identities using platform signals, name patterns, and safe name patterns. AI confidence scores are indicators, not declarations. Only the application team that owns the workload can confirm that a service account belongs to them and that its dependency chains are complete.',
         'Gate g2 (NHI Classification Review) requires individual App Owner acknowledgment within 5 business days. iOPEX cannot mark NHI owners as confirmed on their behalf.'],

        ['4', 'var(--cyan)', 'Application Functionality is Declared by App Owners — Not iOPEX',
         'After each wave and at the pilot gate (g6), iOPEX provides heartbeat success rates and integrity check results. These are technical metrics — they confirm the credential exists and rotates. They do not confirm the application works. Only the application owner can confirm their end-to-end workflow functions in the target system.',
         'Pilot gate g6 is a hard block on all production waves. App Owners must physically verify access in the target. iOPEX heartbeat results are necessary but not sufficient.'],

        ['5', 'var(--red)', 'SOX Dual-Control on NHI Rotation Certification (Wave 3)',
         'Wave 3 migrates 554 NHI accounts and configures rotation policies in the target. The team that configures a control (iOPEX setting rotation policies) cannot also certify that the control is operating correctly. Cisco Compliance must independently verify rotation policies are active at gate g9.',
         'SOX Section 404 requires dual-control for credential management operations. Gate g9 requires Compliance sign-off in addition to App Owner confirmation. iOPEX cannot satisfy both roles.'],

        ['6', 'var(--red)', 'Point-of-No-Return (g13) Requires Maximum Cisco Authority — iOPEX Has Zero Approval Power',
         'Gate g13 (Cutover Approval) sets the source CyberArk vault to read-only — the last reversible step before decommission. iOPEX presents the evidence: parallel-run metrics, final validation report, all App Owner sign-offs, and compliance packages. iOPEX then waits. All three independent Cisco approvers (CAB, Exec Sponsor, Compliance) must authorize before iOPEX executes the read-only switch.',
         'This is the highest-authority gate in the program. If any approver is unavailable or withholds approval, the migration pauses. iOPEX cannot proceed based on partial approvals or verbal authorization.'],

      ].map(([num, color, title, body, enforcement]) => `
        <div style="padding:14px 16px;background:var(--bg-surface);border:1px solid var(--border);border-left:4px solid ${color};border-radius:4px;">
          <div style="display:flex;gap:10px;align-items:baseline;margin-bottom:7px;">
            <div style="font-family:var(--font-mono);font-size:0.65rem;color:${color};font-weight:800;min-width:16px;">${num}</div>
            <div style="font-size:0.7rem;font-weight:700;color:var(--text-bright);line-height:1.4;">${title}</div>
          </div>
          <div style="font-size:0.67rem;color:var(--text-standard);line-height:1.75;margin-bottom:8px;padding-left:26px;">${body}</div>
          <div style="margin-left:26px;padding:6px 10px;background:var(--bg-base);border-left:2px solid ${color};font-size:0.62rem;font-family:var(--font-mono);color:var(--text-muted);line-height:1.6;"><strong style="color:${color};">ENFORCED:</strong> ${enforcement}</div>
        </div>
      `).join('')}
    </div>

    <div style="font-size:0.65rem;font-family:var(--font-mono);color:var(--text-muted);margin-bottom:8px;text-transform:uppercase;letter-spacing:.06em;">RACI Summary — iOPEX vs Cisco by Activity</div>
    <div style="overflow-x:auto;margin-bottom:10px;">
      <table style="width:100%;border-collapse:collapse;font-size:0.64rem;">
        <thead>
          <tr style="border-bottom:1px solid var(--border);">
            <th style="padding:6px 10px;text-align:left;color:var(--text-muted);">Activity</th>
            <th style="padding:6px 10px;text-align:center;color:var(--cyan);">iOPEX</th>
            <th style="padding:6px 10px;text-align:center;color:var(--green);">Cisco Accountable</th>
            <th style="padding:6px 10px;text-align:left;color:var(--text-muted);">Cisco Team</th>
          </tr>
        </thead>
        <tbody>
          ${[
            ['Run discovery agents (01, 09, 11, 12)',   'R',  'I',  'PAM Owner'],
            ['Confirm NHI ownership',                   'C',  'A/R','App Owners'],
            ['Accept compliance risk / gap findings',   'C',  'A/R','Compliance + Exec Sponsor'],
            ['Provision Keeper Gateway + network rules','I',  'A/R','NOC/Infra + NSEC'],
            ['Run permission mapping (Agent 03)',        'R',  'I',  '—'],
            ['Approve permission mapping output',       '✗',  'A/R','Security Architect'],
            ['Execute ETL waves (Agent 04)',             'R',  'I',  '—'],
            ['Confirm wave accounts are accessible',    'C',  'A/R','App Owners (per wave)'],
            ['Certify NHI rotation policies active',    'C',  'A/R','Compliance'],
            ['Deploy integration replacement code',     'R',  'I',  '—'],
            ['Approve production app code (CCP→KSM)',   'C',  'A/R','Dev Leads'],
            ['Declare migration complete',              'C',  'A/R','Compliance + PAM Owner'],
            ['Authorize source set-to-read-only',       '✗',  'A/R','CAB + Exec Sponsor'],
            ['Accept platform ownership post-migration','I',  'A/R','Operations'],
          ].map((row, i) => `
            <tr style="border-bottom:1px solid var(--border);${i % 2 === 1 ? 'background:var(--bg-surface);' : ''}">
              <td style="padding:5px 10px;color:var(--text-bright);font-weight:500">${row[0]}</td>
              <td style="padding:5px 10px;text-align:center;font-family:var(--font-mono);font-weight:700;color:${row[1] === '✗' ? 'var(--red)' : row[1] === 'R' ? 'var(--cyan)' : 'var(--text-muted)'}">${row[1]}</td>
              <td style="padding:5px 10px;text-align:center;font-family:var(--font-mono);font-weight:700;color:var(--green)">${row[2]}</td>
              <td style="padding:5px 10px;color:var(--text-muted)">${row[3]}</td>
            </tr>`).join('')}
        </tbody>
      </table>
    </div>
    <div style="font-size:0.6rem;color:var(--text-muted);font-style:italic;">R = Responsible (does the work) &nbsp;·&nbsp; A = Accountable (owns the outcome) &nbsp;·&nbsp; C = Consulted &nbsp;·&nbsp; I = Informed &nbsp;·&nbsp; ✗ = Explicitly prohibited</div>
  `) +

  _guideSection('&#x1F9E9; Hybrid PAM Architecture — Full Coverage Model', `
    <p style="margin-bottom:14px;font-size:0.72rem;color:var(--text-standard);line-height:1.7;">
      No single front-runner covers 100% of Cisco's PAM requirements at enterprise scale. The recommended posture is a
      <strong>layered hybrid</strong>: Keeper as the primary secrets vault and DevOps core, Devolutions RDM as the
      session management layer for on-prem/hybrid infrastructure, and MiniOrange as the identity and MFA front-door.
      Together, they close every gap left open by each individual vendor.
    </p>

    <div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:12px;margin-bottom:20px;">
      <div style="background:var(--bg-surface);border:1px solid var(--cyan);border-radius:8px;padding:14px;">
        <div style="font-size:0.62rem;font-family:var(--font-mono);color:var(--cyan);font-weight:700;margin-bottom:8px;letter-spacing:.04em;">KEEPER SECURITY — CORE VAULT</div>
        <ul style="margin:0;padding-left:14px;font-size:0.68rem;color:var(--text-standard);line-height:1.9;">
          <li>Privileged secrets vault (zero-knowledge)</li>
          <li>KSM — DevOps/NHI secrets (40+ integrations)</li>
          <li>KCM — Browser-based session recording</li>
          <li>Password rotation via Keeper Gateway</li>
          <li>JIT / just-in-time access provisioning</li>
          <li>FedRAMP High (March 2026)</li>
          <li>Cloud IAM integration (AWS/Azure/GCP)</li>
        </ul>
      </div>
      <div style="background:var(--bg-surface);border:1px solid var(--blue);border-radius:8px;padding:14px;">
        <div style="font-size:0.62rem;font-family:var(--font-mono);color:var(--blue);font-weight:700;margin-bottom:8px;letter-spacing:.04em;">DEVOLUTIONS RDM — SESSION LAYER</div>
        <ul style="margin:0;padding-left:14px;font-size:0.68rem;color:var(--text-standard);line-height:1.9;">
          <li>RDP / SSH / VNC / Telnet (100+ protocols)</li>
          <li>On-prem session recording &amp; playback</li>
          <li>Cisco IOS / NX-OS / ASA terminal sessions</li>
          <li>RDM Agent credential rotation</li>
          <li>Jump-host for air-gapped segments</li>
          <li>Credential pull from Keeper vault via API</li>
          <li>No Windows RDS licensing required</li>
        </ul>
      </div>
      <div style="background:var(--bg-surface);border:1px solid var(--purple);border-radius:8px;padding:14px;">
        <div style="font-size:0.62rem;font-family:var(--font-mono);color:var(--purple);font-weight:700;margin-bottom:8px;letter-spacing:.04em;">MINIORANGE — IDENTITY FRONT-DOOR</div>
        <ul style="margin:0;padding-left:14px;font-size:0.68rem;color:var(--text-standard);line-height:1.9;">
          <li>MFA enforcement (TOTP, Push, FIDO2)</li>
          <li>SSO / SAML / OIDC brokering</li>
          <li>Identity governance &amp; access review</li>
          <li>Step-up auth for high-risk vaults</li>
          <li>Cisco Duo / AD / LDAP integration</li>
          <li>Risk-based adaptive authentication</li>
          <li>Access request &amp; approval workflow</li>
        </ul>
      </div>
    </div>

    <div style="font-size:0.65rem;font-family:var(--font-mono);color:var(--text-muted);margin-bottom:8px;text-transform:uppercase;letter-spacing:.06em;">PAM Component Coverage Map</div>
    <div style="overflow-x:auto;margin-bottom:20px;">
      <table style="width:100%;border-collapse:collapse;font-size:0.66rem;">
        <thead>
          <tr style="border-bottom:1px solid var(--border);">
            <th style="padding:6px 10px;text-align:left;color:var(--text-muted);min-width:180px;">PAM Component</th>
            <th style="padding:6px 10px;color:var(--cyan);text-align:center;">Keeper</th>
            <th style="padding:6px 10px;color:var(--blue);text-align:center;">Devolutions</th>
            <th style="padding:6px 10px;color:var(--purple);text-align:center;">MiniOrange</th>
            <th style="padding:6px 10px;color:var(--green);text-align:center;">Covered?</th>
          </tr>
        </thead>
        <tbody>
          ${[
            ['Privileged Secrets Vault',         '✓ Primary',       '✓ Secondary',    '✗',                '✓ FULL'],
            ['Password Rotation',                 '✓ Gateway',       '✓ RDM Agent',    '⚠ Basic',          '✓ FULL'],
            ['Session Recording',                 '✓ KCM',           '✓ RDM',          '✗',                '✓ FULL'],
            ['RDP / SSH / VNC Access',            '⚠ KCM (browser)', '✓ Native RDM',   '✗',                '✓ FULL'],
            ['Cisco Network Device Access',       '⚠ Custom scripts','✓ Telnet/SSH/CLI','✗',                '✓ FULL'],
            ['DevOps / NHI Secrets (CI/CD)',      '✓ KSM 40+',       '⚠ REST only',    '✗',                '✓ FULL'],
            ['Cloud IAM (AWS/Azure/GCP)',          '✓ Native',        '⚠ Entry type',   '⚠ SSO only',       '✓ FULL'],
            ['MFA / Step-up Authentication',      '✓ Built-in',      '⚠ Basic',        '✓ Primary',        '✓ FULL'],
            ['SSO / Identity Brokering',          '⚠ Limited',       '✗',              '✓ SAML/OIDC',      '✓ FULL'],
            ['Just-in-Time Access (ZSP)',         '✓ KSM JIT',       '✗',              '✓ Approval flow',  '✓ FULL'],
            ['Compliance Audit Trail',            '✓ FedRAMP High',  '✓ RDM logs',     '✓ IAM audit',      '✓ FULL'],
            ['Database Credential Mgmt',          '✓ PAM Resources', '✓ DB entry type','⚠ Basic',          '✓ FULL'],
            ['Air-gapped / Jump-host Access',     '⚠ Gateway only',  '✓ Jump server',  '✗',                '✓ FULL'],
            ['Access Request / Approval',         '⚠ Basic',         '✗',              '✓ Workflow',       '✓ FULL'],
            ['Zero Standing Privilege',           '✓ KSM dynamic',   '✗',              '✓ Adaptive auth',  '✓ FULL'],
          ].map((row, i) => `
            <tr style="border-bottom:1px solid var(--border);${i % 2 === 1 ? 'background:var(--bg-surface);' : ''}">
              <td style="padding:5px 10px;font-weight:600;color:var(--text-bright)">${row[0]}</td>
              <td style="padding:5px 10px;text-align:center;color:var(--text-standard)">${row[1]}</td>
              <td style="padding:5px 10px;text-align:center;color:var(--text-standard)">${row[2]}</td>
              <td style="padding:5px 10px;text-align:center;color:var(--text-standard)">${row[3]}</td>
              <td style="padding:5px 10px;text-align:center;color:var(--green);font-weight:700;font-size:0.6rem;font-family:var(--font-mono);">${row[4]}</td>
            </tr>`).join('')}
        </tbody>
      </table>
    </div>

    <div style="font-size:0.65rem;font-family:var(--font-mono);color:var(--text-muted);margin-bottom:8px;text-transform:uppercase;letter-spacing:.06em;">Integration Architecture</div>
    <div class="callout" style="border-color:var(--green);background:var(--bg-surface);margin-bottom:10px;">
      <div class="callout-title" style="color:var(--green);font-size:0.65rem;">How the Three Layers Connect</div>
      <div style="display:grid;grid-template-columns:1fr 1fr;gap:12px;font-size:0.68rem;color:var(--text-standard);line-height:1.8;">
        <div>
          <strong style="color:var(--cyan)">MiniOrange → Keeper &amp; Devolutions</strong><br>
          MiniOrange acts as SAML/OIDC identity provider. Users authenticate via MiniOrange MFA before being granted a Keeper session token or Devolutions RDM session. Step-up MFA triggers for high-sensitivity vaults.
        </div>
        <div>
          <strong style="color:var(--blue)">Devolutions RDM → Keeper Vault</strong><br>
          Devolutions RDM entries pull credentials directly from Keeper via KSM API integration. Passwords are never stored in RDM — retrieved just-in-time at session launch and zero-standing-privilege enforced.
        </div>
        <div>
          <strong style="color:var(--cyan)">Keeper KSM → CI/CD &amp; Cloud</strong><br>
          GitHub Actions, Terraform, Ansible, and Kubernetes pull secrets from KSM. Cisco network automation scripts (Ansible for IOS/NX-OS) consume Keeper-managed credentials via native KSM SDK — no plaintext in pipelines.
        </div>
        <div>
          <strong style="color:var(--purple)">MiniOrange → Access Governance</strong><br>
          Periodic access reviews and certification campaigns run through MiniOrange IAM. Orphaned accounts flagged for Keeper vault cleanup. Risk-based policies trigger automatic vault lock for anomalous access patterns.
        </div>
      </div>
    </div>

    <div class="callout amber" style="margin-top:10px;">
      <div class="callout-title" style="color:var(--amber);font-size:0.65rem;">&#x26A0; Deployment Phasing Recommendation</div>
      <p style="font-size:0.68rem;line-height:1.8;margin:0;">
        <strong>Phase 1 (Weeks 1–36):</strong> Deploy Keeper as primary vault — migrate all CyberArk accounts, rotate credentials, stand up KSM for DevOps pipelines.<br>
        <strong>Phase 2 (Weeks 20–44):</strong> Layer Devolutions RDM — import Keeper-managed credentials into RDM entries for on-prem session management. Retire CyberArk PSM.<br>
        <strong>Phase 3 (Weeks 30–44):</strong> Deploy MiniOrange — configure SAML federation to both Keeper and Devolutions, enforce adaptive MFA, enable access review workflows.
      </p>
    </div>
  `) +

  _guideSection('&#x1F680; Taking This Live — Pre-Production Checklist', `
    <p style="margin-bottom:14px;font-size:0.72rem;color:var(--text-standard);line-height:1.7;">
      This demo runs entirely on mock data. The 15-agent orchestration code is production-grade Python, but the
      control center UI is wired to a mock API layer. The items below are what convert this demo into a live
      migration platform. They are sequenced by dependency — <strong>you cannot skip ahead</strong>.
      The full checklist also appears in the <strong>Comparison tab → "What's Needed for Production"</strong> panel.
    </p>

    <div class="callout" style="border-color:var(--red);background:var(--bg-surface);margin-bottom:16px;">
      <div class="callout-title" style="color:var(--red);font-size:0.65rem;">&#x1F6A7; Hard Gate — Must Be True Before Migration Starts</div>
      <div style="display:grid;grid-template-columns:1fr 1fr;gap:14px;font-size:0.68rem;color:var(--text-standard);line-height:1.8;margin-top:6px;">
        <div>
          <strong style="color:var(--cyan)">1. Keeper Gateway deployed</strong><br>
          Docker container (4 CPU / 16 GB) running in a network segment with line-of-sight to all managed systems
          (Windows DCs, Unix hosts, Oracle/MSSQL servers, Cisco IOS devices). Without Gateway, rotation and heartbeat
          calls never reach targets — migration appears to succeed but credentials are unverified.
          At Cisco 250K+ scale: minimum 2-node HA cluster behind a load balancer.
        </div>
        <div>
          <strong style="color:var(--cyan)">2. CyberArk PVWA service account credentialed</strong><br>
          A dedicated migration service account in CyberArk with Safe Member rights across all source safes.
          Credentials set as environment variables (<code style="color:var(--green)">CYBERARK_USERNAME</code> /
          <code style="color:var(--green)">CYBERARK_PASSWORD</code>). The PVWA endpoint must be reachable from
          the orchestration host. This is the source — Agent 01 and 04 fail without it.
        </div>
        <div>
          <strong style="color:var(--cyan)">3. Keeper PAM OAuth2 credentials issued</strong><br>
          Client ID + Secret from the Keeper Admin Console
          (<code style="color:var(--green)">KEEPER_CLIENT_ID</code> /
          <code style="color:var(--green)">KEEPER_CLIENT_SECRET</code>).
          The PAM Config (top of the 3-tier hierarchy) must be created before any accounts can be imported.
          Without this, Agent 04 ETL has no target to write to.
        </div>
        <div>
          <strong style="color:var(--cyan)">4. <code>keeper-secrets-manager-core</code> installed</strong><br>
          Add to <code style="color:var(--green)">requirements.txt</code> in the orchestration environment.
          Required for KSM DevOps secrets distribution (CI/CD pipeline credential handoff). The vault migration
          itself (Agent 04) uses the Keeper PAM REST API directly — KSM SDK is specifically needed for the
          NHI/DevOps secrets phase (P5 onward).
        </div>
      </div>
    </div>

    <div style="font-size:0.65rem;font-family:var(--font-mono);color:var(--text-muted);margin-bottom:8px;text-transform:uppercase;letter-spacing:.06em;">Full Production Readiness — Sequenced by Dependency</div>
    <div style="overflow-x:auto;margin-bottom:16px;">
      <table style="width:100%;border-collapse:collapse;font-size:0.66rem;">
        <thead>
          <tr style="border-bottom:1px solid var(--border);">
            <th style="padding:6px 10px;text-align:left;color:var(--text-muted);width:28px;">#</th>
            <th style="padding:6px 10px;text-align:left;color:var(--text-muted);">Item</th>
            <th style="padding:6px 10px;text-align:left;color:var(--text-muted);">Why it matters</th>
            <th style="padding:6px 10px;text-align:left;color:var(--text-muted);width:80px;">Needed by</th>
          </tr>
        </thead>
        <tbody>
          ${[
            ['1',  'Wire API stubs → real coordinator.py agent calls',       'The demo backend returns mock JSON. Production wires each API route to the actual agent method — Agent 01 for discovery, 04 for ETL, 05 for heartbeat, etc.', 'P1'],
            ['2',  'CyberArk PVWA REST API (Agents 11, 01, 04)',              'Source system connectivity. All discovery, account export, and freeze/unfreeze operations hit the live PVWA endpoint. Env vars + network access required.', 'P1'],
            ['3',  'Devolutions Server REST API (Agents 04, 05, 10)',         'Target vault for Option A. Agent 04 ETL creates Vault entries; Agent 05 heartbeat verifies; Agent 10 staging validates before production waves.', 'P2'],
            ['4',  'Keeper Gateway + PAM API (rotation, heartbeat, KSM)',     'Target for Option B. Gateway must be running for rotation and heartbeat. KSM SDK handles DevOps secrets. Hard gate — see above.', 'P1'],
            ['5',  'OAuth2/OIDC provider integration (enterprise IdP)',        'Enterprise SSO into the control center UI. MiniOrange or Cisco\'s existing IdP issues tokens. Without this, the UI has no authentication layer.', 'Pre-P1'],
            ['6',  'Database persistence (PostgreSQL for state)',             'Migration state currently held in JSON files. PostgreSQL enables multi-node orchestration, crash recovery without file locks, and audit log queries at scale.', 'P1'],
            ['7',  'WebSocket support for real-time agent status',            'The UI polls the API today. WebSockets push live agent heartbeat, ETL progress, and gate status to the dashboard without polling lag.', 'P3'],
            ['8',  'Production TLS / certificate management',                 'PVWA, Keeper, and Devolutions Server all enforce HTTPS. The orchestration host needs valid certs and the CA chain for all three endpoints trusted.', 'Pre-P1'],
            ['9',  'CI/CD pipeline (GitHub Actions or Jenkins)',              'Automates orchestrator deployment, config validation, and regression tests on each commit. Prevents broken agent code reaching the migration environment.', 'Pre-P1'],
            ['10', 'Load testing with 20K+ accounts',                        'Validates ETL batch sizing, Keeper Gateway throughput, and API rate-limit handling (Keeper HTTP 403 throttle) before running production waves.', 'Pre-P5'],
            ['11', 'Security audit and penetration testing',                  'The orchestrator handles live privileged credentials in memory. Pentest validates secret zeroing, state file permissions, TLS config, and API auth posture.', 'Pre-P5'],
            ['12', 'Dual-backend parallel mode (P6 traffic shifting)',        'Phase 6 runs source and target simultaneously. The control center needs to display both systems live, shift traffic percentages, and trigger rollback on anomaly.', 'P6'],
          ].map((row, i) => `
            <tr style="border-bottom:1px solid var(--border);${i % 2 === 1 ? 'background:var(--bg-surface);' : ''}">
              <td style="padding:5px 10px;font-family:var(--font-mono);color:var(--text-muted);font-size:0.6rem;">${row[0]}</td>
              <td style="padding:5px 10px;font-weight:600;color:var(--text-bright)">${row[1]}</td>
              <td style="padding:5px 10px;color:var(--text-standard);line-height:1.6;">${row[2]}</td>
              <td style="padding:5px 10px;font-family:var(--font-mono);font-size:0.6rem;color:var(--amber);font-weight:700;">${row[3]}</td>
            </tr>`).join('')}
        </tbody>
      </table>
    </div>

    <div class="callout teal" style="margin-top:4px;">
      <div class="callout-title" style="color:var(--cyan);font-size:0.65rem;">Minimum Viable Start — What You Need on Day 1</div>
      <p style="font-size:0.68rem;line-height:1.8;margin:0;">
        Items <strong>#1–4 + #8</strong> are sufficient to run Phase 1 (discovery and gap analysis) against a live CyberArk environment.
        No accounts are moved in P1 — it is read-only. This means you can validate connectivity, agent output, and permission mapping
        reports against real data before any migration risk is taken. Items #5–12 are required before production waves (P5) begin.
        The Keeper Gateway (<strong>#4</strong>) is the longest-lead infrastructure item — provision it first.
      </p>
    </div>
  `) +

  _guideSection('&#x2699;&#xFE0F; Migration Platform CI/CD — Tool Decision &amp; Testing Standard', `
    <p style="margin-bottom:14px;font-size:0.72rem;color:var(--text-standard);line-height:1.7;">
      The migration orchestrators (coordinator.py + 15 agents) are production-grade software that modifies live privileged
      accounts. They require the same CI/CD discipline as any critical infrastructure code — automated testing on every
      commit, config validation before deployment, and a promotion gate before any changes reach the migration environment.
      <br><br>
      <strong>The CI/CD tooling is a decision point</strong> — Cisco will likely have an existing standard (GitHub Enterprise,
      Jenkins, GitLab CI, or Azure DevOps). The tool choice does not change the pipeline stages or testing requirements.
      What follows is tool-agnostic: the procedure is the standard regardless of platform.
    </p>

    <div style="font-size:0.65rem;font-family:var(--font-mono);color:var(--text-muted);margin-bottom:8px;text-transform:uppercase;letter-spacing:.06em;">Tool Decision Matrix — Pick One</div>
    <div style="overflow-x:auto;margin-bottom:20px;">
      <table style="width:100%;border-collapse:collapse;font-size:0.66rem;">
        <thead>
          <tr style="border-bottom:1px solid var(--border);">
            <th style="padding:6px 10px;text-align:left;color:var(--text-muted);">Platform</th>
            <th style="padding:6px 10px;text-align:left;color:var(--text-muted);">Best fit when…</th>
            <th style="padding:6px 10px;text-align:left;color:var(--text-muted);">Key consideration</th>
            <th style="padding:6px 10px;text-align:center;color:var(--text-muted);">Secret mgmt</th>
          </tr>
        </thead>
        <tbody>
          ${[
            ['GitHub Actions',   'Code repo is on GitHub Enterprise',                        'Runners must be self-hosted in Cisco network to reach PVWA + Keeper Gateway. No public runner can touch migration env.', 'KSM native action'],
            ['Jenkins',          'Cisco already runs Jenkins for infrastructure automation',  'Existing pipeline library, agent pools, and LDAP auth reuse. Most common in enterprise PAM environments.', 'Keeper plugin or env vars'],
            ['GitLab CI',        'Code repo is on GitLab (self-hosted)',                     'Built-in container registry and environments model maps cleanly to migration phases. Good secrets masking.', 'GitLab Vault integration'],
            ['Azure DevOps',     'Cisco Microsoft shop — AzDO already managing infra',       'Service connections to Keeper and Devolutions. YAML pipelines with environment approvals match phase gates.', 'Azure Key Vault link'],
          ].map((row, i) => `
            <tr style="border-bottom:1px solid var(--border);${i % 2 === 1 ? 'background:var(--bg-surface);' : ''}">
              <td style="padding:5px 10px;font-weight:700;color:var(--cyan)">${row[0]}</td>
              <td style="padding:5px 10px;color:var(--text-standard)">${row[1]}</td>
              <td style="padding:5px 10px;color:var(--text-standard);line-height:1.6;">${row[2]}</td>
              <td style="padding:5px 10px;text-align:center;color:var(--text-muted)">${row[3]}</td>
            </tr>`).join('')}
        </tbody>
      </table>
    </div>

    <div class="callout amber" style="margin-bottom:16px;">
      <div class="callout-title" style="color:var(--amber);font-size:0.65rem;">&#x26A0; Non-Negotiable Regardless of Tool</div>
      <p style="font-size:0.68rem;line-height:1.8;margin:0;">
        CI/CD runners <strong>must run inside Cisco's network</strong> — they need reachable paths to the CyberArk PVWA (source),
        Keeper Gateway (target), and Devolutions Server (target). Public cloud runners cannot be used for any stage
        that touches migration infrastructure. Credentials must <strong>never appear in pipeline logs</strong> — all
        secrets injected via the chosen platform's secret store, not hardcoded in YAML.
      </p>
    </div>

    <div style="font-size:0.65rem;font-family:var(--font-mono);color:var(--text-muted);margin-bottom:8px;text-transform:uppercase;letter-spacing:.06em;">Standard Pipeline Stages — Consistent Across All Tools</div>
    <div style="display:grid;gap:8px;margin-bottom:20px;">
      ${[
        ['1', 'LINT &amp; STATIC ANALYSIS', 'var(--blue)',
         'Run <code>flake8</code> / <code>ruff</code> on all agent code. Run <code>bandit</code> for security anti-patterns (hardcoded secrets, subprocess injection, insecure deserialization). Fail on any HIGH severity finding. Takes ~30s — runs on every commit including PRs.',
         'Every commit'],
        ['2', 'SECRET SCAN', 'var(--red)',
         'Scan repo history and staged files with <code>trufflehog</code> or <code>detect-secrets</code>. Flag any credential pattern (API key, password, token, private key). Pipeline hard-fails — commit cannot merge until finding is remediated. Prevents credentials from ever entering version history.',
         'Every commit'],
        ['3', 'UNIT TESTS', 'var(--cyan)',
         'pytest suite for each agent — mock all external API calls (PVWA, Keeper, Devolutions). Test: ETL transform logic, permission mapping rules (22→Vault roles, 22→4 axes), NHI classification signals, state machine transitions, error sanitization (no secrets in exception messages), watchdog timer logic.',
         'Every commit'],
        ['4', 'CONFIG VALIDATION', 'var(--amber)',
         'Schema-validate <code>config.json</code> and <code>agent_config.json</code> against their JSON Schema definitions. Verify all required fields present, URL formats valid, timeout values in safe ranges. Run <code>python3 cli.py preflight --dry-run</code> against the staging config. Catches malformed configs before deployment — a bad config during live migration can freeze accounts.',
         'Every commit'],
        ['5', 'INTEGRATION TESTS', 'var(--green)',
         'Deploy a mock API server (Flask emulating PVWA + Keeper PAM + Devolutions REST) in the runner environment. Run a full P1 discovery sequence and a 10-account ETL pipeline against mock endpoints. Validates actual HTTP request/response handling, retry logic, circuit breaker behavior, and state file writes. Slower (~5 min) — runs on merge to main only.',
         'Merge to main'],
        ['6', 'DEPLOYMENT TO STAGING', 'var(--purple)',
         'Package orchestrator code, copy to staging host, install dependencies, run <code>cli.py preflight</code> against real staging endpoints (CyberArk dev/lab + Keeper test tenant + Devolutions test instance). A passing preflight confirms connectivity, auth, and config are all healthy before any migration code runs.',
         'Merge to main'],
        ['7', 'PROMOTION GATE — HUMAN APPROVAL', 'var(--amber)',
         'Before any deployment reaches the production migration environment, a named approver (Migration Lead or Security Architect) manually reviews the change and approves in the CI/CD platform. This mirrors the Agent 08 runbook gate model — the pipeline enforces it mechanically. No code reaches the live migration environment without a human sign-off.',
         'Pre-P1 deploy'],
        ['8', 'LOAD &amp; THROUGHPUT TEST', 'var(--cyan)',
         'Seed mock API with 20,000+ account records. Run ETL pipeline and measure: batch throughput (accounts/min), Keeper Gateway API call rate (must stay under 50 calls/min per vault ceiling), state file write performance, and memory footprint under sustained load. Run before each production wave (P5). Catches Keeper HTTP 403 throttle scenarios and Gateway OOM risk at Cisco scale.',
         'Pre-P5 waves'],
        ['9', 'ROLLBACK TEST', 'var(--red)',
         'Inject a simulated mid-pipeline failure (kill coordinator process at step 4 of 7). Verify: watchdog timer fires within 120 min, all frozen accounts are unfrozen, state file is recoverable, coordinator resumes correctly from last checkpoint on restart. Must pass before production waves. This is the safety net — validate it works before you need it.',
         'Pre-P5 waves'],
      ].map(([num, label, color, desc, when]) => `
        <div style="display:grid;grid-template-columns:28px 180px 1fr 80px;gap:10px;align-items:start;padding:10px 12px;background:var(--bg-surface);border:1px solid var(--border);border-left:3px solid ${color};border-radius:4px;">
          <div style="font-family:var(--font-mono);font-size:0.65rem;color:var(--text-muted);font-weight:700;padding-top:1px;">${num}</div>
          <div style="font-family:var(--font-mono);font-size:0.6rem;color:${color};font-weight:700;padding-top:2px;line-height:1.4;">${label}</div>
          <div style="font-size:0.67rem;color:var(--text-standard);line-height:1.7;">${desc}</div>
          <div style="font-size:0.58rem;font-family:var(--font-mono);color:var(--text-muted);text-align:right;padding-top:2px;">${when}</div>
        </div>
      `).join('')}
    </div>

    <div style="font-size:0.65rem;font-family:var(--font-mono);color:var(--text-muted);margin-bottom:8px;text-transform:uppercase;letter-spacing:.06em;">Environment Promotion Model</div>
    <div style="display:grid;grid-template-columns:repeat(4,1fr);gap:8px;margin-bottom:16px;font-size:0.65rem;text-align:center;">
      ${[
        ['DEV', 'var(--blue)', 'Local dev machine or feature branch. Stages 1–4 only. Mock APIs throughout.'],
        ['STAGING', 'var(--amber)', 'Shared staging host. Stages 1–6. Real CyberArk dev/lab + Keeper test tenant.'],
        ['MIGRATION ENV', 'var(--red)', 'Live migration server. Stage 7 human gate required. All stages must be green.'],
        ['PRODUCTION WAVES', 'var(--green)', 'P5 waves. Stages 8–9 load + rollback tests must pass first.'],
      ].map(([env, color, desc]) => `
        <div style="background:var(--bg-surface);border:1px solid ${color};border-radius:6px;padding:12px 8px;">
          <div style="font-family:var(--font-mono);font-weight:700;color:${color};margin-bottom:6px;">${env}</div>
          <div style="color:var(--text-muted);line-height:1.6;">${desc}</div>
        </div>
      `).join('')}
    </div>

    <div class="callout" style="border-color:var(--green);background:var(--bg-surface);">
      <div class="callout-title" style="color:var(--green);font-size:0.65rem;">What Stays the Same Regardless of CI/CD Tool</div>
      <div style="display:grid;grid-template-columns:1fr 1fr;gap:10px;font-size:0.68rem;color:var(--text-standard);line-height:1.8;margin-top:6px;">
        <div>
          <strong>The 9 pipeline stages</strong> — lint, secret scan, unit tests, config validation, integration tests,
          staging deploy, human approval gate, load test, rollback test. Every tool can implement these. The stage
          order and pass/fail criteria are fixed.
        </div>
        <div>
          <strong>The test coverage targets</strong> — unit tests cover all agent logic; integration tests cover full
          P1 discovery + 10-account ETL; load test covers 20K+ accounts. These thresholds apply regardless of whether
          the runner is a GitHub Action, a Jenkins agent, or a GitLab runner.
        </div>
        <div>
          <strong>The secret handling rules</strong> — credentials injected at runtime from the chosen secret store,
          never in YAML or code, never in logs. Trufflehog/detect-secrets runs on every commit. This is non-negotiable
          for a system handling live privileged credentials.
        </div>
        <div>
          <strong>The human promotion gate</strong> — no code reaches the migration environment without a named
          approver. This mirrors the Agent 08 phase gate model and provides the same audit trail. The CI/CD platform
          records who approved, when, and what SHA was deployed.
        </div>
      </div>
    </div>
  `) +

  _guideSection('Glossary', `
    <div style="columns:2;column-gap:20px;font-size:0.65rem;">
      ${[
        ['NHI', 'Non-Human Identity — service accounts, API keys, SSH keys, certificates used by applications'],
        ['CPM', 'Central Policy Manager — CyberArk component that rotates passwords on schedule'],
        ['RDM Agent', 'Devolutions Remote Desktop Manager rotation agent — equivalent of CyberArk CPM'],
        ['KSM', 'Keeper Secrets Manager — DevOps secrets distribution, replaces CCP/AAM'],
        ['KCM', 'Keeper Connection Manager — session recording platform (Apache Guacamole), replaces PSM'],
        ['Gateway', 'Keeper Gateway Docker container — handles rotation + session proxy for Keeper'],
        ['PVWA', 'Password Vault Web Access — CyberArk web management interface'],
        ['Safe', 'CyberArk container for privileged accounts with access controls'],
        ['Vault', 'Devolutions Server container equivalent to CyberArk Safe'],
        ['pamUser', 'Keeper credential record — linked to pamMachine or pamDatabase in 3-tier hierarchy'],
        ['pamMachine', 'Keeper resource record for servers/endpoints in PAM hierarchy'],
        ['Resource Group', 'MiniOrange container equivalent to CyberArk Safe'],
        ['Platform', 'CyberArk definition of how to manage a specific system type'],
        ['ETL', 'Extract-Transform-Load — the core migration pipeline pattern'],
        ['MCP', 'Model Context Protocol — standard for AI model tool integration'],
        ['CCP', 'Central Credential Provider — CyberArk passwordless application auth'],
        ['AAM', 'Application Access Manager — CyberArk enterprise app integration'],
        ['PSM', 'Privileged Session Manager — CyberArk session recording/proxy'],
        ['PAM Config', 'Keeper top-level container that groups PAM resources for a given system/environment'],
        ['Gate', 'Human approval checkpoint required before phase advancement'],
        ['Yellow Checkpoint', 'AI-detected condition requiring contextual evaluation'],
        ['Heartbeat', 'Automated check that a migrated account can still authenticate'],
        ['Watchdog', 'Timer that auto-unfreezes accounts if ETL pipeline stalls'],
        ['SIEM', 'Security Information & Event Management — log aggregation target'],
        ['SOX', 'Sarbanes-Oxley Act — financial controls compliance framework'],
      ].map(([term, def]) => `
        <div style="margin-bottom:8px;break-inside:avoid;">
          <span style="font-weight:700;color:var(--cyan);font-family:var(--font-mono);">${term}</span>
          <span style="color:var(--text-standard);"> — ${def}</span>
        </div>
      `).join('')}
    </div>
  `);
}

function _guideSection(title, content) {
  return `
    <details class="panel" style="margin-bottom:12px;cursor:pointer;" open>
      <summary class="panel-header" style="user-select:none;list-style:none;">
        <div class="panel-title">${title}</div>
        <span style="font-size:0.6rem;color:var(--text-muted);font-family:var(--font-mono);">CLICK TO TOGGLE</span>
      </summary>
      <div class="panel-body" style="padding:14px 16px;font-size:0.72rem;color:var(--text-standard);line-height:1.7;">
        ${content}
      </div>
    </details>`;
}

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
    <p><strong>Executive summary:</strong> The SHIFT Migration Control Center is a real-time operational dashboard for managing a large-scale Privileged Access Management migration. It provides visibility into every phase, agent, gate, and risk factor across an 80-week (Option A) or 50-week (Option B) migration timeline.</p>
    <p><strong>Technical overview:</strong> The frontend is a single-page app (Vanilla JS, no frameworks) served by a FastAPI backend. All data flows through the 15-agent AI orchestrator. Each page visualizes a different slice of the orchestrator's output — from high-level phase timelines down to individual account-level ETL results. The two MCP servers (pam-migration-mcp and SHIFT Portal) provide Model Context Protocol integration for AI-assisted operations.</p>
    <p>This control center is a <strong>demonstration/proposal tool</strong> — it uses mock data to show how the migration would be managed. In production, the backend connects to live CyberArk PVWA and target platform APIs.</p>
  `) +

  _guideSection('SHIFT Architecture — Framework-Agnostic Design', `
    <p style="margin-bottom:14px;">SHIFT is a <strong>methodology, tooling, and agent design pattern</strong> — not an SDK. The underlying orchestration engine is swappable. This makes SHIFT portable and platform-independent.</p>

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
        <div class="shift-arch-desc">PAM APIs (CyberArk, Delinea, StrongDM) &middot; MCP Servers &middot; State Store &middot; Audit Logger</div>
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
          <th style="padding:6px 8px;">Option A: Delinea (Secret Server)</th>
          <th style="padding:6px 8px;">Option B: CyberArk Cloud (Privilege Cloud)</th>
        </tr>
      </thead>
      <tbody>
        ${[
          ['Timeline', '80 weeks', '50 weeks'],
          ['Permission Model', '22 &rarr; 4 roles (LOSSY — escalation risk)', '22 &rarr; 22 (1:1 mapping)'],
          ['Data Structure', 'Safe &rarr; Folder (hierarchical)', 'Safe &rarr; Safe (identical)'],
          ['Platforms', 'Platform &rarr; Secret Template', 'Platform &rarr; Platform'],
          ['API Surface', 'Completely different (/api/v1/)', 'Same (/PasswordVault/api/)'],
          ['Audit Logs', 'Do NOT transfer', 'Can migrate'],
          ['PSM Recordings', 'Cannot migrate', 'Can migrate'],
          ['Integration Rework', 'Full re-architecture (CCP/AAM &rarr; OAuth2)', 'Similar patterns'],
          ['CPM/RPC', 'RPC plugins must be rebuilt per template', 'CPM plugins carry over'],
          ['Risk Level', 'Higher — permission loss, audit discontinuity', 'Lower — same vendor ecosystem'],
        ].map(r => `
          <tr style="border-bottom:1px solid var(--border-light);">
            <td style="padding:5px 8px;font-weight:600;color:var(--text-bright);">${r[0]}</td>
            <td style="padding:5px 8px;color:var(--blue);">${r[1]}</td>
            <td style="padding:5px 8px;color:var(--green);">${r[2]}</td>
          </tr>
        `).join('')}
      </tbody>
    </table>
    <p style="margin-top:10px;font-size:0.62rem;color:var(--text-muted);">Toggle between Option A and Option B using the sidebar switch. All pages update to show the appropriate data, checkpoints, predictions, and timelines for each option.</p>
  `) +

  _guideSection('Vendor Team\'s RoM for Migration to Delinea', `
    <p style="margin-bottom:12px;">The vendor SI (System Integration) team provided the following <strong>Rough Order of Magnitude (RoM)</strong> estimate for migrating to Delinea Secret Server. This represents the vendor's projected effort across 6 workstreams spanning 45 sprints.</p>
    <table style="width:100%;border-collapse:collapse;font-size:0.65rem;">
      <thead>
        <tr style="border-bottom:2px solid var(--border);color:var(--text-muted);text-align:left;">
          <th style="padding:6px 8px;">#</th>
          <th style="padding:6px 8px;">SI Task</th>
          <th style="padding:6px 8px;">RoM (p.hours)</th>
          <th style="padding:6px 8px;">Sprints</th>
          <th style="padding:6px 8px;">Sprint Range</th>
        </tr>
      </thead>
      <tbody>
        ${[
          ['1', 'Review POV, Discovery, Traceability Matrix', '250', '5', 'Sprint 1-5'],
          ['2', 'Digital Engineering & Experience Workstream', '1,000', '10', 'Sprint 3-13'],
          ['3', 'Agentification Workstream', '1,000', '10', 'Sprint 5-15'],
          ['4', 'Testing / QA Workstream', '3,000', 'Throughout', 'Sprint 3-40'],
          ['5', 'Wave Planning and Rollout Workstream', '4,800', '22', 'Sprint 8-40'],
          ['6', 'Legacy Retirement Workstream', '2,000', '20', 'Sprint 25-45'],
        ].map(r => `
          <tr style="border-bottom:1px solid var(--border-light);">
            <td style="padding:5px 8px;font-weight:700;color:var(--cyan);font-family:var(--font-mono);">${r[0]}</td>
            <td style="padding:5px 8px;color:var(--text-bright);">${r[1]}</td>
            <td style="padding:5px 8px;color:var(--amber);font-family:var(--font-mono);font-weight:600;">${r[2]}</td>
            <td style="padding:5px 8px;color:var(--text-muted);">${r[3]}</td>
            <td style="padding:5px 8px;color:var(--teal);font-family:var(--font-mono);">${r[4]}</td>
          </tr>
        `).join('')}
        <tr style="border-top:2px solid var(--border);font-weight:700;">
          <td style="padding:6px 8px;"></td>
          <td style="padding:6px 8px;color:var(--text-bright);">Total Effort</td>
          <td style="padding:6px 8px;color:var(--red);font-family:var(--font-mono);font-size:0.75rem;">12,050</td>
          <td colspan="2" style="padding:6px 8px;color:var(--text-muted);">45 sprints</td>
        </tr>
      </tbody>
    </table>
    <div class="callout amber" style="margin-top:14px;font-size:0.68rem;line-height:1.6;">
      <div class="callout-title" style="font-size:0.72rem;">Key Observations</div>
      <ul style="margin:0;padding-left:18px;line-height:2;">
        <li><strong>Testing/QA</strong> is the largest workstream at 3,000 hours, running nearly the entire project (Sprint 3-40)</li>
        <li><strong>Wave Planning and Rollout</strong> consumes 4,800 hours — the most resource-intensive phase of the migration</li>
        <li><strong>Agentification</strong> (1,000 hours) covers the AI-driven automation buildout for the migration tooling</li>
        <li><strong>Legacy Retirement</strong> (2,000 hours) begins at Sprint 25 and extends to Sprint 45, covering decommission and cutover</li>
        <li>Total effort of <strong>12,050 person-hours</strong> across 45 sprints reflects the scale and complexity of a cross-vendor PAM migration</li>
      </ul>
    </div>
  `) +

  _guideSection('Glossary', `
    <div style="columns:2;column-gap:20px;font-size:0.65rem;">
      ${[
        ['NHI', 'Non-Human Identity — service accounts, API keys, SSH keys, certificates used by applications'],
        ['CPM', 'Central Policy Manager — CyberArk component that rotates passwords on schedule'],
        ['RPC', 'Remote Password Changing — Secret Server equivalent of CPM'],
        ['PVWA', 'Password Vault Web Access — CyberArk web management interface'],
        ['Safe', 'CyberArk container for privileged accounts with access controls'],
        ['Folder', 'Secret Server container equivalent to CyberArk Safe'],
        ['Template', 'Secret Server schema defining fields for a credential type'],
        ['Platform', 'CyberArk definition of how to manage a specific system type'],
        ['ETL', 'Extract-Transform-Load — the core migration pipeline pattern'],
        ['MCP', 'Model Context Protocol — standard for AI model tool integration'],
        ['CCP', 'Central Credential Provider — CyberArk passwordless application auth'],
        ['AAM', 'Application Access Manager — CyberArk enterprise app integration'],
        ['PSM', 'Privileged Session Manager — CyberArk session recording/proxy'],
        ['StrongDM', 'Infrastructure access platform often paired with Secret Server'],
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

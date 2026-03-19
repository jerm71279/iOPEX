/**
 * Lab Showcase — interactive PAM capability demonstrations.
 * All simulations run client-side; no backend required.
 */

// ── JIT Session simulation state ─────────────────────────
let _jit = {
  sessionId: null, accountName: null,
  maskedSecret: null, timer: null, elapsed: 0
};

let _labTab = 'jit';
let _connView = 'category';
let _oracleStep = 0;

// ── Oracle DB Workflow data ───────────────────────────────
const ORACLE_STEPS = [
  {
    title: 'Request Initiated',
    connector: null,
    stageHtml: `
      <div style="...">
        <div style="font-size:0.6rem;font-family:var(--font-mono);color:var(--text-muted);letter-spacing:1.5px;margin-bottom:8px;">ACCESS REQUEST</div>
        <div style="font-size:1rem;font-weight:700;color:var(--text-bright);margin-bottom:14px;">Oracle DB — ORCL-PROD @ db-server-01</div>
        <div style="display:grid;grid-template-columns:1fr 1fr;gap:10px;font-size:0.72rem;">
          <div><span style="color:var(--text-muted);font-family:var(--font-mono);">REQUESTOR</span><br><span style="color:var(--text-bright);font-weight:600;">dba-admin</span></div>
          <div><span style="color:var(--text-muted);font-family:var(--font-mono);">TARGET PLATFORM</span><br><span style="color:var(--cyan);font-family:var(--font-mono);">OracleDB</span></div>
          <div><span style="color:var(--text-muted);font-family:var(--font-mono);">ACCOUNT</span><br><span style="color:var(--text-bright);font-family:var(--font-mono);">sys @ ORCL-PROD</span></div>
          <div><span style="color:var(--text-muted);font-family:var(--font-mono);">STATUS</span><br><span style="color:var(--amber);">&#x23F3; Pending Verification</span></div>
        </div>
        <div style="margin-top:12px;font-size:0.68rem;color:var(--text-muted);">Justification: Emergency DBA access — DB performance incident</div>
      </div>`
  },
  {
    title: 'Identity Verified',
    connector: 'IDP Connector',
    stageHtml: `
      <div>
        <div style="display:flex;align-items:center;gap:10px;margin-bottom:14px;">
          <span style="color:var(--green);font-size:1.2rem;">&#x2714;</span>
          <div>
            <div style="font-size:0.6rem;font-family:var(--font-mono);color:var(--text-muted);">PRIMARY ID</div>
            <div style="font-family:var(--font-mono);font-size:0.82rem;color:var(--text-bright);">j.smith@corp.com</div>
          </div>
          <span class="badge badge-green" style="margin-left:auto;">VERIFIED</span>
        </div>
        <div style="display:flex;align-items:center;gap:10px;">
          <span style="color:var(--blue);font-size:1.2rem;">&#x1F511;</span>
          <div>
            <div style="font-size:0.6rem;font-family:var(--font-mono);color:var(--text-muted);">SECONDARY ID (VAULT)</div>
            <div style="font-family:var(--font-mono);font-size:0.82rem;color:var(--text-bright);">j.smith-priv</div>
          </div>
          <span class="badge badge-green" style="margin-left:auto;">LOCATED</span>
        </div>
        <div style="margin-top:14px;font-size:0.68rem;color:var(--text-muted);">AD group membership confirmed. Vault account j.smith-priv has access to DB-Production safe.</div>
      </div>`
  },
  {
    title: 'Workflow Approval',
    connector: 'Workflow Engine',
    stageHtml: `
      <div>
        <div style="font-size:0.6rem;font-family:var(--font-mono);color:var(--text-muted);letter-spacing:1.5px;margin-bottom:10px;">DUAL-CONTROL APPROVAL CHAIN</div>
        <div style="display:flex;flex-direction:column;gap:8px;">
          <div style="display:flex;align-items:center;justify-content:space-between;padding:8px 12px;background:var(--bg-surface);border:1px solid var(--green);border-radius:6px;">
            <div><span style="font-size:0.72rem;font-weight:600;color:var(--text-bright);">DBA Lead</span><br><span style="font-size:0.6rem;color:var(--text-muted);">maria.chen@corp.com</span></div>
            <span class="badge badge-green">&#x2714; APPROVED</span>
          </div>
          <div style="display:flex;align-items:center;justify-content:space-between;padding:8px 12px;background:var(--bg-surface);border:1px solid var(--green);border-radius:6px;">
            <div><span style="font-size:0.72rem;font-weight:600;color:var(--text-bright);">Security Ops</span><br><span style="font-size:0.6rem;color:var(--text-muted);">secops@corp.com</span></div>
            <span class="badge badge-green">&#x2714; APPROVED</span>
          </div>
        </div>
        <div style="margin-top:12px;display:flex;justify-content:space-between;font-size:0.68rem;">
          <span style="color:var(--text-muted);">TTL WINDOW</span>
          <span style="font-family:var(--font-mono);color:var(--amber);">60 minutes</span>
        </div>
      </div>`
  },
  {
    title: 'Credential Retrieved',
    connector: 'CPM / CCP Connector',
    stageHtml: `
      <div>
        <div style="font-size:0.6rem;font-family:var(--font-mono);color:var(--text-muted);letter-spacing:1.5px;margin-bottom:8px;">VAULT API CALL</div>
        <div style="background:var(--bg-page);border:1px solid var(--border);border-radius:4px;padding:10px;font-family:var(--font-mono);font-size:0.68rem;color:var(--cyan);margin-bottom:12px;">
          POST /PasswordVault/api/Accounts/{id}/Password/Retrieve<br>
          Platform: <span style="color:var(--green);">OracleDB</span><br>
          Account: <span style="color:var(--text-bright);">sys @ ORCL-PROD</span>
        </div>
        <div style="font-size:0.6rem;font-family:var(--font-mono);color:var(--text-muted);letter-spacing:1.5px;margin-bottom:6px;">INJECTED CREDENTIAL</div>
        <div style="font-family:var(--font-mono);font-size:1rem;color:var(--text-bright);letter-spacing:0.08em;">Ab3k&#x2022;&#x2022;&#x2022;&#x2022;&#x2022;&#x2022;&#x2022;&#x2022;&#x2022;&#x2022;&#x2022;&#x2022;7xPq</div>
        <div style="margin-top:8px;font-size:0.6rem;color:var(--text-muted);">Credential masked — only the PSM proxy receives the raw value</div>
      </div>`
  },
  {
    title: 'Session Launched',
    connector: 'PSM Connector',
    stageHtml: `
      <div>
        <div style="font-size:0.6rem;font-family:var(--font-mono);color:var(--text-muted);letter-spacing:1.5px;margin-bottom:8px;">PSM SESSION PROXY</div>
        <div style="background:var(--bg-page);border:1px solid var(--border);border-radius:4px;padding:10px;font-family:var(--font-mono);font-size:0.68rem;color:var(--cyan);margin-bottom:12px;">
          sys/&#x2022;&#x2022;&#x2022;&#x2022;&#x2022;&#x2022;&#x2022;&#x2022;&#x2022;&#x2022;&#x2022;&#x2022;&#x2022;&#x2022;&#x2022;&#x2022;&#x2022;&#x2022;@//db-server-01:1521/ORCL
        </div>
        <div style="display:grid;grid-template-columns:1fr 1fr;gap:10px;font-size:0.68rem;">
          <div><span style="color:var(--text-muted);font-family:var(--font-mono);">SESSION ID</span><br><span style="font-family:var(--font-mono);color:var(--text-bright);">PSM-DB-2847-A</span></div>
          <div><span style="color:var(--text-muted);font-family:var(--font-mono);">STATUS</span><br><span style="color:var(--green);">&#x25CF; RECORDING</span></div>
          <div><span style="color:var(--text-muted);font-family:var(--font-mono);">PORT</span><br><span style="font-family:var(--font-mono);color:var(--text-bright);">1521</span></div>
          <div><span style="color:var(--text-muted);font-family:var(--font-mono);">SERVICE NAME</span><br><span style="font-family:var(--font-mono);color:var(--text-bright);">ORCL</span></div>
        </div>
      </div>`
  },
  {
    title: 'Session Active',
    connector: 'PSM + Audit Connector',
    stageHtml: `
      <div>
        <div style="font-size:0.6rem;font-family:var(--font-mono);color:var(--text-muted);letter-spacing:1.5px;margin-bottom:8px;">LIVE ACTIVITY LOG</div>
        <div style="background:var(--bg-page);border:1px solid var(--border);border-radius:4px;padding:10px;font-family:var(--font-mono);font-size:0.65rem;color:var(--text-standard);line-height:1.9;">
          <span style="color:var(--text-muted);">14:22:01</span> <span style="color:var(--green);">SQL&gt;</span> SELECT * FROM DBA_USERS;<br>
          <span style="color:var(--text-muted);">14:22:03</span> <span style="color:var(--text-muted);">27 rows returned</span><br>
          <span style="color:var(--text-muted);">14:22:18</span> <span style="color:var(--green);">SQL&gt;</span> GRANT CONNECT TO app_user;<br>
          <span style="color:var(--text-muted);">14:22:19</span> <span style="color:var(--text-muted);">Grant succeeded.</span><br>
          <span style="color:var(--text-muted);">14:22:45</span> <span style="color:var(--green);">SQL&gt;</span> ALTER USER app_user IDENTIFIED BY &#x2022;&#x2022;&#x2022;&#x2022;&#x2022;&#x2022;&#x2022;&#x2022;;<br>
          <span style="color:var(--text-muted);">14:22:46</span> <span style="color:var(--text-muted);">User altered.</span>
        </div>
        <div style="margin-top:8px;font-size:0.6rem;color:var(--text-muted);">All commands recorded by PSM. Session timer: <span style="font-family:var(--font-mono);">00:01:47</span></div>
      </div>`
  },
  {
    title: 'Session End & Rotation',
    connector: 'CPM Connector',
    stageHtml: `
      <div>
        <div id="oracle-rotation-wrap">
          <div style="font-size:0.6rem;font-family:var(--font-mono);color:var(--text-muted);letter-spacing:1.5px;margin-bottom:8px;">CPM ROTATION</div>
          <div style="height:6px;background:var(--border);border-radius:3px;overflow:hidden;margin-bottom:6px;">
            <div id="oracle-progress-fill" style="height:100%;width:0%;background:var(--blue);border-radius:3px;transition:width 0.6s ease;"></div>
          </div>
          <div id="oracle-progress-msg" style="font-size:0.68rem;color:var(--text-muted);font-family:var(--font-mono);">Waiting to start rotation...</div>
        </div>
        <div style="margin-top:12px;">
          <div style="font-size:0.6rem;font-family:var(--font-mono);color:var(--text-muted);letter-spacing:1.5px;margin-bottom:6px;">OLD CREDENTIAL</div>
          <div id="oracle-cred-old" style="font-family:var(--font-mono);font-size:0.88rem;color:var(--text-bright);">Ab3k&#x2022;&#x2022;&#x2022;&#x2022;&#x2022;&#x2022;&#x2022;&#x2022;&#x2022;&#x2022;&#x2022;&#x2022;7xPq</div>
          <div id="oracle-cred-new" style="display:none;font-family:var(--font-mono);font-size:0.88rem;color:var(--green);margin-top:6px;"></div>
        </div>
        <button onclick="_oracleRunRotation()" id="oracle-rotate-btn" style="margin-top:14px;padding:8px 18px;background:var(--amber);color:#000;font-weight:700;font-size:0.78rem;border:none;border-radius:6px;cursor:pointer;">
          &#x21BB; Trigger CPM Rotation
        </button>
      </div>`
  }
];

const ORACLE_CONNECTORS = [
  null, // step 0: no connector
  { name: 'IDP / Directory Connector', legacy: 'LDAP integration via PVWA — Secondary ID login', target: 'OAuth2/OIDC federation — Primary ID only' },
  { name: 'Workflow Engine', legacy: 'Dual-control via PVWA request portal', target: 'Native workflow engine with webhook triggers' },
  { name: 'CCP / AAM Connector', legacy: 'CCP agent + POST /Accounts/{id}/Password/Retrieve', target: 'OAuth2 secrets API — no agent required' },
  { name: 'PSM Connector', legacy: 'PSM for Databases via PVWA proxy (OracleDB platform)', target: 'Session connector with direct DB tunnel' },
  { name: 'PSM + Audit Connector', legacy: 'PSM session recording stored in vault', target: 'Session recording in cloud + SIEM forwarding' },
  { name: 'Rotation Connector', legacy: 'CPM OracleDB.ini — ALTER USER {user} IDENTIFIED BY', target: 'Devolutions: RDM Agent rotation script  |  Keeper: Gateway rotation script  |  MiniOrange: basic script' }
];

function _labSwitchTab(tab) {
  _labTab = tab;
  ['jit','creds','oracle','connectors','identity'].forEach(t => {
    const panel = document.getElementById('lab-panel-' + t);
    const btn   = document.getElementById('lab-tab-' + t);
    if (panel) panel.style.display = (t === tab) ? 'block' : 'none';
    if (btn)   btn.classList.toggle('active', t === tab);
  });
}

function renderLabShowcase() {
  const el = document.getElementById('labContent');
  if (!el) return;

  el.innerHTML = `

  <div class="view-tabs">
    <button id="lab-tab-jit"        class="view-tab active"  onclick="_labSwitchTab('jit')">JIT Session Demo</button>
    <button id="lab-tab-creds"      class="view-tab"         onclick="_labSwitchTab('creds')">Credential Types</button>
    <button id="lab-tab-oracle"     class="view-tab"         onclick="_labSwitchTab('oracle')">Oracle DB Workflow</button>
    <button id="lab-tab-connectors" class="view-tab"         onclick="_labSwitchTab('connectors')">Connector Comparison</button>
    <button id="lab-tab-identity"   class="view-tab"         onclick="_labSwitchTab('identity')">Identity Transform</button>
  </div>

  <!-- ══ Tab 1: JIT Session Demo ══ -->
  <div id="lab-panel-jit">

    <!-- ══ Demo 1: JIT Secret Injection & Rotation ══ -->
    <div class="panel" style="margin-bottom:16px;">
      <div class="panel-header">
        <div class="panel-title">&#x1F510; Live Demo — JIT Secret Injection &amp; Auto-Rotation</div>
        <span style="font-size:0.6rem;color:var(--text-muted);font-family:var(--font-mono);">SIMULATED · NO VAULT REQUIRED</span>
      </div>
      <div class="panel-body" style="padding:20px;">

        <p style="font-size:0.72rem;color:var(--text-standard);line-height:1.7;margin-bottom:20px;">
          This demo shows the <strong>Just-In-Time privileged access flow</strong>: a user lands on a web page,
          the platform injects a credential directly from the CyberArk vault (the user never touches the vault UI),
          and when the session ends the secret is <strong>automatically rotated</strong> so the injected credential
          is immediately invalidated.
        </p>

        <div style="display:grid;grid-template-columns:1fr 1fr;gap:20px;" id="jit-grid">

          <!-- LEFT: form / active session -->
          <div>
            <!-- Phase 1: Setup form -->
            <div id="jit-setup">
              <div style="font-size:0.62rem;font-family:var(--font-mono);color:var(--text-muted);letter-spacing:1.5px;margin-bottom:6px;">TARGET ACCOUNT</div>
              <select id="jit-account" style="width:100%;padding:8px 10px;background:var(--bg-surface);border:1px solid var(--border);border-radius:6px;color:var(--text-bright);font-size:0.78rem;margin-bottom:12px;">
                <option value="demo-001">svc-webportal @ web-server-01 (WinServerLocal)</option>
                <option value="demo-002">svc-database @ db-server-01 (WinDomain)</option>
                <option value="demo-003">svc-api @ api-server-01 (UnixSSH)</option>
                <option value="demo-004">svc-backup @ backup-server (WinServerLocal)</option>
                <option value="demo-005">admin-portal @ mgmt-server-01 (WinDomain)</option>
              </select>

              <div style="font-size:0.62rem;font-family:var(--font-mono);color:var(--text-muted);letter-spacing:1.5px;margin-bottom:6px;">USER ID</div>
              <input id="jit-user" value="demo-admin" style="width:100%;padding:8px 10px;background:var(--bg-surface);border:1px solid var(--border);border-radius:6px;color:var(--text-bright);font-size:0.78rem;margin-bottom:12px;">

              <div style="font-size:0.62rem;font-family:var(--font-mono);color:var(--text-muted);letter-spacing:1.5px;margin-bottom:6px;">BUSINESS JUSTIFICATION</div>
              <input id="jit-reason" value="Emergency access — incident #INC-4821" style="width:100%;padding:8px 10px;background:var(--bg-surface);border:1px solid var(--border);border-radius:6px;color:var(--text-bright);font-size:0.78rem;margin-bottom:16px;">

              <button onclick="jitStart()" style="width:100%;padding:10px;background:var(--green);color:#000;font-weight:700;font-size:0.82rem;border:none;border-radius:6px;cursor:pointer;transition:opacity 0.2s;" onmouseover="this.style.opacity=0.85" onmouseout="this.style.opacity=1">
                &#x25B6; Start Privileged Session
              </button>
            </div>

            <!-- Phase 2: Active session -->
            <div id="jit-active" style="display:none;">

              <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:14px;">
                <div>
                  <div style="font-size:0.6rem;font-family:var(--font-mono);color:var(--text-muted);letter-spacing:1.5px;">SESSION ID</div>
                  <div id="jit-session-id" style="font-family:var(--font-mono);font-size:0.72rem;color:var(--text-muted);"></div>
                </div>
                <span id="jit-status-badge" class="badge badge-green">ACTIVE</span>
              </div>

              <div style="font-size:0.6rem;font-family:var(--font-mono);color:var(--text-muted);letter-spacing:1.5px;margin-bottom:4px;">ACCOUNT</div>
              <div id="jit-account-name" style="font-size:0.82rem;font-weight:600;color:var(--text-bright);margin-bottom:14px;"></div>

              <!-- Credential display -->
              <div style="background:var(--bg-surface);border:1px solid var(--border);border-radius:6px;padding:12px 14px;margin-bottom:14px;">
                <div style="font-size:0.58rem;font-family:var(--font-mono);color:var(--text-muted);letter-spacing:1.5px;margin-bottom:6px;">INJECTED CREDENTIAL</div>
                <div style="display:flex;align-items:center;gap:12px;">
                  <div style="flex:1;">
                    <div id="jit-cred-old" style="font-family:var(--font-mono);font-size:1rem;color:var(--text-bright);letter-spacing:0.08em;transition:all 0.4s;"></div>
                    <div id="jit-cred-new" style="display:none;font-family:var(--font-mono);font-size:1rem;color:var(--green);letter-spacing:0.08em;margin-top:4px;"></div>
                  </div>
                  <div style="text-align:right;">
                    <div id="jit-vault-label" style="font-size:0.6rem;font-family:var(--font-mono);color:var(--blue);">⬡ CyberArk Vault</div>
                    <div id="jit-cred-status" style="font-size:0.58rem;font-family:var(--font-mono);color:var(--text-muted);">ACTIVE</div>
                  </div>
                </div>
              </div>

              <!-- Timer -->
              <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:14px;">
                <div style="font-size:0.6rem;font-family:var(--font-mono);color:var(--text-muted);">SESSION DURATION</div>
                <div id="jit-timer" style="font-family:var(--font-mono);font-size:0.82rem;color:var(--text-bright);">00:00:00</div>
              </div>

              <!-- Rotation progress (hidden until end) -->
              <div id="jit-rotation-wrap" style="display:none;margin-bottom:14px;">
                <div style="height:6px;background:var(--border);border-radius:3px;overflow:hidden;margin-bottom:6px;">
                  <div id="jit-progress-fill" style="height:100%;width:0%;background:var(--blue);border-radius:3px;transition:width 0.6s ease;"></div>
                </div>
                <div id="jit-progress-msg" style="font-size:0.68rem;color:var(--text-muted);font-family:var(--font-mono);"></div>
              </div>

              <!-- Buttons -->
              <div style="display:flex;gap:8px;">
                <button id="jit-end-btn" onclick="jitEnd()" style="flex:1;padding:9px;background:var(--red);color:#fff;font-weight:700;font-size:0.78rem;border:none;border-radius:6px;cursor:pointer;transition:opacity 0.2s;" onmouseover="this.style.opacity=0.85" onmouseout="this.style.opacity=1">
                  &#x23F9; End Session &amp; Rotate Secret
                </button>
                <button onclick="jitReset()" style="padding:9px 14px;background:var(--bg-surface);border:1px solid var(--border);color:var(--text-muted);font-size:0.78rem;border-radius:6px;cursor:pointer;" title="Reset demo">&#x21BA;</button>
              </div>
            </div>
          </div>

          <!-- RIGHT: audit log -->
          <div>
            <div style="font-size:0.62rem;font-family:var(--font-mono);color:var(--text-muted);letter-spacing:1.5px;margin-bottom:10px;">SESSION AUDIT LOG</div>
            <div id="jit-log" style="background:var(--bg-surface);border:1px solid var(--border);border-radius:6px;padding:10px 12px;min-height:260px;max-height:360px;overflow-y:auto;">
              <div style="color:var(--text-muted);font-size:0.68rem;font-style:italic;padding:8px 0;">Start a session to see audit events...</div>
            </div>
          </div>

        </div><!-- /grid -->

        <!-- How it works callout -->
        <div class="callout teal" style="margin-top:20px;font-size:0.68rem;line-height:1.7;">
          <div class="callout-title">How This Works in Production</div>
          <div style="display:grid;grid-template-columns:repeat(3,1fr);gap:12px;margin-top:8px;">
            <div><strong style="color:var(--teal);">1. Session Start</strong><br>User identity verified → CyberArk AAM/CCP API called → credential injected into session context → audit log entry written with SHA-256 hash.</div>
            <div><strong style="color:var(--teal);">2. Session Active</strong><br>Credential is masked in all UI surfaces. Only the target system receives the raw value. CPM tracks the account as "checked out" — dual-control enforced.</div>
            <div><strong style="color:var(--teal);">3. Session End → Rotation</strong><br>Check-in triggers <code>POST /Accounts/{id}/Change</code> → CPM generates new credential → vault updated → old value invalidated within seconds.</div>
          </div>
        </div>

      </div><!-- /panel-body -->
    </div><!-- /panel -->

  </div><!-- /lab-panel-jit -->

  <!-- ══ Tab 2: Credential Types ══ -->
  <div id="lab-panel-creds" style="display:none;"></div>

  <!-- ══ Tab 3: Oracle DB Workflow ══ -->
  <div id="lab-panel-oracle" style="display:none;"></div>

  <!-- ══ Tab 4: Connector Comparison ══ -->
  <div id="lab-panel-connectors" style="display:none;"></div>

  <!-- ══ Tab 5: Identity Transform ══ -->
  <div id="lab-panel-identity" style="display:none;"></div>

  `;

  renderCredentialTypes();
  renderOracleWorkflow();
  renderConnectorComparison();
  renderIdentityTransform();
  _labSwitchTab(_labTab);
}

function renderCredentialTypes() {
  const el = document.getElementById('lab-panel-creds');
  if (!el) return;

  const cardStyle = (accent) =>
    `background:var(--bg-surface);border:1px solid var(--border);border-top:3px solid ${accent};border-radius:8px;padding:18px;`;

  const badgeStyle = (bg, color) =>
    `background:${bg};color:${color};font-family:var(--font-mono);font-size:0.55rem;padding:2px 7px;border-radius:3px;`;

  const fieldRow = (label, value) => `
    <div style="display:flex;justify-content:space-between;align-items:baseline;padding:5px 0;border-bottom:1px solid var(--border);font-size:0.72rem;">
      <span style="font-family:var(--font-mono);color:var(--text-muted);font-size:0.62rem;letter-spacing:0.04em;">${label}</span>
      <span style="color:var(--text-standard);text-align:right;max-width:60%;">${value}</span>
    </div>`;

  const useCasesList = (items) => items.map(i => `<li>${i}</li>`).join('');

  const riskBadge = (label, bg, color) =>
    `<div style="margin-top:14px;">
      <span style="background:${bg};color:${color};font-family:var(--font-mono);font-size:0.6rem;padding:3px 9px;border-radius:3px;font-weight:700;">${label}</span>
    </div>`;

  el.innerHTML = `
    <div class="panel">
      <div class="panel-header">
        <div class="panel-title">&#x1F4CB; Credential Models &mdash; Dedicated &middot; Shared &middot; ZSP / JIT</div>
      </div>
      <div class="panel-body" style="padding:20px;">

        <!-- ── Three credential cards ── -->
        <div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:16px;margin-bottom:24px;">

          <!-- Card 1: Dedicated -->
          <div style="${cardStyle('var(--green)')}">
            <div style="display:flex;justify-content:space-between;align-items:center;">
              <span style="${badgeStyle('var(--green-dim)', 'var(--green)')}">DEDICATED</span>
              <span style="font-size:1.1rem;">&#x1F512;</span>
            </div>
            <div style="font-weight:700;font-size:0.88rem;margin:10px 0 6px;color:var(--text-bright);">Dedicated Credential</div>
            <div style="font-size:0.72rem;color:var(--text-standard);line-height:1.6;margin-bottom:12px;">
              One credential bound to one person or service. No sharing. Individually tracked, rotated, and audited.
            </div>
            ${fieldRow('BOUND TO', 'svc-webportal @ web-server-01')}
            ${fieldRow('ROTATION', 'Every 30 days / on session end')}
            ${fieldRow('AUDIT TRAIL', 'Full individual history')}
            ${fieldRow('CHECKOUT', 'Single user at a time')}
            <div style="margin-top:12px;">
              <div style="font-size:0.62rem;font-family:var(--font-mono);color:var(--text-muted);letter-spacing:0.05em;margin-bottom:6px;">USE CASES</div>
              <ul style="font-size:0.72rem;color:var(--text-standard);line-height:1.7;padding-left:16px;margin:0;">
                ${useCasesList(['Human privileged admins', 'Service accounts with compliance requirements', 'Break-glass accounts'])}
              </ul>
            </div>
            ${riskBadge('LOW RISK', 'var(--green-dim)', 'var(--green)')}
          </div>

          <!-- Card 2: Shared -->
          <div style="${cardStyle('var(--amber)')}">
            <div style="display:flex;justify-content:space-between;align-items:center;">
              <span style="${badgeStyle('var(--amber-dim)', 'var(--amber)')}">SHARED</span>
              <span style="font-size:1.1rem;">&#x1F465;</span>
            </div>
            <div style="font-weight:700;font-size:0.88rem;margin:10px 0 6px;color:var(--text-bright);">Shared Credential</div>
            <div style="font-size:0.72rem;color:var(--text-standard);line-height:1.6;margin-bottom:12px;">
              One credential used by multiple people or services. Simpler to manage but requires tighter session controls.
            </div>
            ${fieldRow('BOUND TO', 'db-admin @ shared-pool-1')}
            ${fieldRow('ROTATION', 'On each checkout return')}
            ${fieldRow('AUDIT TRAIL', 'Session-level (who / when)')}
            ${fieldRow('CHECKOUT', 'Dual control / time-limited')}
            <div style="margin-top:12px;">
              <div style="font-size:0.62rem;font-family:var(--font-mono);color:var(--text-muted);letter-spacing:0.05em;margin-bottom:6px;">USE CASES</div>
              <ul style="font-size:0.72rem;color:var(--text-standard);line-height:1.7;padding-left:16px;margin:0;">
                ${useCasesList(['Shared service accounts', 'Legacy apps that cannot support individual credentials', 'Emergency break-glass pools'])}
              </ul>
            </div>
            ${riskBadge('MEDIUM RISK', 'var(--amber-dim)', 'var(--amber)')}
          </div>

          <!-- Card 3: ZSP / JIT -->
          <div style="${cardStyle('var(--blue)')}">
            <div style="display:flex;justify-content:space-between;align-items:center;">
              <span style="${badgeStyle('var(--blue-dim)', 'var(--blue)')}">ZERO STANDING PRIVILEGE</span>
              <span style="font-size:1.1rem;">&#x26A1;</span>
            </div>
            <div style="font-weight:700;font-size:0.88rem;margin:10px 0 6px;color:var(--text-bright);">ZSP / JIT Ephemeral</div>
            <div style="font-size:0.72rem;color:var(--text-standard);line-height:1.6;margin-bottom:12px;">
              No credential exists at rest. Created on-demand for the session duration, then immediately destroyed or rotated.
            </div>
            ${fieldRow('BOUND TO', 'Ephemeral &mdash; created per request')}
            ${fieldRow('ROTATION', 'Immediate post-session')}
            ${fieldRow('AUDIT TRAIL', 'Full session recording')}
            ${fieldRow('CHECKOUT', 'Auto-expires (TTL enforced)')}
            <div style="margin-top:12px;">
              <div style="font-size:0.62rem;font-family:var(--font-mono);color:var(--text-muted);letter-spacing:0.05em;margin-bottom:6px;">USE CASES</div>
              <ul style="font-size:0.72rem;color:var(--text-standard);line-height:1.7;padding-left:16px;margin:0;">
                ${useCasesList(['Just-In-Time access', 'Cloud workload identities', 'High-security environments (PCI / SOX zones)'])}
              </ul>
            </div>
            ${riskBadge('LOWEST RISK', 'var(--green-dim)', 'var(--green)')}
          </div>

        </div><!-- /card grid -->

        <!-- ── Comparison table ── -->
        <table class="compare-table">
          <thead>
            <tr>
              <th>Aspect</th>
              <th>Dedicated</th>
              <th>Shared</th>
              <th>ZSP / JIT</th>
            </tr>
          </thead>
          <tbody>
            <tr>
              <td>Standing credential exists?</td>
              <td class="risk-low">Yes</td>
              <td class="risk-medium">Yes</td>
              <td>No</td>
            </tr>
            <tr>
              <td>Simultaneous users</td>
              <td class="risk-low">1</td>
              <td class="risk-medium">Multiple</td>
              <td>1 (ephemeral)</td>
            </tr>
            <tr>
              <td>Rotation trigger</td>
              <td class="risk-low">Schedule / session end</td>
              <td class="risk-medium">Per checkout return</td>
              <td>Always post-session</td>
            </tr>
            <tr>
              <td>Blast radius if leaked</td>
              <td class="risk-low">Low &mdash; one account</td>
              <td class="risk-medium">High &mdash; all users</td>
              <td>Near-zero &mdash; expired</td>
            </tr>
            <tr>
              <td>Compliance best practice</td>
              <td class="risk-low">Yes</td>
              <td class="risk-medium">Conditional</td>
              <td>Gold standard</td>
            </tr>
            <tr>
              <td>Migration complexity</td>
              <td class="risk-low">Low</td>
              <td class="risk-medium">Medium</td>
              <td>High (workflow rebuild required)</td>
            </tr>
          </tbody>
        </table>

        <!-- ── What SHIFT Migrates callout ── -->
        <div class="callout teal" style="margin-top:20px;font-size:0.72rem;line-height:1.7;">
          <div class="callout-title">What SHIFT Migrates</div>
          SHIFT migrates Dedicated credentials 1:1. Shared credentials are flagged for rationalization &mdash;
          each should become Dedicated or ZSP where possible. ZSP/JIT patterns require new workflow configuration
          in the target PAM platform and are out of scope for automated ETL but are documented in the migration runbook.
        </div>

      </div><!-- /panel-body -->
    </div><!-- /panel -->
  `;
}
function renderOracleWorkflow() {
  const el = document.getElementById('lab-panel-oracle');
  if (!el) return;
  el.innerHTML = `
    <div class="panel" style="margin-bottom:16px;">
      <div class="panel-header">
        <div class="panel-title">&#x1F4CA; Oracle DB — CorePAS Privileged Access Workflow</div>
        <span style="font-size:0.6rem;color:var(--text-muted);font-family:var(--font-mono);">7 STEPS · CLICK-THROUGH</span>
      </div>
      <div class="panel-body" style="padding:20px;">

        <!-- Breadcrumb -->
        <div id="oracle-breadcrumb" style="display:flex;gap:6px;align-items:center;margin-bottom:20px;flex-wrap:wrap;"></div>

        <!-- Stage -->
        <div style="display:grid;grid-template-columns:1fr 1fr;gap:20px;margin-bottom:20px;">
          <div>
            <div id="oracle-step-title" style="font-size:0.78rem;font-weight:700;color:var(--text-bright);margin-bottom:12px;"></div>
            <div id="oracle-stage" style="background:var(--bg-surface);border:1px solid var(--border);border-radius:8px;padding:16px;min-height:160px;"></div>
          </div>
          <div>
            <div style="font-size:0.6rem;font-family:var(--font-mono);color:var(--text-muted);letter-spacing:1.5px;margin-bottom:8px;">ACTIVE CONNECTOR</div>
            <div id="oracle-connector-box" style="background:var(--bg-surface);border:1px solid var(--teal);border-radius:8px;padding:14px;min-height:160px;"></div>
          </div>
        </div>

        <!-- Controls -->
        <div style="display:flex;gap:10px;align-items:center;">
          <button id="oracle-prev-btn" onclick="_oraclePrev()" style="padding:8px 16px;background:var(--bg-surface);border:1px solid var(--border);color:var(--text-muted);font-size:0.78rem;border-radius:6px;cursor:pointer;">&#x276E; Previous</button>
          <button id="oracle-next-btn" onclick="_oracleNext()" style="padding:8px 20px;background:var(--teal);color:#000;font-weight:700;font-size:0.78rem;border:none;border-radius:6px;cursor:pointer;">Next Step &#x276F;</button>
          <span id="oracle-step-counter" style="font-size:0.68rem;font-family:var(--font-mono);color:var(--text-muted);margin-left:auto;"></span>
          <button onclick="_oracleReset()" style="padding:6px 12px;background:transparent;border:none;color:var(--text-muted);font-size:0.72rem;cursor:pointer;text-decoration:underline;">Restart</button>
        </div>

      </div>
    </div>
  `;
  _oracleRender();
}

function _oracleRender() {
  const s = _oracleStep;
  const step = ORACLE_STEPS[s];

  // Breadcrumb
  const bc = document.getElementById('oracle-breadcrumb');
  if (bc) {
    bc.innerHTML = ORACLE_STEPS.map((st, i) => {
      let bg, color, border;
      if (i < s) { bg = 'var(--green-dim)'; color = 'var(--green)'; border = '1px solid var(--green)'; }
      else if (i === s) { bg = 'var(--teal)'; color = '#000'; border = '1px solid var(--teal)'; }
      else { bg = 'var(--bg-surface)'; color = 'var(--text-muted)'; border = '1px solid var(--border)'; }
      return `<div onclick="_oracleGoTo(${i})" style="width:28px;height:28px;border-radius:50%;display:flex;align-items:center;justify-content:center;font-size:0.65rem;font-weight:700;font-family:var(--font-mono);cursor:pointer;background:${bg};color:${color};border:${border};flex-shrink:0;">${i+1}</div>
      ${i < ORACLE_STEPS.length-1 ? `<div style="flex:1;height:1px;background:var(--border);min-width:8px;"></div>` : ''}`;
    }).join('');
  }

  // Step title
  const titleEl = document.getElementById('oracle-step-title');
  if (titleEl) titleEl.textContent = `Step ${s+1}: ${step.title}`;

  // Stage content
  const stageEl = document.getElementById('oracle-stage');
  if (stageEl) stageEl.innerHTML = step.stageHtml;

  // Connector box
  const connEl = document.getElementById('oracle-connector-box');
  if (connEl) {
    const c = ORACLE_CONNECTORS[s];
    if (!c) {
      connEl.innerHTML = `<div style="color:var(--text-muted);font-size:0.72rem;font-style:italic;">No active connector at this step.</div>`;
    } else {
      connEl.innerHTML = `
        <div style="font-size:0.78rem;font-weight:700;color:var(--teal);margin-bottom:10px;">${c.name}</div>
        <div style="margin-bottom:8px;">
          <div style="font-size:0.6rem;font-family:var(--font-mono);color:var(--text-muted);letter-spacing:1px;margin-bottom:3px;">LEGACY CYBERARK</div>
          <div style="font-size:0.7rem;color:var(--text-standard);">${c.legacy}</div>
        </div>
        <div>
          <div style="font-size:0.6rem;font-family:var(--font-mono);color:var(--text-muted);letter-spacing:1px;margin-bottom:3px;">TARGET PAM</div>
          <div style="font-size:0.7rem;color:var(--green);">${c.target}</div>
        </div>`;
    }
  }

  // Counter
  const counter = document.getElementById('oracle-step-counter');
  if (counter) counter.textContent = `Step ${s+1} of ${ORACLE_STEPS.length}`;

  // Button states
  const prevBtn = document.getElementById('oracle-prev-btn');
  const nextBtn = document.getElementById('oracle-next-btn');
  if (prevBtn) prevBtn.disabled = s === 0;
  if (nextBtn) {
    nextBtn.disabled = s === ORACLE_STEPS.length - 1;
    nextBtn.textContent = s === ORACLE_STEPS.length - 2 ? 'Final Step \u203a' : 'Next Step \u203a';
  }
}

function _oracleNext()     { if (_oracleStep < ORACLE_STEPS.length - 1) { _oracleStep++; _oracleRender(); } }
function _oraclePrev()     { if (_oracleStep > 0) { _oracleStep--; _oracleRender(); } }
function _oracleGoTo(n)    { _oracleStep = n; _oracleRender(); }
function _oracleReset()    { _oracleStep = 0; _oracleRender(); }

function _oracleRunRotation() {
  const btn = document.getElementById('oracle-rotate-btn');
  if (btn) btn.disabled = true;

  const setProgress = (pct, msg) => {
    const f = document.getElementById('oracle-progress-fill');
    const m = document.getElementById('oracle-progress-msg');
    if (f) f.style.width = pct + '%';
    if (m) m.textContent = msg;
  };

  setProgress(5, 'Initiating CPM rotation\u2026');
  setTimeout(() => setProgress(25, 'Generating new credential\u2026'), 800);
  setTimeout(() => setProgress(55, 'Pushing to vault\u2026'), 1600);
  setTimeout(() => setProgress(85, 'Validating rotation\u2026'), 2400);
  setTimeout(() => {
    setProgress(100, 'Credential rotated successfully \u2713');
    const oldEl = document.getElementById('oracle-cred-old');
    if (oldEl) { oldEl.style.textDecoration = 'line-through'; oldEl.style.color = 'var(--red)'; }
    const newEl = document.getElementById('oracle-cred-new');
    if (newEl) { newEl.textContent = 'Xm9r\u2022\u2022\u2022\u2022\u2022\u2022\u2022\u2022\u2022\u2022\u2022\u20222kYd'; newEl.style.display = 'block'; }
  }, 3200);
}

function renderConnectorComparison() {
  const el = document.getElementById('lab-panel-connectors');
  if (!el) return;

  el.innerHTML = `
    <div class="panel-header">
      <span class="panel-title">&#x1F517; Connector Architecture &mdash; Legacy CyberArk vs Target PAM</span>
    </div>

    <div style="display:flex;gap:8px;margin-bottom:16px;">
      <button id="conn-tab-category" onclick="_connSwitchView('category')"></button>
      <button id="conn-tab-table" onclick="_connSwitchView('table')"></button>
    </div>

    <div id="conn-view-category">

      <!-- Group 1: Password Rotation -->
      <div class="panel" style="margin-bottom:12px;">
        <div class="panel-title">Password Rotation &mdash; CPM vs RPC vs Native</div>
        <table class="compare-table">
          <thead>
            <tr>
              <th>Aspect</th>
              <th>Legacy CyberArk CPM</th>
              <th>Devolutions (RDM Agent)</th>
              <th>Keeper (Gateway Script)</th>
            </tr>
          </thead>
          <tbody>
            <tr>
              <td>Component</td>
              <td>CPM &mdash; Central Policy Manager</td>
              <td>RPC &mdash; Remote Password Changer</td>
              <td>CPM &mdash; same component</td>
            </tr>
            <tr>
              <td>Plugin format</td>
              <td><code>.ini</code> platform file + <code>Process.ini</code></td>
              <td class="risk-medium">PowerShell script per Secret Template</td>
              <td class="risk-low"><code>.ini</code> &mdash; direct carry-over &#x2713;</td>
            </tr>
            <tr>
              <td>Oracle DB support</td>
              <td>OracleDB.ini built-in</td>
              <td class="risk-medium">Custom PowerShell script required</td>
              <td class="risk-low">OracleDB.ini direct carry-over &#x2713;</td>
            </tr>
            <tr>
              <td>Rotation trigger</td>
              <td>Schedule + session check-in</td>
              <td>Schedule + heartbeat</td>
              <td>Schedule + session check-in</td>
            </tr>
            <tr>
              <td>Migration path</td>
              <td>Source (paused during FREEZE)</td>
              <td class="risk-medium">Rebuild per template</td>
              <td class="risk-low">Direct carry-over</td>
            </tr>
          </tbody>
        </table>
      </div>

      <!-- Group 2: Session Management -->
      <div class="panel" style="margin-bottom:12px;">
        <div class="panel-title">Session Management &mdash; PSM vs RDM vs KCM</div>
        <table class="compare-table">
          <thead>
            <tr>
              <th>Aspect</th>
              <th>Legacy PSM</th>
              <th>Devolutions (RDM)</th>
              <th>Keeper (KCM)</th>
            </tr>
          </thead>
          <tbody>
            <tr>
              <td>Component</td>
              <td>PSM &mdash; Privileged Session Manager</td>
              <td>RDM/KCM gateway</td>
              <td>PSM for Cloud</td>
            </tr>
            <tr>
              <td>Protocol support</td>
              <td>RDP, SSH, DB via PSM for DBs</td>
              <td>SSH, RDP, DB, K8s, Web</td>
              <td>RDP, SSH, DB</td>
            </tr>
            <tr>
              <td>Recording storage</td>
              <td>Vault-side (on-prem)</td>
              <td>Keeper Cloud (KCM)</td>
              <td>CyberArk cloud</td>
            </tr>
            <tr>
              <td>PSM recording migration</td>
              <td>N/A</td>
              <td class="risk-high">Cannot migrate &#x2717;</td>
              <td>Can migrate &#x2713;</td>
            </tr>
            <tr>
              <td>Session isolation</td>
              <td>PVWA proxy</td>
              <td>RDM Gateway / KCM</td>
              <td>PVWA cloud proxy</td>
            </tr>
          </tbody>
        </table>
      </div>

      <!-- Group 3: Credential Retrieval -->
      <div class="panel" style="margin-bottom:12px;">
        <div class="panel-title">Credential Retrieval &mdash; CCP / AAM vs REST</div>
        <table class="compare-table">
          <thead>
            <tr>
              <th>Aspect</th>
              <th>Legacy CCP / AAM</th>
              <th>Devolutions REST</th>
              <th>Keeper API</th>
            </tr>
          </thead>
          <tbody>
            <tr>
              <td>Component</td>
              <td>CCP Agent + AAM SDK</td>
              <td>OAuth2 REST API</td>
              <td>CCP/AAM (similar pattern)</td>
            </tr>
            <tr>
              <td>App auth model</td>
              <td>Agent-based certificate</td>
              <td>Client credentials grant</td>
              <td>OAuth2 similar</td>
            </tr>
            <tr>
              <td>Secret endpoint</td>
              <td><code>POST /Accounts/{id}/Password/Retrieve</code></td>
              <td><code>GET /api/v1/entries/{id}</code></td>
              <td><code>POST /Accounts/{id}/Password/Retrieve</code></td>
            </tr>
            <tr>
              <td>Code change required</td>
              <td>N/A (source)</td>
              <td class="risk-high">Full rewrite</td>
              <td class="risk-low">Minor &mdash; same URL pattern</td>
            </tr>
            <tr>
              <td>Agent deployment</td>
              <td>CCP agent on app server</td>
              <td>None required</td>
              <td>CCP agent (optional)</td>
            </tr>
          </tbody>
        </table>
      </div>

      <!-- Group 4: Secret Schema -->
      <div class="panel" style="margin-bottom:12px;">
        <div class="panel-title">Secret Object &mdash; CyberArk Account vs Target</div>
        <div style="display:grid;grid-template-columns:1fr 1fr;gap:16px;margin-top:12px;">

          <!-- Left: CyberArk Account Object -->
          <div style="border:1px solid var(--blue);border-radius:6px;overflow:hidden;">
            <div style="background:var(--blue-dim);padding:6px 10px;font-size:0.6rem;font-family:var(--font-mono);color:var(--blue);letter-spacing:1px;">CYBERARK ACCOUNT OBJECT</div>
            <pre style="background:var(--bg-page);padding:12px;font-family:var(--font-mono);font-size:0.65rem;color:var(--text-standard);margin:0;overflow-x:auto;">{
  "name": "sys-ORCL-PROD-db01",
  "address": "db-server-01",
  "userName": "sys",
  "platformId": "OracleDB",
  "safeName": "DB-Production",
  "platformAccountProperties": {
    "Port": "1521",
    "Database": "ORCL"
  },
  "secretType": "password"
}</pre>
          </div>

          <!-- Right: two stacked targets -->
          <div>
            <!-- Keeper -->
            <div style="border:1px solid var(--green);border-radius:6px;overflow:hidden;">
              <div style="background:var(--cyan-dim);padding:6px 10px;font-size:0.6rem;font-family:var(--font-mono);color:var(--cyan);letter-spacing:1px;">KEEPER TARGET (3-TIER HIERARCHY)</div>
              <pre style="background:var(--bg-page);padding:12px;font-family:var(--font-mono);font-size:0.65rem;color:var(--text-standard);margin:0;overflow-x:auto;">{
  "name": "sys-ORCL-PROD-db01",  // identical
  "address": "db-server-01",     // identical
  "userName": "sys",             // identical
  "platformId": "OracleDB",      // identical
  "safeName": "DB-Production",   // identical &mdash; same schema
  "platformAccountProperties": {
    "Port": "1521",
    "Database": "ORCL"
  }
}</pre>
            </div>

            <!-- Devolutions -->
            <div style="border:1px solid var(--amber);border-radius:6px;overflow:hidden;margin-top:12px;">
              <div style="background:var(--blue-dim);padding:6px 10px;font-size:0.6rem;font-family:var(--font-mono);color:var(--blue);letter-spacing:1px;">DEVOLUTIONS SERVER TARGET (VAULT ENTRY MODEL)</div>
              <pre style="background:var(--bg-page);padding:12px;font-family:var(--font-mono);font-size:0.65rem;color:var(--text-standard);margin:0;overflow-x:auto;">{
  "name": "sys-ORCL-PROD-db01",
  "folderId": 142,               // &larr; was safeName
  "secretTemplateId": 6003,      // &larr; was platformId
  "items": [
    { "fieldName": "Username",  "itemValue": "sys" },
    { "fieldName": "Password",  "itemValue": "&#x2022;&#x2022;&#x2022;&#x2022;" },
    { "fieldName": "Server",    "itemValue": "db-server-01" },
    { "fieldName": "Port",      "itemValue": "1521" },
    { "fieldName": "Database",  "itemValue": "ORCL" }
  ]
}</pre>
            </div>
          </div>
        </div>

        <div class="callout amber" style="margin-top:16px;">
          <div class="callout-title">SHIFT ETL Transform</div>
          Agent 04 reads the CyberArk Account Object, maps platformId &rarr; templateId using agent_config.json, flattens platformAccountProperties into Secret Template field items, and resolves safeName &rarr; folderId from the pre-built folder map (Agent 13 + Agent 03).
        </div>
      </div>

    </div><!-- /#conn-view-category -->

    <div id="conn-view-table" style="display:none;">
      <table class="compare-table">
        <thead>
          <tr>
            <th>Component</th>
            <th>Legacy</th>
            <th>Legacy Mechanism</th>
            <th>Devolutions Target</th>
            <th>Keeper Target</th>
            <th>Migration Effort</th>
          </tr>
        </thead>
        <tbody>
          <tr>
            <td>Password Rotation</td>
            <td>CPM</td>
            <td><code>.ini</code> platform plugin + Process.ini</td>
            <td>RPC PowerShell script per template</td>
            <td>CPM <code>.ini</code> &mdash; direct carry-over</td>
            <td><span class="risk-high">High (Keeper 3-tier)</span> / <span class="risk-medium">Med (Devolutions)</span></td>
          </tr>
          <tr>
            <td>Session Management</td>
            <td>PSM</td>
            <td>PVWA session proxy</td>
            <td>RDM / KCM gateway</td>
            <td>PSM for Cloud</td>
            <td class="risk-medium">Medium</td>
          </tr>
          <tr>
            <td>Credential Retrieval</td>
            <td>CCP / AAM</td>
            <td>Agent + certificate auth</td>
            <td>OAuth2 REST API</td>
            <td>CCP / AAM OAuth2</td>
            <td><span class="risk-high">High (Keeper 3-tier)</span> / <span class="risk-medium">Med (Devolutions)</span></td>
          </tr>
          <tr>
            <td>Dual-Control Workflow</td>
            <td>PVWA Portal</td>
            <td>Request + dual approval forms</td>
            <td>Native workflow + webhooks</td>
            <td>PVWA workflow engine</td>
            <td class="risk-medium">Medium</td>
          </tr>
          <tr>
            <td>SIEM Integration</td>
            <td>SIEM Connector</td>
            <td>Syslog + LEEF format</td>
            <td>Syslog / webhook</td>
            <td>Syslog / webhook</td>
            <td class="risk-low">Low</td>
          </tr>
          <tr>
            <td>IDP Integration</td>
            <td>LDAP/SAML</td>
            <td>PVWA + LDAP bind</td>
            <td>SSO + SCIM</td>
            <td>SSO + SCIM</td>
            <td class="risk-medium">Medium</td>
          </tr>
        </tbody>
      </table>
    </div><!-- /#conn-view-table -->
  `;

  _connSwitchView(_connView);
}

function _connSwitchView(view) {
  _connView = view;
  const catPanel   = document.getElementById('conn-view-category');
  const tablePanel = document.getElementById('conn-view-table');
  const catBtn     = document.getElementById('conn-tab-category');
  const tableBtn   = document.getElementById('conn-tab-table');
  if (catPanel)   catPanel.style.display   = (view === 'category') ? 'block' : 'none';
  if (tablePanel) tablePanel.style.display = (view === 'table')    ? 'block' : 'none';
  const activeStyle   = 'background:var(--teal-dim);color:var(--teal);border:1px solid var(--teal);padding:6px 14px;font-size:0.72rem;font-weight:600;border-radius:4px;cursor:pointer;font-family:var(--font-mono);';
  const inactiveStyle = 'background:var(--bg-surface);color:var(--text-muted);border:1px solid var(--border);padding:6px 14px;font-size:0.72rem;border-radius:4px;cursor:pointer;font-family:var(--font-mono);';
  if (catBtn)   { catBtn.textContent   = 'By Category';     catBtn.style.cssText   = (view === 'category') ? activeStyle : inactiveStyle; }
  if (tableBtn) { tableBtn.textContent = 'Side-by-Side Table'; tableBtn.style.cssText = (view === 'table')    ? activeStyle : inactiveStyle; }
}

function renderIdentityTransform() {
  const el = document.getElementById('lab-panel-identity');
  if (!el) return;

  // ── helpers ──────────────────────────────────────────────
  const identityBox = ({ icon, label, value, description, borderColor }) => `
    <div style="background:var(--bg-page);border:1px solid ${borderColor || 'var(--border)'};border-radius:6px;padding:12px;">
      <div style="font-size:0.65rem;font-family:var(--font-mono);color:var(--text-muted);letter-spacing:1px;margin-bottom:4px;">${icon} ${label}</div>
      ${value ? `<div style="font-size:0.88rem;font-weight:700;color:var(--text-bright);font-family:var(--font-mono);margin-bottom:4px;">${value}</div>` : ''}
      <div style="font-size:0.68rem;color:var(--text-muted);">${description}</div>
    </div>`;

  const subLabel = (text) =>
    `<div style="font-size:0.6rem;font-family:var(--font-mono);color:var(--text-muted);letter-spacing:1.5px;text-transform:uppercase;margin-bottom:8px;">${text}</div>`;

  const downArrow = (color) =>
    `<div style="text-align:center;font-size:1.1rem;color:${color};margin:6px 0;">&darr;</div>`;

  // ── TODAY card ───────────────────────────────────────────
  const todayCard = `
    <div class="card" style="border-top:3px solid var(--amber);">
      <div style="font-size:0.6rem;font-family:var(--font-mono);color:var(--amber);letter-spacing:1.5px;margin-bottom:14px;">TODAY — CyberArk PAS (Legacy)</div>

      ${subLabel('HUMAN USERS')}
      ${identityBox({ icon: '&#x1F464;', label: 'PRIMARY ID', value: 'j.smith@corp.com', description: 'Corporate identity — AD/email/apps login' })}
      ${downArrow('var(--amber)')}
      ${identityBox({ icon: '&#x1F511;', label: 'SECONDARY ID (VAULT)', value: 'j.smith-priv', description: 'Privileged vault account — PVWA login only' })}

      <div style="background:var(--amber-dim);border-left:3px solid var(--amber);border-radius:0 4px 4px 0;padding:10px;margin-top:10px;font-size:0.68rem;">
        <div style="font-weight:700;color:var(--amber);margin-bottom:6px;">&#x26A0; Pain Points</div>
        <ul style="margin:0;padding-left:16px;color:var(--text-muted);line-height:1.7;">
          <li>Two separate passwords to manage</li>
          <li>PVWA login uses secondary ID only</li>
          <li>Access reviews cover both accounts separately</li>
          <li>De-provisioning requires two steps</li>
        </ul>
      </div>

      <div style="margin-top:16px;">
        ${subLabel('APPLICATIONS / SERVICES')}
        ${identityBox({ icon: '&#x2699;', label: 'PRIMARY ID (ONLY)', value: 'svc-oracle-prod', description: 'Single service account, CPM-managed', borderColor: 'var(--green)' })}
      </div>
    </div>`;

  // ── TARGET WORLD card ────────────────────────────────────
  const targetCard = `
    <div class="card" style="border-top:3px solid var(--green);">
      <div style="font-size:0.6rem;font-family:var(--font-mono);color:var(--green);letter-spacing:1.5px;margin-bottom:14px;">TARGET WORLD — Unified PAM</div>

      ${subLabel('HUMAN USERS')}
      ${identityBox({ icon: '&#x1F464;', label: 'SINGLE IDENTITY', value: 'j.smith@corp.com', description: 'Corporate identity — SSO into PAM portal', borderColor: 'var(--green)' })}
      ${downArrow('var(--green)')}
      <div style="background:var(--bg-page);border:1px solid var(--blue);border-radius:6px;padding:12px;">
        <div style="font-size:0.65rem;font-family:var(--font-mono);color:var(--text-muted);letter-spacing:1px;margin-bottom:4px;">&#x26A1; DYNAMIC JIT GRANT</div>
        <div style="font-size:0.68rem;color:var(--text-muted);">Ephemeral privilege — approved per request, auto-expires after TTL. No standing secondary account.</div>
      </div>

      <div style="background:var(--teal-dim);border-left:3px solid var(--teal);border-radius:0 4px 4px 0;padding:10px;margin-top:10px;font-size:0.68rem;">
        <div style="font-weight:700;color:var(--teal);margin-bottom:6px;">&#x2714; Resolved</div>
        <ul style="margin:0;padding-left:16px;color:var(--text-muted);line-height:1.7;">
          <li>Single identity — SSO login into PAM portal</li>
          <li>No secondary account to provision or de-provision</li>
          <li>Access reviews on one account only</li>
          <li>Automated onboarding via IDP + SCIM</li>
        </ul>
      </div>

      <div style="margin-top:16px;">
        ${subLabel('APPLICATIONS / SERVICES')}
        ${identityBox({ icon: '&#x2699;', label: 'WORKLOAD IDENTITY', value: 'svc-oracle-prod OR ephemeral', description: 'Secrets fetched via OAuth2 API — no human ever touches the password', borderColor: 'var(--teal)' })}
      </div>
    </div>`;

  // ── Section 3: scenario table rows ───────────────────────
  const tableRows = [
    {
      scenario: 'DBA needs emergency Oracle access',
      today: 'Log into PVWA with secondary ID (j.smith-priv), request dual-control access, wait for approval, launch PSM session',
      target: 'SSO into PAM portal with primary ID, request JIT &rarr; auto-approve or manager approves &rarr; ephemeral credential injected',
      connector: 'IDP + JIT Workflow Connector'
    },
    {
      scenario: 'App needs DB password at runtime',
      today: 'App calls CCP agent with certificate, agent retrieves from vault, returns raw password',
      target: 'App calls OAuth2 secrets endpoint with client credentials, gets ephemeral token, secret returned',
      connector: 'CCP / AAM &rarr; OAuth2 Connector'
    },
    {
      scenario: 'New admin onboarding',
      today: 'Create corp AD account + create PVWA secondary ID + assign to safes + train on PVWA',
      target: 'Create corp AD account + assign PAM role &rarr; done. PAM portal auto-provisioned via SSO + SCIM',
      connector: 'IDP / SCIM Connector'
    }
  ].map(r => `
    <tr>
      <td>${r.scenario}</td>
      <td class="risk-medium">${r.today}</td>
      <td>${r.target}</td>
      <td style="font-family:var(--font-mono);font-size:0.68rem;color:var(--teal);">${r.connector}</td>
    </tr>`).join('');

  el.innerHTML = `
    <div class="panel">
      <div class="panel-title">&#x1F464; Identity Model — Today vs Target World</div>

      <!-- Section 1: Two-column cards -->
      <div style="display:grid;grid-template-columns:1fr 1fr;gap:20px;margin-bottom:20px;">
        ${todayCard}
        ${targetCard}
      </div>

      <!-- Section 2: Transformation arrow row -->
      <div style="display:flex;align-items:center;justify-content:center;gap:12px;margin:16px 0;padding:12px;background:var(--bg-surface);border-radius:6px;">
        <div style="text-align:center;">
          <div style="font-size:1.3rem;color:var(--teal);">&#x2192;</div>
          <div style="font-size:0.82rem;font-weight:700;color:var(--teal);font-family:var(--font-mono);letter-spacing:0.5px;">SHIFT Migration Transforms Identity Experience</div>
          <div style="font-size:0.66rem;color:var(--text-muted);margin-top:4px;">Human vault accounts reduced &middot; Service accounts consolidated &middot; ZSP available for high-security zones</div>
        </div>
      </div>

      <!-- Section 3: Scenario comparison table -->
      <table class="compare-table">
        <thead>
          <tr>
            <th>Scenario</th>
            <th>Today's Experience</th>
            <th>Target Experience</th>
            <th>Connector Involved</th>
          </tr>
        </thead>
        <tbody>
          ${tableRows}
        </tbody>
      </table>

      <!-- Section 4: Bottom callout -->
      <div class="callout teal">
        <div class="callout-title">Key Design Decision</div>
        In the target world, the number of managed identities in the PAM vault decreases — humans use dynamic privilege grants instead of standing vault accounts, and applications use workload identity or ephemeral secrets. The vault becomes smaller but more powerful. This is the core identity experience transformation SHIFT enables.
      </div>
    </div>`;
}

// ── Simulation functions ──────────────────────────────────

function jitStart() {
  const accountSel = document.getElementById('jit-account');
  const accountName = accountSel.options[accountSel.selectedIndex].text;

  _jit.sessionId  = 'SESS-' + Math.random().toString(36).slice(2, 10).toUpperCase();
  _jit.accountName = accountName;
  _jit.maskedSecret = _jitMask(_jitGenPw());
  _jit.elapsed = 0;

  // Switch phases
  document.getElementById('jit-setup').style.display  = 'none';
  document.getElementById('jit-active').style.display = 'block';

  // Populate
  document.getElementById('jit-session-id').textContent  = _jit.sessionId;
  document.getElementById('jit-account-name').textContent = _jit.accountName;
  document.getElementById('jit-cred-old').textContent     = _jit.maskedSecret;
  document.getElementById('jit-cred-old').style.textDecoration = 'none';
  document.getElementById('jit-cred-old').style.color    = 'var(--text-bright)';
  document.getElementById('jit-cred-new').style.display  = 'none';
  document.getElementById('jit-vault-label').textContent  = '⬡ CyberArk Vault';
  document.getElementById('jit-vault-label').style.color  = 'var(--blue)';
  document.getElementById('jit-cred-status').textContent  = 'ACTIVE';
  document.getElementById('jit-cred-status').style.color  = 'var(--green)';
  document.getElementById('jit-rotation-wrap').style.display = 'none';
  document.getElementById('jit-progress-fill').style.width   = '0%';
  document.getElementById('jit-progress-msg').textContent    = '';
  document.getElementById('jit-end-btn').disabled = false;
  _jitBadge('ACTIVE', 'badge-green');

  // Timer
  clearInterval(_jit.timer);
  _jit.timer = setInterval(() => {
    _jit.elapsed++;
    const h = String(Math.floor(_jit.elapsed / 3600)).padStart(2,'0');
    const m = String(Math.floor((_jit.elapsed % 3600) / 60)).padStart(2,'0');
    const s = String(_jit.elapsed % 60).padStart(2,'0');
    const el = document.getElementById('jit-timer');
    if (el) el.textContent = `${h}:${m}:${s}`;
  }, 1000);

  // Clear + populate log
  const log = document.getElementById('jit-log');
  log.innerHTML = '';
  _jitLog('SESSION_STARTED',       `Session ${_jit.sessionId} started for ${_jit.accountName}`);
  _jitLog('CREDENTIAL_INJECTED',   `Secret retrieved from CyberArk vault \u2192 ${_jit.maskedSecret}`);
}

function jitEnd() {
  document.getElementById('jit-end-btn').disabled = true;
  document.getElementById('jit-rotation-wrap').style.display = 'block';
  clearInterval(_jit.timer);
  _jitBadge('ROTATING', 'badge-amber');

  _jitLog('ROTATION_STARTING', 'CPM rotation initiated — account checked in');
  _jitProg(5, 'Initiating CPM rotation\u2026');

  setTimeout(() => { _jitLog('ROTATION_PROGRESS', 'Generating new credential\u2026');   _jitProg(25, 'Generating new credential\u2026'); },   800);
  setTimeout(() => { _jitLog('ROTATION_PROGRESS', 'Pushing to vault\u2026');            _jitProg(55, 'Pushing to vault\u2026'); },            1600);
  setTimeout(() => { _jitLog('ROTATION_PROGRESS', 'Validating rotation\u2026');         _jitProg(85, 'Validating rotation\u2026'); },         2400);

  setTimeout(() => {
    const newMasked = _jitMask(_jitGenPw());

    _jitProg(100, 'Credential rotated successfully \u2713');
    _jitLog('ROTATION_COMPLETE', `New credential issued \u2192 ${newMasked}`);

    // Strike old, reveal new
    const oldEl = document.getElementById('jit-cred-old');
    oldEl.style.textDecoration = 'line-through';
    oldEl.style.color = 'var(--red)';

    const newEl = document.getElementById('jit-cred-new');
    newEl.textContent = newMasked;
    newEl.style.display = 'block';

    document.getElementById('jit-vault-label').textContent = '⬡ CyberArk Vault (Rotated)';
    document.getElementById('jit-vault-label').style.color = 'var(--green)';
    document.getElementById('jit-cred-status').textContent = 'ROTATED \u2014 INVALID';
    document.getElementById('jit-cred-status').style.color = 'var(--red)';

    _jitBadge('ENDED', 'badge-muted');

    setTimeout(() => _jitLog('SESSION_ENDED', 'Session closed. Old credential is now invalid.'), 200);
  }, 3200);
}

function jitReset() {
  clearInterval(_jit.timer);
  _jit = { sessionId:null, accountName:null, maskedSecret:null, timer:null, elapsed:0 };
  document.getElementById('jit-setup').style.display  = 'block';
  document.getElementById('jit-active').style.display = 'none';
  document.getElementById('jit-log').innerHTML =
    '<div style="color:var(--text-muted);font-size:0.68rem;font-style:italic;padding:8px 0;">Start a session to see audit events...</div>';
}

// ── Helpers ───────────────────────────────────────────────

function _jitGenPw() {
  const c = 'ABCDEFGHJKLMNPQRSTUVWXYZabcdefghjkmnpqrstuvwxyz23456789!@#$%';
  let pw = '';
  for (let i = 0; i < 20; i++) pw += c[Math.floor(Math.random() * c.length)];
  return pw;
}

function _jitMask(pw) {
  if (!pw || pw.length < 10) return '\u2022\u2022\u2022\u2022\u2022\u2022\u2022\u2022\u2022\u2022\u2022\u2022';
  return pw.slice(0, 4) + '\u2022\u2022\u2022\u2022\u2022\u2022\u2022\u2022\u2022\u2022\u2022\u2022' + pw.slice(-4);
}

function _jitProg(pct, msg) {
  const f = document.getElementById('jit-progress-fill');
  const m = document.getElementById('jit-progress-msg');
  if (f) f.style.width = pct + '%';
  if (m) m.textContent = msg;
}

function _jitBadge(text, cls) {
  const b = document.getElementById('jit-status-badge');
  if (!b) return;
  b.textContent = text;
  b.className = 'badge ' + cls;
}

function _jitLog(type, message) {
  const container = document.getElementById('jit-log');
  if (!container) return;
  const now = new Date().toISOString().replace('T',' ').substring(0,19);
  const colors = {
    SESSION_STARTED:    'var(--blue)',
    CREDENTIAL_INJECTED:'var(--green)',
    ROTATION_STARTING:  'var(--amber)',
    ROTATION_PROGRESS:  'var(--amber)',
    ROTATION_COMPLETE:  'var(--green)',
    SESSION_ENDED:      'var(--text-muted)',
    ERROR:              'var(--red)',
  };
  const div = document.createElement('div');
  div.style.cssText = 'padding:5px 0;border-bottom:1px solid var(--border);display:flex;gap:10px;font-size:0.68rem;';
  div.innerHTML = `
    <span style="color:var(--text-muted);font-family:var(--font-mono);white-space:nowrap;flex-shrink:0;">${now}</span>
    <span style="font-weight:700;min-width:9.5rem;flex-shrink:0;color:${colors[type]||'var(--text-standard)'};">${type}</span>
    <span style="color:var(--text-standard);">${message}</span>`;
  // Remove placeholder text on first entry
  if (container.querySelector('div[style*="italic"]')) container.innerHTML = '';
  container.insertBefore(div, container.firstChild);
}

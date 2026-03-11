/**
 * Lab Showcase — interactive PAM capability demonstrations.
 * All simulations run client-side; no backend required.
 */

// ── JIT Session simulation state ─────────────────────────
let _jit = {
  sessionId: null, accountName: null,
  maskedSecret: null, timer: null, elapsed: 0
};

function renderLabShowcase() {
  const el = document.getElementById('labContent');
  if (!el) return;

  el.innerHTML = `

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

  `;
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

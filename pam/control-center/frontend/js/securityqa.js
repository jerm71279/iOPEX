/**
 * Security Q&A page — deep dive for Enterprise Security Architect
 */
function renderSecurityQA() {
  const el = document.getElementById('securityQAContent');
  if (!el) return;

  const sections = [
    ['Data Encryption & Secrets at Rest', [
      ['How are privileged credentials protected at rest in the target platform?',
        '<strong>Keeper (recommended primary):</strong> Zero-knowledge AES-256-GCM. The Keeper server never sees plaintext — encryption/decryption happens client-side. Even a full server compromise exposes only ciphertext. FedRAMP High authorized (March 2026).<br><br><strong>Devolutions RDM:</strong> Credentials stored encrypted (AES-256). In JIT mode, passwords are never stored in RDM — pulled live from Keeper via KSM at session launch and discarded immediately after.<br><br><strong>MiniOrange:</strong> Handles identity tokens, not credential storage. Not in scope for vault-at-rest risk.'],
      ['During migration, credentials are in-flight between CyberArk and the target. What protects them in transit?',
        'All extraction uses CyberArk PVWA REST API over HTTPS — TLS enforced, no plain HTTP fallback. Passwords retrieved via <code>POST /Accounts/{id}/Password/Retrieve</code> are held in memory only during the ETL EXPORT→IMPORT step. The orchestrator zeroes password variables from memory immediately after use. Credentials never touch disk, log files, or state files. Any exception that fires during that window goes through error sanitization that strips secrets before writing to the audit log.'],
      ['What happens to the credential if the import step fails mid-flight?',
        'The watchdog timer triggers an emergency UNFREEZE of the source vault and the failed account is flagged in the audit log for manual review. The partial import is rolled back. The credential is never left in a half-migrated limbo state where it exists in both platforms simultaneously without control.'],
    ]],
    ['Authentication & Access Control', [
      ['How does the orchestration platform authenticate to CyberArk PVWA?',
        'Via CyberArk native auth (CyberArk/LDAP/RADIUS/Windows). Credentials are passed as environment variables — never in config files or code. A dedicated service account (<code>svc-migration</code>) with least-privilege access to only the Safes being migrated in the current wave is used. No standing admin access.'],
      ['How does it authenticate to Keeper?',
        'OAuth2 client credentials grant via Keeper PAM API. Client ID and secret are environment variables. Token is refreshed proactively before expiry (within 60 seconds) — no silent token failures during a live migration run.'],
      ['What happens to the 22 CyberArk permissions during migration to Keeper?',
        'Keeper uses a Vault role model — not a 1:1 map. Agent 03 translates the 22 permissions and flags two critical risks:<br><br><strong>Permission loss</strong> — 9 permissions have no Keeper equivalent and are permanently dropped.<br><strong>Escalation</strong> — some members may receive <em>more</em> access than intended due to role rounding.<br><br>Agent 03 produces a full escalation and loss report. <strong>iOPEX cannot approve this output.</strong> Enterprise Security Architect must independently review every escalation flag before Phase 3 proceeds. This is a PCI-DSS Requirement 7.1 dual-control — the team that performs a control cannot also approve it.'],
      ['Which 9 permissions are lost with no equivalent in any target?',
        '<code>AccessWithoutConfirmation</code>, <code>SpecifyNextAccountContent</code>, <code>BackupSafe</code>, <code>CreateFolders</code>, <code>DeleteFolders</code>, <code>MoveAccountsAndFolders</code>, <code>RequestsAuthorizationLevel1</code>, <code>RequestsAuthorizationLevel2</code>, <code>InitiateCPMAccountManagementOperations</code>.<br><br>All must be reviewed for compliance impact before migration proceeds.'],
      ['Is MFA enforced for privileged access in the target architecture?',
        'Yes — MiniOrange provides the identity and MFA layer (TOTP, Push, FIDO2). It acts as the SAML/OIDC identity provider. Users authenticate through MiniOrange MFA before receiving a Keeper session token or a Devolutions RDM session. <strong>Step-up MFA</strong> triggers for high-sensitivity vaults — a second factor challenge fires even for already-authenticated sessions reaching defined high-risk entries.'],
    ]],
    ['Network Security', [
      ['What network exposure does the Keeper Gateway require?',
        'The KSM gateway runs as a Docker container (minimum 4 CPU / 16 GB) and requires line-of-sight to all managed target systems. It sits inside the Enterprise network perimeter — it does NOT require inbound internet exposure. Outbound HTTPS to Keeper cloud for command polling only. No inbound firewall rules needed for the gateway itself.'],
      ['What about Cisco-specific network device coverage — IOS, NX-OS, ASA?',
        'All three are included. CyberArk\'s existing platform plugins for Cisco IOS/NX-OS/ASA carry forward. The Ansible-based automation layer consumes Keeper-managed credentials via the native KSM SDK — no plaintext credentials in Ansible playbooks or inventory files.'],
      ['Can the CI/CD pipeline run on public cloud runners?',
        'No. CI/CD runners must be self-hosted inside the Enterprise network. They need reachable paths to CyberArk PVWA (source), Keeper Gateway (target), and KCM (session layer). Public runners have no network path and would be blocked at the firewall. This is enforced by network topology, not just policy.'],
      ['How are secrets injected into the CI/CD pipeline without hardcoding?',
        'Secrets are injected at runtime from the chosen secret store (Keeper KSM). They are never in YAML, never in environment variable blocks in pipeline config files, never in logs. <code>trufflehog</code> and <code>detect-secrets</code> scan every commit and every file before merge — the pipeline hard-fails on any credential pattern detected.'],
    ]],
    ['Audit, Compliance & Governance', [
      ['What happens to the CyberArk audit trail when we migrate?',
        '<strong style="color:var(--red)">This is the most critical compliance risk in the program.</strong> CyberArk audit history does NOT migrate to any target platform. The audit trail restarts at the migration date. Agent 07 automatically exports and archives all CyberArk audit logs before decommission in P7. Archived logs must be retained per the Enterprise compliance retention policy (7 years for SOX, 1 year for PCI-DSS minimum).'],
      ['How do we maintain PCI-DSS compliance through the migration window?',
        'Three controls:<br><br><strong>1. Dual-control at gate g3</strong> — Agent 03 permission mapping output reviewed by Enterprise Security Architect, not iOPEX.<br><strong>2. Parallel running (P6)</strong> — both CyberArk and the target are live simultaneously; no single point of failure.<br><strong>3. Read-only gate (g13)</strong> — CyberArk is set to read-only until all three independent Enterprise approvers (CAB, Exec Sponsor, Compliance) authorize.'],
      ['What does SOX Section 404 require from us specifically?',
        'Gate g9 requires Compliance sign-off in addition to App Owner confirmation before production waves proceed. SOX 404 mandates dual-control for credential management operations — iOPEX cannot satisfy both the executor and approver roles. Enterprise Compliance must be an independent approver at this gate.'],
      ['What is the highest-authority gate and what can block it?',
        'Gate g13 — Cutover Approval. Sets the source CyberArk vault to read-only — the last reversible action before decommission. All three Enterprise approvers must authorize. If any approver is unavailable or withholds approval, the migration pauses indefinitely. iOPEX cannot proceed on partial or verbal authorization.'],
      ['How is the audit log itself protected against tampering?',
        'The orchestrator writes audit logs in JSONL format with a SHA-256 hash chain — each entry includes the hash of the previous entry. Any tampering with a log entry breaks the chain and is immediately detectable. SIEM-ready format for ingestion into the Enterprise SIEM infrastructure.'],
    ]],
    ['Non-Human Identities (NHI) & DevOps Secrets', [
      ['How are service accounts and machine identities handled differently from human accounts?',
        'NHI detection uses three independent signals: (1) platform type (UnixSSHKeys, WinServiceAccount, AWSAccessKeys), (2) naming patterns (<code>svc-</code>, <code>app-</code>, <code>service.account</code>), (3) Safe name patterns (<code>appcred</code>, <code>automation</code>, <code>cicd</code>, <code>pipeline</code>). NHIs get a separate migration track — they cannot simply be copied to the new vault without re-pointing the consuming applications.'],
      ['What replaces CCP/AAM for application credential retrieval?',
        'Keeper Secrets Manager (KSM) — 40+ native integrations covering GitHub Actions, Terraform, Ansible, Kubernetes, Jenkins. Agent 06 scans all application code for CCP/AAM patterns and generates the replacement code. This is a full re-architecture for any app that relied on the AAM agent injection model.'],
      ['What about Conjur secrets for Kubernetes and CI/CD pipelines?',
        'Conjur secrets require platform re-architecture — app teams must update their SDK calls. This is out-of-scope for the automated migration and requires direct engagement with each app team. Tracked as PENDING_EXTERNAL_TEAM items in the PMO Directive.'],
      ['Are there zero standing privilege controls in the target architecture?',
        'Yes — Devolutions RDM entries pull credentials directly from Keeper via KSM API at session launch. Passwords are never stored in RDM. Retrieved just-in-time and discarded after the session closes. Combined with MiniOrange\'s adaptive authentication, no user holds a standing credential to a privileged system outside of an active, logged session.'],
    ]],
    ['Penetration Testing & Security Validation', [
      ['When does penetration testing occur and what does it cover?',
        'Pre-P5 (before production waves begin). Scope:<br><br>• <strong>Secret zeroing validation</strong> — credentials not recoverable from memory after use<br>• <strong>State file permissions</strong> — migration state files not world-readable<br>• <strong>TLS configuration</strong> — cipher suites, certificate validation, no self-signed certs in production<br>• <strong>API authentication posture</strong> — no unauthenticated endpoints, token scoping, rotation<br>• <strong>Injection vectors</strong> — subprocess calls, config parsing, error message sanitization'],
      ['What static analysis runs on the orchestrator code itself?',
        '• <code>bandit</code> — Python security anti-patterns: hardcoded secrets, subprocess injection, insecure deserialization. Pipeline hard-fails on any HIGH severity finding.<br>• <code>trufflehog</code> / <code>detect-secrets</code> — scans repo history and staged files for credential patterns. A single match hard-fails the pipeline and blocks merge until remediated.'],
    ]],
    ['Operational Security During Migration', [
      ['What prevents a rogue wave run from hitting production accounts?',
        'Gate g6 (Pilot Gate) is a hard block on all production waves. The pilot wave must complete with App Owner physical verification of access in the target system. iOPEX heartbeat results confirm the credential exists and rotates — they do not confirm the application works. Only the App Owner can confirm end-to-end workflow. This gate cannot be bypassed programmatically.'],
      ['What is the rollback posture if a production wave fails?',
        'The source CyberArk vault remains fully operational until gate g13. At any point before g13, the migration is fully reversible — unfreeze the source, invalidate target credentials, restore from last-known-good state backup. After g13 (read-only), rollback requires Vault DR promotion and is a major incident.'],
      ['How is the migration service account itself secured and monitored?',
        'The <code>svc-migration</code> service account has scoped access only to Safes actively being migrated in the current wave. After each wave, its Safe membership is trimmed. CyberArk PTA monitors the account for anomalous activity. Any access outside normal migration hours or to out-of-scope Safes fires a PTA alert.'],
    ]],
  ];

  const risks = [
    ['Audit log discontinuity',           'HIGH',   'Enterprise Compliance',         'Agent 07 archives pre-migration; retain per policy'],
    ['Permission model loss (9 perms)',   'HIGH',   'Enterprise Security Architect', 'Agent 03 report — mandatory review at gate g3'],
    ['Permission escalation on mapping',  'HIGH',   'Enterprise Security Architect', 'Dual-control review — iOPEX cannot self-approve'],
    ['Conjur/Kubernetes re-architecture', 'HIGH',   'App Teams',                'PENDING_EXTERNAL_TEAM — outside automated scope'],
    ['PSM session recording loss',        'MEDIUM', 'Enterprise Compliance',         'Archive recordings before P7 decommission'],
    ['CCP/AAM re-point failures',         'MEDIUM', 'IOPEX_DELIVERY',           'Agent 06 code scan; app team sign-off per wave'],
    ['Keeper Gateway network exposure',   'LOW',    'Enterprise NOC/Infra',          'No inbound rules required; outbound HTTPS only'],
    ['TLS misconfiguration',              'LOW',    'IOPEX_DELIVERY',           'Pre-P1 cert validation; pentest pre-P5'],
  ];

  const sevColor = { HIGH: 'var(--red)', MEDIUM: 'var(--amber)', LOW: 'var(--green)' };

  el.innerHTML = `
    <div style="max-width:900px;margin:0 auto;">

      <!-- Header -->
      <div class="panel" style="margin-bottom:20px;padding:20px 24px;">
        <div style="font-size:0.65rem;font-family:var(--font-mono);color:var(--amber);text-transform:uppercase;letter-spacing:.08em;margin-bottom:6px;">SHIFT Engagement — Security Review</div>
        <div style="font-size:1.1rem;font-weight:700;color:var(--text-bright);margin-bottom:8px;">Security Deep Dive — Enterprise Security Architect Q&amp;A</div>
        <div style="font-size:0.72rem;color:var(--text-standard);line-height:1.7;">
          Security-focused questions and answers covering the full SHIFT platform deployment — encryption,
          authentication, network security, compliance (PCI-DSS, SOX), NHI/DevOps secrets, penetration testing,
          and operational security controls. Prepared for Enterprise Security Architect review.
        </div>
      </div>

      <!-- Q&A Sections -->
      ${sections.map(([cat, qas], i) => `
        <details class="panel" style="margin-bottom:12px;" open>
          <summary style="list-style:none;cursor:pointer;padding:14px 16px;display:flex;align-items:center;justify-content:space-between;">
            <div style="display:flex;align-items:center;gap:10px;">
              <span style="font-family:var(--font-mono);font-size:0.6rem;color:var(--amber);background:rgba(229,142,26,0.12);padding:2px 7px;border-radius:3px;">${String(i+1).padStart(2,'0')}</span>
              <span style="font-weight:700;color:var(--text-bright);font-size:0.78rem;">${cat}</span>
            </div>
            <span style="font-size:0.6rem;color:var(--text-muted);font-family:var(--font-mono);">${qas.length} Q&amp;A</span>
          </summary>
          <div style="padding:4px 16px 16px;">
            ${qas.map(([q, a]) => `
              <div style="margin-top:12px;border-left:3px solid var(--blue);padding:10px 14px;background:var(--bg-page);border-radius:0 6px 6px 0;">
                <div style="font-weight:700;color:var(--blue);font-size:0.7rem;margin-bottom:6px;">Q: ${q}</div>
                <div style="font-size:0.7rem;color:var(--text-standard);line-height:1.75;">${a}</div>
              </div>
            `).join('')}
          </div>
        </details>
      `).join('')}

      <!-- Risk Matrix -->
      <details class="panel" style="margin-bottom:12px;" open>
        <summary style="list-style:none;cursor:pointer;padding:14px 16px;display:flex;align-items:center;justify-content:space-between;">
          <div style="display:flex;align-items:center;gap:10px;">
            <span style="font-family:var(--font-mono);font-size:0.6rem;color:var(--red);background:rgba(192,48,48,0.12);padding:2px 7px;border-radius:3px;">RISK</span>
            <span style="font-weight:700;color:var(--text-bright);font-size:0.78rem;">Security Risk Summary — Sign-Off Matrix</span>
          </div>
          <span style="font-size:0.6rem;color:var(--text-muted);font-family:var(--font-mono);">8 ITEMS</span>
        </summary>
        <div style="padding:4px 16px 16px;">
          <table style="width:100%;border-collapse:collapse;font-size:0.68rem;margin-top:8px;">
            <thead>
              <tr style="font-family:var(--font-mono);font-size:0.6rem;color:var(--text-muted);text-transform:uppercase;letter-spacing:.04em;">
                <th style="text-align:left;padding:6px 10px;border-bottom:1px solid var(--border);">Risk</th>
                <th style="text-align:left;padding:6px 10px;border-bottom:1px solid var(--border);">Severity</th>
                <th style="text-align:left;padding:6px 10px;border-bottom:1px solid var(--border);">Owner</th>
                <th style="text-align:left;padding:6px 10px;border-bottom:1px solid var(--border);">Mitigation</th>
              </tr>
            </thead>
            <tbody>
              ${risks.map(([risk, sev, owner, mit]) =>
                '<tr style="border-bottom:1px solid var(--border);">'
                + '<td style="padding:7px 10px;color:var(--text-standard);">' + risk + '</td>'
                + '<td style="padding:7px 10px;"><span style="color:' + sevColor[sev] + ';font-weight:700;font-family:var(--font-mono);font-size:0.63rem;">' + sev + '</span></td>'
                + '<td style="padding:7px 10px;color:var(--cyan);font-family:var(--font-mono);font-size:0.63rem;">' + owner + '</td>'
                + '<td style="padding:7px 10px;color:var(--text-muted);">' + mit + '</td>'
                + '</tr>'
              ).join('')}
            </tbody>
          </table>
        </div>
      </details>

    </div>
  `;
}

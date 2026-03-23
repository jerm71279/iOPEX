/**
 * HELIX — Guide
 */

const GUIDE_SECTIONS = [
  {
    title: '1. The Problem — The Tangle',
    content: `
      <p>When a primary identity trigger fires — for example, a Date of Birth update in the DnP SQL database — a synchronisation cascade begins. This cascade should update all downstream systems: One View (broadband), SAF (Digital Identity), and Customer Hub (profile).</p>
      <p>In practice, the cascade frequently enters a <strong>Partial Success Trap</strong>: One View is updated successfully, but the cascade stalls before reaching SAF and Customer Hub. The result is a state of <strong>external inconsistency</strong> — One View holds the correct value, while SAF and Customer Hub hold stale data.</p>
      <p>This inconsistency is visible to customers: they may be unable to log in, unable to update their profile, or see incorrect data in their account. It also creates a <strong>Staff Response Bottleneck</strong> — operations teams must manually identify, diagnose, and correct these inconsistencies, which typically takes 2–4 hours per incident.</p>
      <p>This is "The Tangle" — a fragmented data synchronisation model that generates constant manual work and customer-visible failures.</p>
    `,
  },
  {
    title: '2. The Solution — Autonomous Healing Architecture',
    content: `
      <p>The Autonomous Healing Architecture adds an AI intelligence layer on top of the existing BT components. <strong>No changes are made to any existing system.</strong> The AI layer observes, intercepts, and heals — operating entirely at the event and API level.</p>
      <p>The core philosophy is <strong>"moving the tangle to the right"</strong> — using specialised agents to resolve discrepancies before they reach the customer, or immediately after they are detected, rather than waiting for a staff escalation.</p>
      <ul>
        <li><strong>Observability Agent:</strong> Monitors every cascade event. When a stall is detected, it captures the data delta and initiates autonomous re-orchestration within 30 seconds.</li>
        <li><strong>Resolution Agent:</strong> Executes targeted, field-level fixes to specific out-of-sync systems. No full resync. No risk of re-triggering race conditions.</li>
        <li><strong>Healing Agent:</strong> For complex, multi-field drift — orchestrates a full consistency scan and coordinated restoration across all 5 domains.</li>
        <li><strong>RPA Automation:</strong> After backend fix, restores application-layer access — clearing stale auth tokens and confirming the customer can log in.</li>
      </ul>
    `,
  },
  {
    title: '3. The Five Domains',
    content: `
      <ul>
        <li><strong>DnP SQL</strong> — Source of truth for identity data. Triggers cascade on updates (Date of Birth, name, address, etc.).</li>
        <li><strong>One View</strong> — Broadband database. First downstream target in the cascade. Typically succeeds.</li>
        <li><strong>SAF (Digital Identity)</strong> — Second downstream target. Most common point of cascade failure — the "stall point."</li>
        <li><strong>Customer Hub (MongoDB)</strong> — Profile store. Third downstream target. Also affected by cascade stalls; has no independent retry mechanism.</li>
        <li><strong>Excalibur</strong> — Mobile and BACS (debt collection) data. Operates on a separate sync pathway; typically not involved in the standard cascade failure pattern, but monitored for completeness.</li>
      </ul>
    `,
  },
  {
    title: '4. The Three Legacy Safety Nets',
    content: `
      <p>Three existing safeguards are preserved alongside the AI layer, providing defence-in-depth:</p>
      <ul>
        <li><strong>Heuristic Monitoring with Intentional Delay:</strong> Scheduled consistency checks every 15 minutes, with a 90-second intentional delay to allow normal async processing to complete before raising an alert. Catches failures the real-time AI layer may miss.</li>
        <li><strong>Customer Complaint Triggers:</strong> "Unable to login" reports from customers act as a secondary trigger, forcing immediate identity alignment. Ground-truth signal for user-visible failures.</li>
        <li><strong>Auditability:</strong> Every agent action is logged with a structured entry — field, old value, new value, target system, agent, and timestamp. SHA-256 hash chain for tamper-evidence. 90-day retention.</li>
      </ul>
    `,
  },
  {
    title: '5. Test Subjects',
    content: `
      <p>Two validation targets are pre-mapped for cross-system consistency testing:</p>
      <ul>
        <li><strong>Buck Barrow (BB-0042)</strong> — Identity update scenario. Date of Birth update in DnP SQL. Used to validate the standard cascade failure and AI resolution flow: DnP SQL → One View ✓ → SAF (stall) → Customer Hub (stall) → AI intercept → Resolution → Confirmed consistent.</li>
        <li><strong>Barbara Hershey (BH-0117)</strong> — Mobile SIM sequence update scenario. Validates the Excalibur + Customer Hub pathway and the Healing Agent's full-restoration flow. Used for more complex, multi-domain consistency checks.</li>
      </ul>
    `,
  },
  {
    title: '6. Team Ownership',
    content: `
      <ul>
        <li><strong>Neil (Solution Architect)</strong> — Technical design authority for the AI intelligence layer and system integration points.</li>
        <li><strong>Manoj (QA Manager)</strong> — Validation strategy, test subject management, and consistency verification framework.</li>
        <li><strong>Jiayi Zhang (Dev Manager)</strong> — Development delivery, agent implementation, and integration with BT systems.</li>
        <li><strong>Product Owners</strong> — Operational governance: define resolution SLAs, approve escalation thresholds, and manage the scope of autonomous action.</li>
        <li><strong>Data Agents</strong> — Maintain the data landscape model: field mappings, domain schemas, and consistency rules used by the agents.</li>
        <li><strong>Healer/Observer Role</strong> — Ongoing governance of the autonomous logic: review agent decisions, tune thresholds, and evolve the healing rules as the data landscape changes.</li>
      </ul>
    `,
  },
  {
    title: '7. Glossary',
    content: `
      <ul>
        <li><strong>Cascade:</strong> The sequence of synchronisation events triggered by a DnP SQL identity update — propagating to One View, SAF, and Customer Hub.</li>
        <li><strong>Partial Success Trap:</strong> The state where a cascade partially succeeds (One View updates) but stalls before completing (SAF and Customer Hub remain stale).</li>
        <li><strong>The Tangle:</strong> The accumulated state of inconsistency across the BT data estate caused by repeated Partial Success Traps — requiring staff intervention to resolve.</li>
        <li><strong>Data Delta:</strong> The structured change payload — { field, old value, new value, target systems } — captured by the Observability Agent and used by the Resolution Agent to apply a targeted fix.</li>
        <li><strong>Autonomous Healing:</strong> The end-to-end process of detecting, resolving, and confirming a data inconsistency without human intervention.</li>
        <li><strong>Staff Response Bottleneck:</strong> The current state where data inconsistencies require manual staff escalation to resolve — typically taking 2–4 hours per incident.</li>
        <li><strong>DnP SQL:</strong> BT's identity source-of-truth database. Upstream trigger point for all identity synchronisation cascades.</li>
        <li><strong>SAF:</strong> Single Authentication Framework — BT's Digital Identity system. Holds customer authentication state and identity attributes.</li>
        <li><strong>Excalibur:</strong> BT-internal delinquent account management and BACS debt collection platform. FCA-regulated under CONC.</li>
      </ul>
    `,
  },
];

function renderGuide() {
  const el = document.getElementById('guideContent');
  if (!el) return;

  el.innerHTML = GUIDE_SECTIONS.map((s, i) => `
    <div class="guide-section${i === 0 ? ' open' : ''}" id="guide-sec-${i}">
      <div class="guide-header" onclick="toggleGuideSection(${i})">
        <div class="guide-title">${s.title}</div>
        <div class="guide-arrow">&#x25B6;</div>
      </div>
      <div class="guide-body">
        <div class="guide-content">${s.content}</div>
      </div>
    </div>`).join('');
}

function toggleGuideSection(i) {
  const sec = document.getElementById(`guide-sec-${i}`);
  if (sec) sec.classList.toggle('open');
}

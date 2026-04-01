# Runbook P1 — Discovery, Gap Analysis & Permission Inventory
## CyberArk → KeeperPAM Migration | SHIFT System

**Scope:** Full source system discovery. Maps every safe, account, dependency, and NHI. Produces gap analysis and permission translation report.
**Duration:** 3–4 weeks
**Prerequisite:** P0 complete, all preflight checks passing.
**Who runs this:** iOPEX delivery engineer (supervised)

**Agent sequence:** `11-source-adapter` → `01-discovery` → `09-dependency-mapper` → `12-nhi-handler` → `02-gap-analysis` → `03-permissions`

---

## P1 Checklist

- [ ] Source adapter configured for CyberArk on-prem
- [ ] Full account discovery complete
- [ ] Dependency scan complete (IIS, services, tasks, Jenkins, scripts, configs)
- [ ] NHI classification complete
- [ ] Gap analysis report reviewed and signed off
- [ ] Permission translation report reviewed — flagged sensitive permissions approved
- [ ] Wave classification plan agreed

---

## Run P1 (Full Automated Sequence)

```bash
# Dry run first — no API writes, validates all connections
az containerapp exec \
  --name "$APP_NAME" --resource-group "$RG" \
  --command "python3 cli.py run P1 --dry-run"

# Review dry-run output, then run live
az containerapp exec \
  --name "$APP_NAME" --resource-group "$RG" \
  --command "python3 cli.py run P1"
```

The coordinator runs all 6 P1 agents in sequence. Each agent gates on the prior agent's output. Estimated wall time: 2–8 hours depending on account count and PVWA response times.

Monitor progress:
```bash
az containerapp exec \
  --name "$APP_NAME" --resource-group "$RG" \
  --command "python3 cli.py status"
```

---

## Run Agents Individually (if needed)

If the full P1 run fails mid-sequence, restart from the failed agent:

### Agent 11 — Source Adapter (Multi-Vendor)
Normalizes source data from CyberArk on-prem into the common migration format.

```bash
az containerapp exec \
  --name "$APP_NAME" --resource-group "$RG" \
  --command "python3 cli.py agent 11-source-adapter"
```

**What it does:**
- Authenticates to CyberArk PVWA
- Exports all safes and accounts in normalized format
- Handles pagination (batch size 1000)
- Output: raw account export saved to `output/state/raw/agent_11_source_adapter/`

**Verify:**
```bash
# Check raw export count
az containerapp exec \
  --name "$APP_NAME" --resource-group "$RG" \
  --command "python3 -c \"
import json
data = json.load(open('output/state/raw/agent_11_source_adapter/P1.json'))
print('Accounts exported:', len(data.get('accounts', [])))
print('Safes:', len(data.get('safes', [])))
\""
```

---

### Agent 01 — Discovery & Dependency Mapping
Enumerates all CyberArk safes and accounts. Detects NHIs via 3-signal method.

```bash
az containerapp exec \
  --name "$APP_NAME" --resource-group "$RG" \
  --command "python3 cli.py agent 01-discovery"
```

**What it does:**
- Calls `GET /Safes` — enumerates all accessible safes
- Calls `GET /Accounts` per safe — full account inventory
- NHI signal detection: platform type + name patterns + safe name patterns
- Dependency detection: calls CyberArk Applications API
- Output: discovery report at `output/reports/agent_01_discovery_P1.json`

**Verify:**
```bash
az containerapp exec \
  --name "$APP_NAME" --resource-group "$RG" \
  --command "cat output/reports/agent_01_discovery_P1.json | python3 -m json.tool | head -40"
```

Expected: `total_safes`, `total_accounts`, `nhi_count`, `dependency_count` populated.

---

### Agent 09 — Dependency Mapper
6-scanner infrastructure crawl. Finds everything that calls CyberArk credentials.

```bash
az containerapp exec \
  --name "$APP_NAME" --resource-group "$RG" \
  --command "python3 cli.py agent 09-dependency-mapper"
```

**What it does:**
- Scanner 1: IIS application pool identities and connection strings
- Scanner 2: Windows services using managed accounts
- Scanner 3: Scheduled tasks using CyberArk accounts
- Scanner 4: Jenkins credential references
- Scanner 5: Script files with hardcoded CyberArk references
- Scanner 6: Config files (XML, JSON, INI) with CyberArk URLs or AppIDs
- Output: dependency map at `output/reports/agent_09_dependency_mapper_P1.json`

**Requires:** Read access to client infrastructure. May require elevated credentials or remote WinRM access.

**Verify:**
```bash
az containerapp exec \
  --name "$APP_NAME" --resource-group "$RG" \
  --command "cat output/reports/agent_09_dependency_mapper_P1.json | python3 -m json.tool | grep -E 'total_|scanner'"
```

---

### Agent 12 — NHI Classification
Classifies all detected non-human identities into 7 subtypes with weighted scoring.

```bash
az containerapp exec \
  --name "$APP_NAME" --resource-group "$RG" \
  --command "python3 cli.py agent 12-nhi-handler"
```

**NHI subtypes classified:**
| Subtype | Example |
|---------|---------|
| ServiceAccount | `svc-iis-apppool` |
| APIKey | AWS access key |
| CertificateIdentity | TLS client cert |
| DatabaseCredential | `db-sa-prod` |
| CloudIdentity | Azure SP, GCP SA |
| PipelineCredential | Jenkins, GitHub Actions |
| AutomationCredential | Ansible, Terraform |

**Verify:**
```bash
az containerapp exec \
  --name "$APP_NAME" --resource-group "$RG" \
  --command "cat output/reports/agent_12_nhi_handler_P1.json | python3 -m json.tool | grep -E 'subtype|count|confidence'"
```

---

### Agent 02 — Gap Analysis
10-domain gap analysis mapped to PCI-DSS, NIST 800-53, HIPAA, SOX.

```bash
az containerapp exec \
  --name "$APP_NAME" --resource-group "$RG" \
  --command "python3 cli.py agent 02-gap-analysis"
```

**10 domains analyzed:**
1. Authentication & Access Control
2. Safe/Vault Structure Parity
3. Permission Model Compatibility
4. Platform/Record Type Coverage
5. NHI Migration Complexity
6. Integration Point Count
7. CPM/Rotation Policy Coverage
8. Audit Log Continuity
9. Compliance Control Gaps
10. Operational Readiness

**Output:** Gap analysis report at `output/reports/agent_02_gap_analysis_P1.json`

**Review the report:**
```bash
az containerapp exec \
  --name "$APP_NAME" --resource-group "$RG" \
  --command "cat output/reports/agent_02_gap_analysis_P1.json | python3 -m json.tool | python3 -c \"
import json, sys
data = json.load(sys.stdin)
for domain in data.get('gaps', []):
    risk = domain.get('risk_level', 'UNKNOWN')
    if risk in ('HIGH', 'CRITICAL'):
        print(f'[{risk}] {domain[\\\"domain\\\"]}: {domain[\\\"finding\\\"]}')
\""
```

**⚠ Any HIGH or CRITICAL gaps must be reviewed with the client before advancing to P2.**

---

### Agent 03 — Permission Mapping (P1 Analysis)
Maps all 22 CyberArk safe member permissions. Flags the 7 security-sensitive permissions.

```bash
az containerapp exec \
  --name "$APP_NAME" --resource-group "$RG" \
  --command "python3 cli.py agent 03-permissions"
```

**What it does in P1 (analysis only — no writes):**
- Calls `GET /Safes/{safe}/Members` for every safe
- Maps all 22 permissions per member
- Flags: `ManageSafe`, `ManageSafeMembers`, `AccessWithoutConfirmation`, `DeleteAccounts`, `UnlockAccounts`, `BackupSafe`, `SpecifyNextAccountContent`
- Output: permission inventory at `output/reports/agent_03_permissions_P1.json`

**Review flagged permissions:**
```bash
az containerapp exec \
  --name "$APP_NAME" --resource-group "$RG" \
  --command "cat output/reports/agent_03_permissions_P1.json | python3 -c \"
import json, sys
data = json.load(sys.stdin)
flagged = data.get('flagged_members', [])
print(f'Flagged members requiring review: {len(flagged)}')
for m in flagged[:10]:
    print(f'  Safe: {m[\\\"safe\\\"]} | Member: {m[\\\"member\\\"]} | Flags: {m[\\\"flagged_permissions\\\"]}')
\""
```

Flagged members require human review before P3 applies permissions to KeeperPAM vaults.

---

## P1 Output Files

| File | Contents |
|------|----------|
| `output/reports/agent_11_source_adapter_P1.json` | Normalized source export |
| `output/reports/agent_01_discovery_P1.json` | Full safe/account inventory |
| `output/reports/agent_09_dependency_mapper_P1.json` | Dependency map |
| `output/reports/agent_12_nhi_handler_P1.json` | NHI classification |
| `output/reports/agent_02_gap_analysis_P1.json` | Gap analysis with compliance mapping |
| `output/reports/agent_03_permissions_P1.json` | Permission inventory + flagged members |
| `output/logs/audit.jsonl` | SHA-256 hash-chained audit log |

---

## Wave Classification

After P1, classify accounts into migration waves for P4/P5:

| Wave | Tier | Criteria | Risk |
|------|------|----------|------|
| 1 | Test/Dev | Name matches: test, dev, sandbox, poc, lab, demo | LOW |
| 2 | Standard Users | Personal admin accounts, standard service accounts | MEDIUM |
| 3 | Infrastructure | Network, firewall, server admin accounts | HIGH |
| 4 | NHIs | All classified non-human identities | HIGH |
| 5 | Critical/Privileged | Domain admins, HSM keys, break-glass accounts | CRITICAL |

Document the wave plan and get client sign-off before P3.

---

## P1 Troubleshooting

| Issue | Cause | Fix |
|-------|-------|-----|
| Agent 01 fails with 403 | Service account missing safe membership | Add to all migration safes |
| Agent 09 returns 0 dependencies | No network path to client infra scanners | Configure WinRM / network access |
| Agent 12 NHI count unexpectedly low | Naming convention differs from patterns | Add custom patterns to `agent_config.json` |
| Agent 02 fails compliance mapping | Missing compliance framework config | Check `agent_config.json` → `compliance_frameworks` |
| State corruption mid-run | Container restart | Re-run from last successful agent; state auto-recovers |

---

## Yellow Checkpoint YC-P1

**Gate before advancing to P2. Requires:**
- [ ] Migration lead sign-off on gap analysis
- [ ] Security team review of flagged permissions
- [ ] Wave classification plan approved by client
- [ ] Account count confirmed against client's known inventory (within 5%)
- [ ] All HIGH/CRITICAL gaps documented with mitigation plan

```bash
# After approval, advance to P2
az containerapp exec \
  --name "$APP_NAME" --resource-group "$RG" \
  --command "python3 cli.py advance"
```

---

## Next Step

→ **[P2_staging.md](P2_staging.md)** — Platform plugin validation and full staging ETL run against KeeperPAM test tenant.

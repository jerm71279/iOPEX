# pam/common — Shared Library

Shared code used by both migration orchestrators. **Single source of truth.**

> Do not edit duplicates in `cyberark-migration/` or `secret-server-migration/` —
> those are symlinks that resolve here. All changes go in `common/` only.

---

## Contents

### `core/` — Framework Modules

| File | Purpose | Used By |
|------|---------|---------|
| `base.py` | AgentBase ABC + AgentResult | Both orchestrators |
| `state.py` | MigrationState — atomic writes, file locking, backup recovery | Both orchestrators |
| `logging.py` | AuditLogger — SHA-256 hash chain, SIEM-ready JSONL | Both orchestrators |
| `cyberark_client.py` | CyberArk PVWA REST client (source system) | Both orchestrators |
| `source_adapters.py` | Multi-vendor source adapters (BeyondTrust, HashiCorp, AWS, Azure, GCP, Okta) | Both orchestrators |

### `agents/` — Shared Agents

| Agent | Purpose | Used By |
|-------|---------|---------|
| `agent_01_discovery.py` | Discovery & Dependency Mapping | Both orchestrators |
| `agent_09_dependency_mapper.py` | Dependency Mapper (IIS, Windows services, Jenkins, scripts) | Both orchestrators |
| `agent_11_source_adapter.py` | Multi-Vendor Source Adapter | Both orchestrators |
| `agent_12_nhi_handler.py` | NHI Handler — 7 subtypes, weighted classification | Both orchestrators |

### `scripts/` — Shared CLI Tools

| Script | Purpose | Used By |
|--------|---------|---------|
| `ccp_code_scanner.py` | Scan codebases for CyberArk CCP/AAM calls | migration-assistant, consulting-agent |
| `code_converter.py` | Convert CCP code to new platform SDK | migration-assistant, consulting-agent |
| `generate_wrapper.py` | Generate PAM abstraction layer wrapper | migration-assistant, consulting-agent |

---

## How Symlinks Work

Each orchestrator's `core/` and `agents/` directories contain symlinks pointing here:

```
pam/cyberark-migration/core/base.py  →  ../../common/core/base.py
pam/secret-server-migration/core/base.py  →  ../../common/core/base.py
```

Python follows symlinks transparently — `from core.base import AgentBase` resolves correctly
in both orchestrators without any import path changes.

"""ETL batch tool — wraps Agent 04 with watchdog timer and frozen registry.

The most critical MCP tool: executes the 7-step ETL pipeline
(FREEZE → EXPORT → TRANSFORM → CREATE → IMPORT → HEARTBEAT → UNFREEZE)
with crash recovery protections:

  - FrozenAccountRegistry: persists frozen account IDs to disk
  - WatchdogManager: auto-unfreezes on timeout
  - Signal handlers: emergency unfreeze on SIGTERM/SIGINT
  - Emergency unfreeze tool: manual recovery

Pattern source: CyberArk migration/agents/agent_04_etl.py
"""

import logging
import sys
from pathlib import Path

from ..server import mcp, _get_state, _get_audit, _get_enforcer, _get_registry, _get_watchdog
from ..shared.config import PamMcpSettings
from ..shared.redaction import sanitize_response
from ..shared.phase_enforcer import PhaseEnforcementError

logger = logging.getLogger(__name__)
settings = PamMcpSettings()


@mcp.tool()
async def execute_etl_batch(
    wave: int,
    batch: int = 0,
    option: str = "b",
    dry_run: bool = True,
) -> dict:
    """Execute an ETL migration batch (Agent 04) with crash recovery.

    Runs the 7-step pipeline for a wave/batch of accounts:
    FREEZE → EXPORT → TRANSFORM → CREATE → IMPORT → HEARTBEAT → UNFREEZE

    Protected by:
      - Watchdog timer (auto-unfreeze on timeout)
      - Frozen account registry (persists to disk)
      - Signal handlers (emergency unfreeze on crash)

    Args:
        wave: Wave number (1-5).
        batch: Batch number within the wave (default: 0).
        option: Migration target — "a" or "b".
        dry_run: If True, simulate without making API calls (default: True).
    """
    state = _get_state()
    audit = _get_audit()
    enforcer = _get_enforcer()
    registry = _get_registry()
    watchdog = _get_watchdog()

    try:
        enforcer.validate("execute_etl_batch")
    except PhaseEnforcementError as exc:
        return {"error": str(exc)}

    batch_id = f"W{wave}B{batch}"
    phase = state.current_phase or "P4"

    # Check if batch already completed
    existing_status = state.get_batch_status(wave, batch)
    if existing_status == "completed" and not dry_run:
        return {
            "status": "skipped",
            "batch_id": batch_id,
            "reason": "Batch already completed",
        }

    audit.log("etl_batch_started", {
        "batch_id": batch_id,
        "wave": wave,
        "batch": batch,
        "option": option,
        "dry_run": dry_run,
        "phase": phase,
    })

    # Start watchdog (unless dry run)
    if not dry_run:
        watchdog.start(
            timeout_minutes=settings.watchdog_timeout_minutes,
            batch_id=batch_id,
        )
        state.update_batch(wave, batch, "in_progress")

    try:
        orch_path = str(Path(settings.orchestrator_path).resolve())
        if orch_path not in sys.path:
            sys.path.insert(0, orch_path)

        from agents import AGENT_REGISTRY
        import json

        agent_cls = AGENT_REGISTRY.get("04-etl")
        if agent_cls is None:
            return {"error": "Agent 04 not found in registry"}

        config_path = Path(orch_path) / "config.json"
        if not config_path.exists():
            config_path = Path(orch_path) / "config.example.json"
        config = json.loads(config_path.read_text()) if config_path.exists() else {}

        agent = agent_cls(config=config, state=state, dry_run=dry_run)

        # Hook into agent's freeze/unfreeze to track in registry
        if not dry_run:
            _patch_agent_freeze_tracking(agent, registry, wave, batch)

        result = agent.run(phase=phase, wave=wave, batch=batch)

        if not dry_run:
            watchdog.cancel()
            if result.status == "success":
                state.update_batch(wave, batch, "completed")
                state.complete_step(f"{phase}:04-etl:{batch_id}")
            else:
                state.update_batch(wave, batch, "failed", {
                    "error": getattr(result, "error", "unknown"),
                })

        audit.log("etl_batch_completed", {
            "batch_id": batch_id,
            "status": result.status,
            "dry_run": dry_run,
        })

        return sanitize_response({
            "status": result.status,
            "batch_id": batch_id,
            "wave": wave,
            "batch": batch,
            "dry_run": dry_run,
            "summary": result.summary if hasattr(result, "summary") else {},
        })

    except Exception as exc:
        logger.error("ETL batch %s failed: %s", batch_id, exc)

        # Emergency cleanup
        if not dry_run:
            watchdog.cancel()
            frozen_ids = registry.unfreeze_all()
            state.update_batch(wave, batch, "failed", {"error": str(exc)})
            state.record_error("04-etl", str(exc), {"batch_id": batch_id})
            audit.log("etl_batch_emergency_cleanup", {
                "batch_id": batch_id,
                "unfrozen": len(frozen_ids),
                "error": str(exc),
            })

        return {"error": f"ETL batch failed: {type(exc).__name__}", "batch_id": batch_id}


@mcp.tool()
async def get_batch_status(wave: int, batch: int = 0) -> dict:
    """Get the status of a specific ETL batch.

    Args:
        wave: Wave number (1-5).
        batch: Batch number within the wave.
    """
    state = _get_state()
    status = state.get_batch_status(wave, batch)
    registry = _get_registry()

    return {
        "batch_id": f"W{wave}B{batch}",
        "status": status or "not_started",
        "frozen_accounts": registry.count if registry else 0,
        "watchdog_active": _get_watchdog().is_active if _get_watchdog() else False,
    }


@mcp.tool()
async def emergency_unfreeze() -> dict:
    """Emergency: unfreeze ALL frozen CyberArk accounts immediately.

    Use this if the ETL pipeline is stuck or after a crash. Unfreezes
    accounts via PVWA API and clears the frozen registry.

    This tool is available in ANY phase.
    """
    audit = _get_audit()
    registry = _get_registry()
    watchdog = _get_watchdog()

    # Cancel watchdog
    if watchdog:
        watchdog.cancel()

    frozen_ids = list(registry.get_frozen_ids()) if registry else []

    if not frozen_ids:
        return {"status": "no_frozen_accounts", "message": "No accounts are currently frozen."}

    audit.log("emergency_unfreeze_requested", {
        "frozen_count": len(frozen_ids),
        "source": "mcp",
    })

    # Attempt PVWA unfreeze
    unfrozen = 0
    errors = []

    if settings.cyberark_base_url:
        try:
            orch_path = str(Path(settings.orchestrator_path).resolve())
            if orch_path not in sys.path:
                sys.path.insert(0, orch_path)

            from core.cyberark_client import CyberArkClient

            config = {
                "base_url": settings.cyberark_base_url,
                "auth_type": settings.cyberark_auth_type,
                "verify_ssl": settings.cyberark_verify_ssl,
                "timeout": settings.cyberark_timeout,
            }
            with CyberArkClient(config) as client:
                for acct_id in frozen_ids:
                    try:
                        client.enable_account_management(acct_id)
                        registry.unfreeze(acct_id)
                        unfrozen += 1
                    except Exception as exc:
                        errors.append(f"{acct_id}: {exc}")
        except Exception as exc:
            errors.append(f"PVWA connection failed: {exc}")
    else:
        # No PVWA configured — just clear registry
        registry.unfreeze_all()
        unfrozen = len(frozen_ids)
        errors.append("WARNING: PVWA not configured — registry cleared but accounts may still be frozen in CyberArk")

    audit.log("emergency_unfreeze_completed", {
        "unfrozen": unfrozen,
        "errors": len(errors),
    })

    return {
        "status": "completed",
        "unfrozen": unfrozen,
        "failed": len(errors),
        "errors": errors[:20],
        "remaining_frozen": registry.count if registry else 0,
    }


def _patch_agent_freeze_tracking(agent, registry, wave, batch):
    """Monkey-patch Agent 04's freeze/unfreeze to also track in the registry.

    Agent 04 maintains its own _frozen_accounts list in memory. This patch
    ensures the persistent FrozenAccountRegistry stays in sync.
    """
    original_freeze = getattr(agent, "_freeze_accounts", None)
    original_unfreeze = getattr(agent, "_unfreeze_accounts", None)

    if original_freeze:
        def patched_freeze(*args, **kwargs):
            result = original_freeze(*args, **kwargs)
            # Sync frozen accounts to registry
            for acct_id in getattr(agent, "_frozen_accounts", []):
                registry.freeze(
                    acct_id,
                    wave=wave,
                    batch=batch,
                    session_id=getattr(agent, "session_id", None),
                )
            return result
        agent._freeze_accounts = patched_freeze

    if original_unfreeze:
        def patched_unfreeze(*args, **kwargs):
            result = original_unfreeze(*args, **kwargs)
            # Clear registry on successful unfreeze
            registry.unfreeze_all()
            return result
        agent._unfreeze_accounts = patched_unfreeze

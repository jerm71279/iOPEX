"""CyberArk → Delinea Secret Server Migration Coordinator.

Sequences agent execution per phase, enforces human-in-the-loop gates,
and manages persistent state transitions. Uses signal handlers for
clean shutdown with state preservation.
"""

import argparse
import json
import logging
import os
import signal
import sys
from pathlib import Path

from core.state import MigrationState, PHASES, PHASE_NAMES
from core.logging import AuditLogger
from agents import AGENT_REGISTRY
from core.ml import is_ml_enabled
from core.ml.wave_learning_coordinator import WaveLearningCoordinator

logger = logging.getLogger(__name__)

# Agent execution order per phase
PHASE_SEQUENCE = {
    "P0": [],  # Manual environment setup
    "P1": [
        "11-source-adapter",       # G-01: Load from any vendor
        "01-discovery",
        "09-dependency-mapper",    # G-04: Map credential consumers
        "12-nhi-handler",          # G-03: Classify NHIs
        "02-gap-analysis",
        "03-permissions",
    ],
    "P2": [
        "13-platform-plugins",     # G-07: Validate/migrate templates
        "10-staging",              # G-08: Staging dry-run
    ],
    "P3": [
        "03-permissions",
        "14-onboarding",           # G-02: Onboard new apps
    ],
    "P4": ["04-etl", "05-heartbeat"],
    "P5": [
        "04-etl",
        "05-heartbeat",
        "06-integration",
        "14-onboarding",           # G-02: Production onboarding
        "07-compliance",
    ],
    "P6": [
        "15-hybrid-fleet",         # G-05: Mixed fleet management
        "05-heartbeat",
        "06-integration",
        "07-compliance",
    ],
    "P7": ["07-compliance"],
}


def _deep_merge(base: dict, override: dict) -> dict:
    """Recursively merge override into base."""
    merged = base.copy()
    for key, val in override.items():
        if key in merged and isinstance(merged[key], dict) and isinstance(val, dict):
            merged[key] = _deep_merge(merged[key], val)
        else:
            merged[key] = val
    return merged


class Coordinator:
    """Orchestrates the 15-agent Secret Server migration pipeline."""

    def __init__(self, config_path: str = "config.json", dry_run: bool = False):
        self.dry_run = dry_run

        # Load config
        config_file = Path(config_path)
        if config_file.exists():
            with open(config_file) as f:
                self.config = json.load(f)
        else:
            example = Path("config.example.json")
            if example.exists():
                with open(example) as f:
                    self.config = json.load(f)
                logger.warning("Using config.example.json — copy to config.json for real credentials")
            else:
                self.config = {}

        # Merge agent-specific config
        agent_config_file = Path("agent_config.json")
        if agent_config_file.exists():
            with open(agent_config_file) as f:
                agent_cfg = json.load(f)
            self.config = _deep_merge(self.config, agent_cfg)

        # Set up output directories
        output_dir = Path(self.config.get("output_dir", "./output"))
        output_dir.mkdir(parents=True, exist_ok=True)
        (output_dir / "logs").mkdir(exist_ok=True)
        (output_dir / "reports").mkdir(exist_ok=True)
        (output_dir / "state").mkdir(exist_ok=True)

        # Configure logging
        log_level = self.config.get("log_level", "INFO")
        logging.basicConfig(
            level=getattr(logging, log_level, logging.INFO),
            format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
        )

        # Initialize state and audit logger
        state_file = output_dir / "state" / "migration_state.json"
        self.state = MigrationState(str(state_file))
        self.logger = AuditLogger(
            agent_id="coordinator",
            output_dir=str(output_dir / "logs"),
            environment=self.config.get("environment", "dev"),
        )

        # Register signal handlers for clean shutdown
        signal.signal(signal.SIGTERM, self._signal_handler)
        signal.signal(signal.SIGINT, self._signal_handler)

    def _signal_handler(self, signum, frame):
        sig_name = signal.Signals(signum).name
        self.logger.log("emergency_shutdown", {"signal": sig_name})
        try:
            self.state.save()
        except Exception:
            pass

        print(f"\n  [!] Received {sig_name}. State saved. Exiting.")
        sys.exit(128 + signum)

    def start(self, migration_id: str):
        self.state.start_migration(migration_id)
        self.logger.log("migration_started", {"id": migration_id, "target": "Secret Server"})
        print(f"\nMigration '{migration_id}' started (CyberArk → Secret Server).")
        print(f"Current phase: P0 ({PHASE_NAMES['P0']})")
        print(f"Run 'python cli.py run P0' to begin.\n")

    def status(self):
        summary = self.state.summary()
        print("\n" + "=" * 60)
        print("  MIGRATION STATUS (CyberArk → Secret Server)")
        print("=" * 60)

        if summary["migration_id"] is None:
            print("  No active migration.")
            print("  Start one with: python cli.py start <id>")
            print("=" * 60 + "\n")
            return

        print(f"  Migration ID: {summary['migration_id']}")
        print(f"  Current Phase: {summary['current_phase'] or 'COMPLETE'} "
              f"({summary['phase_name']})")
        print(f"  Steps Completed: {summary['steps_completed']}")
        print(f"  Approvals: {summary['approvals']}")
        print(f"  Errors: {summary['errors']}")
        print()

        print("  PHASES:")
        for phase, status in summary["phases"].items():
            marker = {"completed": "[x]", "in_progress": "[>]", "pending": "[ ]"}.get(status, "[?]")
            name = PHASE_NAMES.get(phase, "")
            print(f"    {marker} {phase}: {name} — {status}")

        if summary.get("batches_tracked", 0) > 0:
            print(f"\n  Batches tracked: {summary['batches_tracked']}")

        print("=" * 60 + "\n")

    def run_phase(self, phase: str):
        current = self.state.current_phase

        if current is None:
            print("No active migration. Start one first.")
            return

        if phase != current:
            print(f"Cannot run {phase}: current phase is {current}.")
            print(f"Complete {current} first, or advance manually.")
            return

        agents_to_run = PHASE_SEQUENCE.get(phase, [])

        if not agents_to_run:
            print(f"\nPhase {phase} ({PHASE_NAMES.get(phase, '')}) has no automated agents.")
            print("This phase requires manual steps.")
            response = input("Mark phase as complete and advance? (yes/no): ").strip().lower()
            if response in ("yes", "y"):
                next_phase = self.state.advance_phase()
                if next_phase:
                    print(f"Advanced to {next_phase} ({PHASE_NAMES.get(next_phase, '')})")
                else:
                    print("Migration complete!")
            return

        print(f"\n{'='*60}")
        print(f"  PHASE {phase}: {PHASE_NAMES.get(phase, '')}")
        print(f"  Target: Delinea Secret Server")
        print(f"  Agents: {', '.join(agents_to_run)}")
        if self.dry_run:
            print(f"  MODE: DRY RUN (no real API calls)")
        print(f"{'='*60}\n")

        self.logger.log("phase_start", {"phase": phase, "agents": agents_to_run, "dry_run": self.dry_run})

        # ML model lifecycle for ETL/NHI phases
        wlc = None
        if phase in ("P4", "P5") and is_ml_enabled(self.config):
            wlc = WaveLearningCoordinator(self.state, self.logger, self.config)
            ml_status = wlc.pre_wave(int(phase[1]))
            print(f"  [ML] Models loaded: ETL={ml_status['etl_detector']}, NHI={ml_status['nhi_classifier']}")

        previous_result = {}
        all_passed = True

        for agent_key in agents_to_run:
            agent_class = AGENT_REGISTRY.get(agent_key)
            if agent_class is None:
                print(f"  [!] Unknown agent: {agent_key}")
                continue

            agent = agent_class(self.config, self.state, self.logger)

            # Inject ML models if available
            if wlc is not None:
                if hasattr(agent, 'set_anomaly_detector') and wlc.etl_detector:
                    agent.set_anomaly_detector(wlc.etl_detector)
                if hasattr(agent, 'set_ml_classifier') and wlc.nhi_classifier:
                    agent.set_ml_classifier(wlc.nhi_classifier)

            print(f"  [{agent.AGENT_ID}] Running preflight...")

            if self.dry_run:
                print(f"  [{agent.AGENT_ID}] DRY RUN — skipping actual execution")
                print(f"  [{agent.AGENT_ID}] Would run: preflight() -> run('{phase}', ...)")
                continue

            # Preflight
            preflight_result = agent.preflight()
            if not preflight_result.passed:
                print(f"  [{agent.AGENT_ID}] PREFLIGHT FAILED: {preflight_result.errors}")
                self.logger.log_error("preflight_failed", {
                    "agent": agent.AGENT_ID, "errors": preflight_result.errors,
                })
                all_passed = False
                break

            print(f"  [{agent.AGENT_ID}] Preflight passed. Executing...")

            # Run
            result = agent.run(phase, previous_result)

            if result.status == "failed":
                print(f"  [{agent.AGENT_ID}] FAILED: {result.errors}")
                self.logger.log_error("agent_failed", {
                    "agent": agent.AGENT_ID, "errors": result.errors,
                })
                all_passed = False
                break

            if result.needs_human:
                print(f"  [{agent.AGENT_ID}] Needs human approval.")

            previous_result = result.data
            print(f"  [{agent.AGENT_ID}] Complete. Status: {result.status}")
            if result.metrics:
                for k, v in result.metrics.items():
                    print(f"    {k}: {v}")

        # ML post-phase — retrain and save models
        if wlc is not None and all_passed:
            post_status = wlc.post_wave(int(phase[1]))
            self.logger.log("ml_post_phase", post_status)

        # Phase summary
        print(f"\n{'='*60}")
        if self.dry_run:
            print(f"  DRY RUN complete for {phase}")
        elif all_passed:
            print(f"  Phase {phase} complete. All agents passed.")

            # Run Agent 08 (Runbook) for gate management
            runbook_class = AGENT_REGISTRY.get("08-runbook")
            if runbook_class:
                runbook = runbook_class(self.config, self.state, self.logger)
                gate_result = runbook.run(phase, {})
                if gate_result.data.get("advanced_to"):
                    next_p = gate_result.data["advanced_to"]
                    print(f"  Advanced to {next_p} ({PHASE_NAMES.get(next_p, '')})")
                elif gate_result.status == "needs_approval":
                    print(f"  Phase {phase} gate requires approval.")
            else:
                response = input(f"\n  Advance to next phase? (yes/no): ").strip().lower()
                if response in ("yes", "y"):
                    next_phase = self.state.advance_phase()
                    if next_phase:
                        print(f"  Advanced to {next_phase}")
                    else:
                        print("  Migration complete!")
        else:
            print(f"  Phase {phase} had failures. Review errors above.")

        print(f"{'='*60}\n")

    def advance(self):
        current = self.state.current_phase
        if current is None:
            print("No active migration or already complete.")
            return
        next_phase = self.state.advance_phase()
        if next_phase:
            print(f"Advanced from {current} to {next_phase} ({PHASE_NAMES.get(next_phase, '')})")
        else:
            print("Migration complete! No more phases.")


def main():
    parser = argparse.ArgumentParser(description="CyberArk → Secret Server Migration Coordinator")
    parser.add_argument("--start", metavar="ID", help="Start a new migration with given ID")
    parser.add_argument("--resume", action="store_true", help="Resume current migration")
    parser.add_argument("--phase", metavar="P#", help="Run a specific phase (P0-P7)")
    parser.add_argument("--advance", action="store_true", help="Advance to next phase")
    parser.add_argument("--status", action="store_true", help="Show migration status")
    parser.add_argument("--dry-run", action="store_true", help="Simulate without real API calls")
    parser.add_argument("--config", default="config.json", help="Config file path")

    args = parser.parse_args()
    coordinator = Coordinator(config_path=args.config, dry_run=args.dry_run)

    if args.status:
        coordinator.status()
    elif args.start:
        coordinator.start(args.start)
    elif args.advance:
        coordinator.advance()
    elif args.phase:
        coordinator.run_phase(args.phase)
    elif args.resume:
        current = coordinator.state.current_phase
        if current:
            print(f"Resuming migration at phase {current}")
            coordinator.run_phase(current)
        else:
            print("No active migration to resume.")
    else:
        parser.print_help()


if __name__ == "__main__":
    main()

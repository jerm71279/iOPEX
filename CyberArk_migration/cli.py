#!/usr/bin/env python3
"""CLI entry point for the CyberArk PAM Migration system.

Provides a user-friendly command interface:
    python cli.py status           — Show migration status
    python cli.py start <id>       — Start new migration
    python cli.py run <phase>      — Run a phase
    python cli.py advance          — Advance to next phase
    python cli.py agent <id>       — Run a single agent
    python cli.py preflight        — Run all agent preflights
    python cli.py dry-run <phase>  — Simulate a phase
"""

import argparse
import json
import sys
from pathlib import Path

from coordinator import Coordinator
from core.state import MigrationState, PHASES, PHASE_NAMES
from core.logging import AuditLogger
from agents import AGENT_REGISTRY


def cmd_status(args):
    """Show migration status."""
    coord = Coordinator(config_path=args.config)
    coord.status()


def cmd_start(args):
    """Start a new migration."""
    coord = Coordinator(config_path=args.config)
    coord.start(args.migration_id)


def cmd_run(args):
    """Run a phase."""
    coord = Coordinator(config_path=args.config, dry_run=args.dry_run)
    coord.run_phase(args.phase)


def cmd_advance(args):
    """Advance to next phase."""
    coord = Coordinator(config_path=args.config)
    coord.advance()


def cmd_agent(args):
    """Run a single agent for the current phase."""
    coord = Coordinator(config_path=args.config)
    current = coord.state.current_phase

    if current is None:
        print("No active migration.")
        return

    agent_class = AGENT_REGISTRY.get(args.agent_id)
    if agent_class is None:
        print(f"Unknown agent: {args.agent_id}")
        print(f"Available agents: {', '.join(AGENT_REGISTRY.keys())}")
        return

    agent = agent_class(coord.config, coord.state, coord.logger)
    phase = args.phase or current

    print(f"Running {agent.AGENT_NAME} for phase {phase}...")

    preflight = agent.preflight()
    if not preflight.succeeded:
        print(f"Preflight failed: {preflight.errors}")
        return

    result = agent.run(phase, {})
    print(f"\nResult: {result.status}")
    if result.metrics:
        for k, v in result.metrics.items():
            print(f"  {k}: {v}")
    if result.errors:
        print(f"  Errors: {result.errors}")
    if result.next_action:
        print(f"  Next: {result.next_action}")


def cmd_preflight(args):
    """Run preflight checks for all agents."""
    coord = Coordinator(config_path=args.config)

    print("\n" + "=" * 60)
    print("  PREFLIGHT CHECKS")
    print("=" * 60 + "\n")

    for agent_key, agent_class in AGENT_REGISTRY.items():
        agent = agent_class(coord.config, coord.state, coord.logger)
        try:
            result = agent.preflight()
            status = "PASS" if result.succeeded else "FAIL"
            print(f"  [{status}] {agent.AGENT_NAME}")
            if result.errors:
                for err in result.errors:
                    print(f"         {err}")
        except Exception as e:
            print(f"  [ERR]  {agent.AGENT_NAME}: {e}")

    print("\n" + "=" * 60 + "\n")


def cmd_agents(args):
    """List all available agents."""
    print("\n  Available Agents:")
    print("  " + "-" * 50)
    for key, cls in AGENT_REGISTRY.items():
        print(f"  {key:20s}  {cls.AGENT_NAME}")
    print()


def main():
    parser = argparse.ArgumentParser(
        description="CyberArk PAM Migration CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python cli.py status                    Show migration status
  python cli.py start my-migration-001    Start new migration
  python cli.py run P1                    Run Phase 1 (Discovery)
  python cli.py run P1 --dry-run          Simulate Phase 1
  python cli.py advance                   Advance to next phase
  python cli.py agent 01-discovery        Run a single agent
  python cli.py preflight                 Run all preflight checks
  python cli.py agents                    List available agents
        """,
    )
    parser.add_argument("--config", default="config.json", help="Config file path")

    sub = parser.add_subparsers(dest="command")

    # status
    sub.add_parser("status", help="Show migration status")

    # start
    p_start = sub.add_parser("start", help="Start a new migration")
    p_start.add_argument("migration_id", help="Migration identifier")

    # run
    p_run = sub.add_parser("run", help="Run a migration phase")
    p_run.add_argument("phase", choices=PHASES, help="Phase to run (P0-P7)")
    p_run.add_argument("--dry-run", action="store_true", help="Simulate without API calls")

    # advance
    sub.add_parser("advance", help="Advance to next phase")

    # agent
    p_agent = sub.add_parser("agent", help="Run a single agent")
    p_agent.add_argument("agent_id", help="Agent key (e.g., 01-discovery)")
    p_agent.add_argument("--phase", help="Override phase (default: current)")

    # preflight
    sub.add_parser("preflight", help="Run all agent preflight checks")

    # agents (list)
    sub.add_parser("agents", help="List available agents")

    args = parser.parse_args()

    if args.command is None:
        parser.print_help()
        return

    commands = {
        "status": cmd_status,
        "start": cmd_start,
        "run": cmd_run,
        "advance": cmd_advance,
        "agent": cmd_agent,
        "preflight": cmd_preflight,
        "agents": cmd_agents,
    }

    cmd = commands.get(args.command)
    if cmd:
        cmd(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()

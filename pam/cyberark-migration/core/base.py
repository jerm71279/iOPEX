"""Agent base class and result dataclass for the migration framework."""

import sys
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


@dataclass
class AgentResult:
    """Universal output format returned by every agent."""

    status: str  # "success" | "failed" | "needs_approval" | "partial"
    data: Dict[str, Any] = field(default_factory=dict)
    errors: List[str] = field(default_factory=list)
    metrics: Dict[str, Any] = field(default_factory=dict)
    next_action: str = ""
    agent_id: str = ""
    phase: str = ""
    timestamp: str = ""

    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.now(timezone.utc).isoformat()
        # Validate status
        valid = ("success", "failed", "needs_approval", "partial")
        if self.status not in valid:
            raise ValueError(f"Invalid status '{self.status}', must be one of {valid}")

    def to_dict(self) -> dict:
        return asdict(self)

    @property
    def succeeded(self) -> bool:
        return self.status == "success"

    @property
    def passed(self) -> bool:
        """For preflight checks — only 'success' passes."""
        return self.status == "success"

    @property
    def partial_success(self) -> bool:
        return self.status in ("success", "partial")

    @property
    def needs_human(self) -> bool:
        return self.status == "needs_approval"


class AgentBase(ABC):
    """Abstract base class for all migration agents.

    Every agent implements:
      - preflight(): validate prerequisites
      - run(phase, input_data): execute agent logic

    The coordinator calls preflight() before run(). If preflight fails,
    run() is not called and the pipeline halts for human review.
    """

    AGENT_ID: str = "base"
    AGENT_NAME: str = "Base Agent"

    def __init__(self, config: dict, state, logger):
        self.config = config
        self.state = state
        self.logger = logger

    @abstractmethod
    def preflight(self) -> AgentResult:
        """Validate prerequisites before running."""

    @abstractmethod
    def run(self, phase: str, input_data: dict) -> AgentResult:
        """Execute agent logic for the given phase."""

    def requires_approval(
        self, gate_name: str, details: dict, timeout_minutes: int = 30
    ) -> bool:
        """Request human-in-the-loop approval with timeout.

        In non-interactive mode (no tty), defaults to deny (fail-safe).
        Times out after timeout_minutes and denies.
        """
        self.logger.log_human_review(
            gate=gate_name, details=details, approved=False, reviewer=None,
        )
        print(f"\n{'='*60}")
        print(f"  HUMAN APPROVAL REQUIRED: {gate_name}")
        print(f"  Agent: {self.AGENT_NAME}")
        print(f"{'='*60}")
        for key, value in details.items():
            print(f"  {key}: {value}")
        print(f"{'='*60}")

        # Non-interactive mode: fail-safe deny
        if not sys.stdin.isatty():
            self.logger.log("approval_denied_non_interactive", {
                "gate": gate_name,
            })
            print("  [Non-interactive mode] Auto-denying approval.")
            return False

        deadline = time.time() + timeout_minutes * 60
        while time.time() < deadline:
            remaining = int((deadline - time.time()) / 60)
            try:
                response = input(
                    f"\n  Approve? (yes/no) [{remaining}m remaining]: "
                ).strip().lower()
            except EOFError:
                print("  [EOF] Auto-denying approval.")
                return False

            if response in ("yes", "y"):
                self.logger.log_human_review(
                    gate=gate_name, details=details, approved=True
                )
                return True
            elif response in ("no", "n"):
                self.logger.log_human_review(
                    gate=gate_name, details=details, approved=False
                )
                return False
            print("  Please enter 'yes' or 'no'.")

        print(f"  [TIMEOUT] Approval timed out after {timeout_minutes}m. Denying.")
        self.logger.log("approval_timeout", {"gate": gate_name})
        return False

    def _result(self, status: str, **kwargs) -> AgentResult:
        """Helper to build an AgentResult pre-filled with agent metadata."""
        return AgentResult(
            status=status,
            agent_id=self.AGENT_ID,
            phase=kwargs.pop("phase", ""),
            **kwargs,
        )

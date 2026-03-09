"""
In-memory state manager — makes the demo feel alive.

Tracks mutable agent/wave/gate statuses with cascading state transitions.
Gate approval triggers agent activation based on phase unlocks and blocked_by chains.
Resets to a mid-migration snapshot (P2 complete, P3 active).
"""

from backend.mock_data.data import AGENTS, GATES, WAVES

# Which phases each gate unlocks when approved
GATE_PHASE_UNLOCKS = {
    "g1": "p1",
    "g3": "p2",
    "g4": "p3",
    "g5": "p4",
    "g6": "p5",
    "g11": "p6",
    "g13": "p7",
}

# Phase → agent IDs that participate in that phase
PHASE_AGENTS = {
    "p0": [],
    "p1": ["11", "1", "9", "12", "2", "3"],
    "p2": ["13", "10"],
    "p3": ["3", "14"],
    "p4": ["4", "5"],
    "p5": ["4", "5", "6", "7", "12", "14"],
    "p6": ["5", "6", "7", "15"],
    "p7": ["7", "8"],
}


class ControlCenterState:
    """Mutable in-memory state for the control center demo."""

    def __init__(self):
        self.reset()

    def reset(self):
        """Reset to mid-migration snapshot: P0-P2 complete, P3 active."""
        # Agent statuses
        self.agent_status = {
            "11": "complete",    # P1 — Source Adapter
            "1":  "complete",    # P1 — Discovery
            "9":  "complete",    # P1 — Dependency Mapper
            "12": "complete",    # P1 — NHI Handler (also P5, but later)
            "2":  "complete",    # P1 — Gap Analysis
            "3":  "active",      # P1 done, P3 active — Permissions
            "13": "complete",    # P2 — Platform Plugins
            "10": "complete",    # P2 — Staging Validation
            "14": "pending",     # P3 — Onboarding (blocked by 3)
            "4":  "pending",     # P4-P5 — Migration Pipeline
            "5":  "pending",     # P4-P6 — Heartbeat
            "6":  "pending",     # P5-P6 — Integration
            "7":  "pending",     # P5-P7 — Compliance
            "8":  "pending",     # P7 — Runbook
            "15": "pending",     # P6 — Hybrid Fleet
            "sh1": "active",    # Cross-phase — Portal Builder
            "sh2": "active",    # Cross-phase — ICG
        }

        # Wave statuses
        self.wave_status = {
            "1": "pending",
            "2": "pending",
            "3": "pending",
            "4": "pending",
            "5": "pending",
        }

        # Gate statuses
        self._reset_gates()

        # Track which phases are unlocked
        self.unlocked_phases = {"p0", "p1", "p2", "p3"}

    def _reset_gates(self):
        """Reset gates to match mid-migration: g1-g4 passed, g5 active, rest pending."""
        passed = {"g1", "g2", "g3", "g4", "g15"}
        active = {"g5"}
        for gate in GATES:
            if gate["id"] in passed:
                gate["status"] = "passed"
            elif gate["id"] in active:
                gate["status"] = "active"
            else:
                gate["status"] = "pending"

    def get_agent_status(self, agent_id: str) -> str:
        return self.agent_status.get(agent_id, "pending")

    def get_wave_status(self, wave_id: str) -> str:
        return self.wave_status.get(wave_id, "pending")

    def phase_status(self, phase_id: str) -> str:
        """Compute phase status from agent statuses."""
        agent_ids = PHASE_AGENTS.get(phase_id, [])
        if not agent_ids:
            return "complete"  # P0 has no agents
        statuses = [self.agent_status.get(a, "pending") for a in agent_ids]
        if all(s == "complete" for s in statuses):
            return "complete"
        if any(s in ("active", "complete") for s in statuses):
            return "active"
        return "pending"

    def approve_gate(self, gate_id: str) -> dict:
        """Approve a gate and trigger cascading state changes."""
        gate = next((g for g in GATES if g["id"] == gate_id), None)
        if not gate:
            return {"error": f"Gate {gate_id} not found"}
        if gate["status"] == "passed":
            return {"status": "already_passed", "gate_id": gate_id}

        gate["status"] = "passed"
        activated = []

        # Activate next pending gate
        gate_idx = GATES.index(gate)
        next_gate_id = None
        if gate_idx + 1 < len(GATES):
            next_gate = GATES[gate_idx + 1]
            if next_gate["status"] == "pending":
                next_gate["status"] = "active"
                next_gate_id = next_gate["id"]

        # Unlock phase if this gate triggers one
        if gate_id in GATE_PHASE_UNLOCKS:
            phase = GATE_PHASE_UNLOCKS[gate_id]
            self.unlocked_phases.add(phase)
            activated = self._activate_ready_agents(phase)

        # Check if current active agents can now complete
        # (gate approval may unblock downstream work)
        self._check_completions()

        return {
            "status": "approved",
            "gate_id": gate_id,
            "next_gate": next_gate_id,
            "activated_agents": activated,
            "phases_unlocked": list(self.unlocked_phases),
        }

    def advance_agent(self, agent_id: str, new_status: str) -> dict:
        """Manually advance an agent's status."""
        if agent_id not in self.agent_status:
            return {"error": f"Agent {agent_id} not found"}
        if new_status not in ("pending", "active", "complete"):
            return {"error": f"Invalid status: {new_status}"}

        old_status = self.agent_status[agent_id]
        self.agent_status[agent_id] = new_status

        # If agent completed, check if blocked agents can now activate
        activated = []
        if new_status == "complete":
            activated = self._activate_blocked_dependents(agent_id)

        return {
            "agent_id": agent_id,
            "old_status": old_status,
            "new_status": new_status,
            "activated": activated,
        }

    def advance_wave(self, wave_id: str, new_status: str) -> dict:
        """Advance a wave's status."""
        if wave_id not in self.wave_status:
            return {"error": f"Wave {wave_id} not found"}
        old = self.wave_status[wave_id]
        self.wave_status[wave_id] = new_status
        return {"wave_id": wave_id, "old_status": old, "new_status": new_status}

    def _activate_ready_agents(self, phase_id: str) -> list:
        """Activate agents in a phase whose blockers are all complete."""
        activated = []
        for agent_id in PHASE_AGENTS.get(phase_id, []):
            if self.agent_status.get(agent_id) != "pending":
                continue
            agent_data = AGENTS.get(agent_id, {})
            blockers = agent_data.get("blocked_by", [])
            if all(self.agent_status.get(str(b), "pending") == "complete" for b in blockers):
                self.agent_status[agent_id] = "active"
                activated.append(agent_id)
        return activated

    def _activate_blocked_dependents(self, completed_agent_id: str) -> list:
        """When an agent completes, check if any pending agents can now activate."""
        activated = []
        completed_num = int(completed_agent_id) if completed_agent_id.isdigit() else None
        if completed_num is None:
            return activated

        for agent_id, agent_data in AGENTS.items():
            if self.agent_status.get(agent_id) != "pending":
                continue
            blockers = agent_data.get("blocked_by", [])
            if completed_num not in blockers:
                continue
            # Check if ALL blockers are now complete
            if all(self.agent_status.get(str(b), "pending") == "complete" for b in blockers):
                # Also check the agent's phase is unlocked
                for phase_id, agents in PHASE_AGENTS.items():
                    if agent_id in agents and phase_id in self.unlocked_phases:
                        self.agent_status[agent_id] = "active"
                        activated.append(agent_id)
                        break
        return activated

    def _check_completions(self):
        """Auto-complete agents that were waiting for gate approval."""
        # When g5 passes (P3→P4 unlock), agent 03 P3 work is implicitly approved
        # This is handled by the activate chain above
        pass

    def snapshot(self) -> dict:
        """Full state dump for debugging."""
        return {
            "agent_status": dict(self.agent_status),
            "wave_status": dict(self.wave_status),
            "gate_status": {g["id"]: g["status"] for g in GATES},
            "phase_status": {
                pid: self.phase_status(pid)
                for pid in ["p0", "p1", "p2", "p3", "p4", "p5", "p6", "p7"]
            },
            "unlocked_phases": sorted(self.unlocked_phases),
        }


# Singleton instance
state = ControlCenterState()

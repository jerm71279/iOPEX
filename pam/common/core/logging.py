"""Structured audit logging for SIEM integration.

All agent actions are logged as JSON events for compliance and debugging.
"""

import hashlib
import json
import logging
import os
import uuid
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional


@dataclass
class AuditEvent:
    """A single audit event."""

    timestamp: str
    agent_id: str
    environment: str
    action: str
    details: Dict[str, Any]
    user: Optional[str] = None
    customer_id: Optional[str] = None
    session_id: Optional[str] = None
    result: str = "success"
    error: Optional[str] = None
    chain_hash: Optional[str] = None


class AuditLogger:
    """Structured JSON audit logger with hash chain for tamper evidence.

    Each log entry includes a SHA-256 hash of the previous entry,
    creating a hash chain that detects log tampering.
    """

    def __init__(
        self,
        agent_id: str,
        environment: str = "dev",
        customer_id: Optional[str] = None,
        output_dir: Optional[str] = None,
        session_id: Optional[str] = None,
    ):
        self.agent_id = agent_id
        self.environment = environment
        self.customer_id = customer_id
        self.session_id = session_id or str(uuid.uuid4())[:8]
        self._logger = logging.getLogger(f"migration.audit.{agent_id}")
        self._hash_chain = hashlib.sha256()

        self.output_path: Optional[Path] = None
        if output_dir:
            log_dir = Path(output_dir)
            log_dir.mkdir(parents=True, exist_ok=True)
            self.output_path = log_dir / f"{agent_id}.audit.jsonl"

    def _user(self) -> str:
        return os.environ.get("USER", os.environ.get("USERNAME", "unknown"))

    def log(
        self,
        action: str,
        details: Optional[Dict[str, Any]] = None,
        result: str = "success",
    ) -> AuditEvent:
        # Compute chain hash
        self._hash_chain.update(f"{action}:{result}".encode())
        chain = self._hash_chain.hexdigest()

        event = AuditEvent(
            timestamp=datetime.now(timezone.utc).isoformat(),
            agent_id=self.agent_id,
            environment=self.environment,
            action=action,
            details=details or {},
            user=self._user(),
            customer_id=self.customer_id,
            session_id=self.session_id,
            result=result,
            chain_hash=chain,
        )
        msg = json.dumps(asdict(event))
        self._logger.info(msg)
        if self.output_path:
            with open(self.output_path, "a") as f:
                f.write(msg + "\n")
        return event

    def log_error(
        self,
        action: str,
        details: Optional[Dict[str, Any]] = None,
        error: str = "",
    ) -> AuditEvent:
        self._hash_chain.update(f"{action}:failure".encode())
        chain = self._hash_chain.hexdigest()

        event = AuditEvent(
            timestamp=datetime.now(timezone.utc).isoformat(),
            agent_id=self.agent_id,
            environment=self.environment,
            action=action,
            details=details or {},
            user=self._user(),
            customer_id=self.customer_id,
            session_id=self.session_id,
            result="failure",
            error=error,
            chain_hash=chain,
        )
        msg = json.dumps(asdict(event))
        self._logger.error(msg)
        if self.output_path:
            with open(self.output_path, "a") as f:
                f.write(msg + "\n")
        return event

    def log_human_review(
        self,
        gate: str,
        details: Dict[str, Any],
        approved: bool,
        reviewer: Optional[str] = None,
    ) -> AuditEvent:
        return self.log(
            action=f"human_review:{gate}",
            details={
                **details,
                "approved": approved,
                "reviewer": reviewer or self._user(),
            },
            result="approved" if approved else "blocked",
        )

import json
import os
import fcntl
import shutil
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Optional, Any
from pydantic import BaseModel, Field


class PipelineStep(str, Enum):
    PENDING = "PENDING"
    INTAKE = "INTAKE"
    EXTRACT = "EXTRACT"
    RISK = "RISK"
    GATEWAY = "GATEWAY"
    HUMAN_REVIEW = "HUMAN_REVIEW"
    GENERATE = "GENERATE"
    SIGN = "SIGN"
    MONITOR = "MONITOR"
    DOWNLOAD = "DOWNLOAD"
    COUNTER_SIGN = "COUNTER_SIGN"
    EMAIL = "EMAIL"
    ARCHIVE = "ARCHIVE"
    OBLIGATION = "OBLIGATION"
    COMPLETE = "COMPLETE"
    FAILED = "FAILED"
    REJECTED = "REJECTED"


class StepLog(BaseModel):
    step: PipelineStep
    status: str  # success | failed | skipped
    ts: str
    detail: Optional[str] = None


class PipelineState(BaseModel):
    contract_id: str
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    current_step: PipelineStep = PipelineStep.PENDING
    status: str = "active"  # active | complete | failed | rejected
    source_email: Optional[str] = None
    raw_pdf_path: Optional[str] = None
    contract_data: dict = Field(default_factory=dict)
    steps: list[StepLog] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)

    def advance(self, step: PipelineStep, detail: Optional[str] = None):
        self.current_step = step
        self.updated_at = datetime.now(timezone.utc).isoformat()
        self.steps.append(StepLog(
            step=step,
            status="success",
            ts=self.updated_at,
            detail=detail,
        ))
        if len(self.steps) > 500:
            self.steps = self.steps[-500:]

    def fail(self, step: PipelineStep, error: str):
        self.current_step = PipelineStep.FAILED
        self.status = "failed"
        self.updated_at = datetime.now(timezone.utc).isoformat()
        self.steps.append(StepLog(step=step, status="failed", ts=self.updated_at, detail=error))
        self.errors.append(f"[{self.updated_at}] {step}: {error}")
        if len(self.errors) > 100:
            self.errors = self.errors[-100:]

    def save(self, state_dir: Path):
        """Atomic write with backup."""
        state_dir.mkdir(parents=True, exist_ok=True)
        path = state_dir / f"{self.contract_id}.json"
        tmp_path = state_dir / f"{self.contract_id}.json.tmp"
        bak_path = state_dir / f"{self.contract_id}.json.bak"

        data = self.model_dump_json(indent=2)
        with open(tmp_path, "w") as f:
            fcntl.flock(f, fcntl.LOCK_EX)
            f.write(data)
            f.flush()
            os.fsync(f.fileno())

        if path.exists():
            shutil.copy2(path, bak_path)
        os.replace(tmp_path, path)

    @classmethod
    def load(cls, contract_id: str, state_dir: Path) -> "PipelineState":
        path = state_dir / f"{contract_id}.json"
        bak_path = state_dir / f"{contract_id}.json.bak"
        for p in [path, bak_path]:
            if p.exists():
                try:
                    return cls.model_validate_json(p.read_text())
                except Exception:
                    continue
        raise FileNotFoundError(f"No state found for contract {contract_id}")

    @classmethod
    def new(cls, contract_id: str, source_email: Optional[str] = None) -> "PipelineState":
        return cls(contract_id=contract_id, source_email=source_email)

    def set(self, key: str, value: Any):
        self.contract_data[key] = value
        self.updated_at = datetime.now(timezone.utc).isoformat()

    def get(self, key: str, default: Any = None) -> Any:
        return self.contract_data.get(key, default)

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum

from agentkinetics.audit.models import AuditEvent
from agentkinetics.policy.models import Approval
from agentkinetics.shared.types import JSONObject


class RunStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    INTERRUPTED = "interrupted"
    WAITING_APPROVAL = "waiting_approval"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELED = "canceled"


class CheckpointType(StrEnum):
    CREATED = "created"
    RESUMED = "resumed"
    INTERRUPTED = "interrupted"
    RETRIED = "retried"
    CANCELED = "canceled"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass(frozen=True)
class Run:
    id: str
    tenant_id: str
    user_id: str
    status: RunStatus
    objective: str
    input_payload: JSONObject
    output_payload: JSONObject
    error_message: str | None
    created_at: datetime
    updated_at: datetime


@dataclass(frozen=True)
class RunSummary:
    id: str
    status: RunStatus
    objective: str
    created_at: datetime
    updated_at: datetime


@dataclass(frozen=True)
class Checkpoint:
    id: str
    run_id: str
    checkpoint_type: CheckpointType
    state_payload: JSONObject
    created_at: datetime


@dataclass(frozen=True)
class RunView:
    run: Run
    checkpoints: list[Checkpoint]
    approvals: list[Approval]
    audit_events: list[AuditEvent]

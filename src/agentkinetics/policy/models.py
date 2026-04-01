from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum

from agentkinetics.shared.types import JSONObject


class PolicyDecision(StrEnum):
    ALLOW = "allow"
    DENY = "deny"
    REQUIRE_APPROVAL = "require_approval"


class ApprovalStatus(StrEnum):
    PENDING = "pending"
    APPROVED = "approved"
    DENIED = "denied"


@dataclass(frozen=True)
class Policy:
    id: str
    tenant_id: str
    policy_name: str
    policy_type: str
    config: JSONObject
    created_at: datetime


@dataclass(frozen=True)
class Approval:
    id: str
    run_id: str
    requested_by_user_id: str
    approved_by_user_id: str | None
    status: ApprovalStatus
    reason: str
    created_at: datetime
    decided_at: datetime | None

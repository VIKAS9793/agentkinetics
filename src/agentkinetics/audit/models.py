from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from agentkinetics.shared.types import JSONObject


@dataclass(frozen=True)
class AuditEvent:
    id: str
    tenant_id: str
    run_id: str | None
    actor_user_id: str | None
    event_type: str
    operation_id: str | None
    payload: JSONObject
    created_at: datetime

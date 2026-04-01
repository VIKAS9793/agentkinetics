from __future__ import annotations

from typing import Protocol

from agentkinetics.audit.models import AuditEvent
from agentkinetics.shared.types import JSONObject


class AuditSink(Protocol):
    def append_event(
        self,
        tenant_id: str,
        run_id: str | None,
        actor_user_id: str | None,
        event_type: str,
        payload: JSONObject,
        operation_id: str | None = None,
    ) -> AuditEvent:
        ...

    def list_events_for_run(self, run_id: str) -> list[AuditEvent]:
        ...

    def list_recent_events_for_tenant(self, tenant_id: str, limit: int) -> list[AuditEvent]:
        ...

    def find_event_by_operation_id(self, operation_id: str) -> AuditEvent | None:
        ...

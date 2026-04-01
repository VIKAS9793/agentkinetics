from __future__ import annotations

from agentkinetics.audit.models import AuditEvent
from agentkinetics.audit.ports import AuditSink
from agentkinetics.shared.types import JSONObject


class AuditService:
    def __init__(self, sink: AuditSink) -> None:
        self._sink = sink

    def record(
        self,
        tenant_id: str,
        run_id: str | None,
        actor_user_id: str | None,
        event_type: str,
        payload: JSONObject,
        operation_id: str | None = None,
    ) -> AuditEvent:
        return self._sink.append_event(
            tenant_id=tenant_id,
            run_id=run_id,
            actor_user_id=actor_user_id,
            event_type=event_type,
            payload=payload,
            operation_id=operation_id,
        )

    def timeline(self, run_id: str) -> list[AuditEvent]:
        return self._sink.list_events_for_run(run_id=run_id)

    def recent_for_tenant(self, tenant_id: str, limit: int = 50) -> list[AuditEvent]:
        return self._sink.list_recent_events_for_tenant(tenant_id=tenant_id, limit=limit)

    def find_by_operation_id(self, operation_id: str) -> AuditEvent | None:
        return self._sink.find_event_by_operation_id(operation_id=operation_id)

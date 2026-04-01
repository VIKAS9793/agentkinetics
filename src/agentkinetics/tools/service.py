from __future__ import annotations

from collections.abc import Callable

from agentkinetics.audit.service import AuditService
from agentkinetics.shared.errors import NotFoundError
from agentkinetics.shared.time import parse_timestamp, utc_now
from agentkinetics.shared.types import JSONObject
from agentkinetics.tools.models import ToolResult


class ToolService:
    def __init__(self, audit_service: AuditService) -> None:
        self._audit_service = audit_service
        self._handlers: dict[str, Callable[[JSONObject], JSONObject]] = {}

    def register(self, name: str, handler: Callable[[JSONObject], JSONObject]) -> None:
        self._handlers[name] = handler

    def execute(
        self,
        tenant_id: str,
        run_id: str,
        actor_user_id: str,
        tool_name: str,
        payload: JSONObject,
        operation_id: str,
    ) -> ToolResult:
        existing = self._audit_service.find_by_operation_id(operation_id=operation_id)
        if existing is not None:
            result_payload = existing.payload["result"]
            if not isinstance(result_payload, dict):
                raise NotFoundError("Stored tool result payload is malformed.")
            executed_at = existing.payload.get("executed_at")
            if not isinstance(executed_at, str):
                raise NotFoundError("Stored tool result timestamp is malformed.")
            return ToolResult(
                tool_name=tool_name,
                success=bool(existing.payload["success"]),
                output=result_payload,
                executed_at=parse_timestamp(executed_at),
            )
        handler = self._handlers.get(tool_name)
        if handler is None:
            raise NotFoundError(f"Tool '{tool_name}' is not registered.")
        result = ToolResult(
            tool_name=tool_name,
            success=True,
            output=handler(payload),
            executed_at=utc_now(),
        )
        self._audit_service.record(
            tenant_id=tenant_id,
            run_id=run_id,
            actor_user_id=actor_user_id,
            event_type="tool.executed",
            operation_id=operation_id,
            payload={
                "tool_name": tool_name,
                "input": payload,
                "result": result.output,
                "success": result.success,
                "executed_at": result.executed_at.isoformat().replace("+00:00", "Z"),
            },
        )
        return result

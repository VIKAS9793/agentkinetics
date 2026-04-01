from __future__ import annotations

from agentkinetics.memory.models import MemoryKind, MemoryRecord
from agentkinetics.memory.ports import MemoryRepository
from agentkinetics.shared.types import JSONObject


class MemoryService:
    def __init__(self, repository: MemoryRepository) -> None:
        self._repository = repository

    def store_memory(
        self,
        tenant_id: str,
        scope_type: str,
        scope_id: str,
        kind: MemoryKind,
        name: str,
        content: JSONObject,
    ) -> MemoryRecord:
        return self._repository.upsert_memory(
            tenant_id=tenant_id,
            scope_type=scope_type,
            scope_id=scope_id,
            kind=kind.value,
            name=name,
            content=content,
        )

    def list_memories(self, scope_type: str, scope_id: str) -> list[MemoryRecord]:
        return self._repository.list_memories(scope_type=scope_type, scope_id=scope_id)

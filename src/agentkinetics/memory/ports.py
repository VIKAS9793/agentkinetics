from __future__ import annotations

from typing import Protocol

from agentkinetics.memory.models import MemoryRecord
from agentkinetics.shared.types import JSONObject


class MemoryRepository(Protocol):
    def upsert_memory(
        self,
        tenant_id: str,
        scope_type: str,
        scope_id: str,
        kind: str,
        name: str,
        content: JSONObject,
    ) -> MemoryRecord:
        ...

    def list_memories(self, scope_type: str, scope_id: str) -> list[MemoryRecord]:
        ...

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum

from agentkinetics.shared.types import JSONObject


class MemoryKind(StrEnum):
    WORKING = "working"
    EPISODIC = "episodic"


@dataclass(frozen=True)
class MemoryRecord:
    id: str
    tenant_id: str
    scope_type: str
    scope_id: str
    kind: MemoryKind
    name: str
    content: JSONObject
    created_at: datetime
    updated_at: datetime

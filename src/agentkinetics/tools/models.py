from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from agentkinetics.shared.types import JSONObject


@dataclass(frozen=True)
class ToolResult:
    tool_name: str
    success: bool
    output: JSONObject
    executed_at: datetime

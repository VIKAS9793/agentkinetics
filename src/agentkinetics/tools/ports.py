from __future__ import annotations

from typing import Protocol

from agentkinetics.shared.types import JSONObject
from agentkinetics.tools.models import ToolResult


class ToolExecutor(Protocol):
    def execute(self, tool_name: str, payload: JSONObject) -> ToolResult:
        ...

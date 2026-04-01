from __future__ import annotations

from typing import TypedDict

from agentkinetics.orchestration.ports import WorkflowEngine
from agentkinetics.shared.types import JSONObject


class WorkflowState(TypedDict, total=False):
    objective: str
    input_payload: dict[str, object]
    steps: list[str]


class LangGraphWorkflowEngine(WorkflowEngine):
    def build_initial_state(self, objective: str, input_payload: JSONObject) -> JSONObject:
        # WHY: LangGraph stays behind the orchestration boundary. Until the
        # dependency is installed, the rest of the system can still run against
        # the same internal workflow contract.
        try:
            from langgraph.graph import END, START, StateGraph  # type: ignore[import-not-found]
        except ImportError:
            return {
                "engine": "fallback-local",
                "objective": objective,
                "input_payload": input_payload,
                "steps": ["created"],
            }

        graph = StateGraph(WorkflowState)

        def created(state: WorkflowState) -> WorkflowState:
            return {
                "objective": state["objective"],
                "input_payload": state["input_payload"],
                "steps": ["created"],
            }

        graph.add_node("created", created)
        graph.add_edge(START, "created")
        graph.add_edge("created", END)
        compiled = graph.compile()
        result = compiled.invoke({"objective": objective, "input_payload": input_payload})
        if not isinstance(result, dict):
            return {
                "engine": "langgraph",
                "objective": objective,
                "input_payload": input_payload,
                "steps": ["created"],
            }
        state = {key: value for key, value in result.items()}
        state["engine"] = "langgraph"
        return state

    def build_resume_state(self, current_status: str, reason: str) -> JSONObject:
        return {
            "previous_status": current_status,
            "resume_reason": reason,
            "steps": ["resumed"],
        }

from __future__ import annotations

from typing import Protocol

from agentkinetics.orchestration.models import Checkpoint, Run, RunSummary
from agentkinetics.policy.models import Approval
from agentkinetics.shared.types import JSONObject


class RunRepository(Protocol):
    def create_run(
        self,
        tenant_id: str,
        user_id: str,
        objective: str,
        input_payload: JSONObject,
    ) -> Run:
        ...

    def get_run(self, run_id: str) -> Run | None:
        ...

    def list_runs(self, tenant_id: str, limit: int) -> list[RunSummary]:
        ...

    def update_run_status(
        self,
        run_id: str,
        status: str,
        output_payload: JSONObject | None = None,
        error_message: str | None = None,
    ) -> Run:
        ...

    def mark_run_waiting_and_create_approval(
        self,
        run_id: str,
        requested_by_user_id: str,
        reason: str,
    ) -> tuple[Run, Approval]:
        ...


class CheckpointStore(Protocol):
    def append_checkpoint(
        self,
        run_id: str,
        checkpoint_type: str,
        state_payload: JSONObject,
    ) -> Checkpoint:
        ...

    def list_checkpoints_for_run(self, run_id: str) -> list[Checkpoint]:
        ...


class WorkflowEngine(Protocol):
    def build_initial_state(self, objective: str, input_payload: JSONObject) -> JSONObject:
        ...

    def build_resume_state(self, current_status: str, reason: str) -> JSONObject:
        ...

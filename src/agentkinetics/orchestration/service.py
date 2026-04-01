from __future__ import annotations

from agentkinetics.audit.service import AuditService
from agentkinetics.orchestration.models import CheckpointType, Run, RunStatus, RunSummary, RunView
from agentkinetics.orchestration.ports import CheckpointStore, RunRepository, WorkflowEngine
from agentkinetics.policy.models import Approval, ApprovalStatus
from agentkinetics.policy.ports import ApprovalRepository, PolicyEvaluator
from agentkinetics.shared.errors import ConflictError, NotFoundError
from agentkinetics.shared.types import JSONObject


class OrchestrationService:
    def __init__(
        self,
        run_repository: RunRepository,
        checkpoint_store: CheckpointStore,
        approval_repository: ApprovalRepository,
        policy_evaluator: PolicyEvaluator,
        audit_service: AuditService,
        workflow_engine: WorkflowEngine,
    ) -> None:
        self._run_repository = run_repository
        self._checkpoint_store = checkpoint_store
        self._approval_repository = approval_repository
        self._policy_evaluator = policy_evaluator
        self._audit_service = audit_service
        self._workflow_engine = workflow_engine

    def create_run(
        self,
        tenant_id: str,
        user_id: str,
        objective: str,
        input_payload: JSONObject,
    ):
        run = self._run_repository.create_run(
            tenant_id=tenant_id,
            user_id=user_id,
            objective=objective,
            input_payload=input_payload,
        )
        initial_state = self._workflow_engine.build_initial_state(
            objective=objective,
            input_payload=input_payload,
        )
        self._checkpoint_store.append_checkpoint(
            run_id=run.id,
            checkpoint_type=CheckpointType.CREATED.value,
            state_payload=initial_state,
        )
        self._audit_service.record(
            tenant_id=tenant_id,
            run_id=run.id,
            actor_user_id=user_id,
            event_type="run.created",
            payload={"objective": objective, "input_payload": input_payload},
        )
        return run

    def resume_run(self, run_id: str, actor_user_id: str, reason: str):
        run = self._require_run(run_id)
        if run.status in {RunStatus.CANCELED, RunStatus.COMPLETED, RunStatus.FAILED}:
            raise ConflictError(f"Run in status '{run.status.value}' cannot be resumed.")
        self._policy_evaluator.assert_resume_allowed(run_id=run_id)
        updated = self._run_repository.update_run_status(
            run_id=run_id,
            status=RunStatus.RUNNING.value,
        )
        resume_state = self._workflow_engine.build_resume_state(
            current_status=run.status.value,
            reason=reason,
        )
        self._checkpoint_store.append_checkpoint(
            run_id=run_id,
            checkpoint_type=CheckpointType.RESUMED.value,
            state_payload=resume_state,
        )
        self._audit_service.record(
            tenant_id=run.tenant_id,
            run_id=run.id,
            actor_user_id=actor_user_id,
            event_type="run.resumed",
            payload={"reason": reason, "from_status": run.status.value},
        )
        return updated

    def interrupt_run(self, run_id: str, actor_user_id: str, reason: str):
        run = self._require_run(run_id)
        if run.status in {RunStatus.CANCELED, RunStatus.COMPLETED, RunStatus.FAILED}:
            raise ConflictError(f"Run in status '{run.status.value}' cannot be interrupted.")
        updated = self._run_repository.update_run_status(
            run_id=run_id,
            status=RunStatus.INTERRUPTED.value,
        )
        self._checkpoint_store.append_checkpoint(
            run_id=run_id,
            checkpoint_type=CheckpointType.INTERRUPTED.value,
            state_payload={"reason": reason},
        )
        self._audit_service.record(
            tenant_id=run.tenant_id,
            run_id=run.id,
            actor_user_id=actor_user_id,
            event_type="run.interrupted",
            payload={"reason": reason},
        )
        return updated

    def retry_run(self, run_id: str, actor_user_id: str, reason: str):
        run = self._require_run(run_id)
        # Note: We allow retrying FAILED runs, but not COMPLETED or CANCELED ones in this business logic.
        # However, for GAP-08/09 we should at least block COMPLETED/CANCELED.
        if run.status in {RunStatus.CANCELED, RunStatus.COMPLETED}:
            raise ConflictError(f"Run in status '{run.status.value}' cannot be retried.")
        updated = self._run_repository.update_run_status(
            run_id=run_id,
            status=RunStatus.PENDING.value,
            error_message=None,
        )
        self._checkpoint_store.append_checkpoint(
            run_id=run_id,
            checkpoint_type=CheckpointType.RETRIED.value,
            state_payload={"reason": reason},
        )
        self._audit_service.record(
            tenant_id=run.tenant_id,
            run_id=run.id,
            actor_user_id=actor_user_id,
            event_type="run.retried",
            payload={"reason": reason},
        )
        return updated

    def cancel_run(self, run_id: str, actor_user_id: str, reason: str):
        run = self._require_run(run_id)
        if run.status in {RunStatus.CANCELED, RunStatus.COMPLETED, RunStatus.FAILED}:
            raise ConflictError(f"Run in status '{run.status.value}' cannot be canceled.")
        updated = self._run_repository.update_run_status(
            run_id=run_id,
            status=RunStatus.CANCELED.value,
        )
        self._checkpoint_store.append_checkpoint(
            run_id=run_id,
            checkpoint_type=CheckpointType.CANCELED.value,
            state_payload={"reason": reason},
        )
        self._audit_service.record(
            tenant_id=run.tenant_id,
            run_id=run.id,
            actor_user_id=actor_user_id,
            event_type="run.canceled",
            payload={"reason": reason},
        )
        return updated

    def request_approval(
        self,
        run_id: str,
        actor_user_id: str,
        tenant_id: str,
        reason: str,
    ) -> tuple[Run, Approval]:
        run = self._require_run(run_id)

        if run.status in {RunStatus.COMPLETED, RunStatus.CANCELED, RunStatus.FAILED}:
            raise ConflictError(
                f"Run in status '{run.status.value}' cannot request approval."
            )

        existing_approvals = self._approval_repository.list_approvals_for_run(run_id=run_id)
        if existing_approvals and existing_approvals[-1].status == ApprovalStatus.PENDING:
            raise ConflictError("Run already has a pending approval request.")

        run, approval = self._run_repository.mark_run_waiting_and_create_approval(
            run_id=run_id,
            requested_by_user_id=actor_user_id,
            reason=reason,
        )
        self._audit_service.record(
            tenant_id=tenant_id,
            run_id=run.id,
            actor_user_id=actor_user_id,
            event_type="run.waiting_approval",
            payload={"reason": reason},
        )
        self._audit_service.record(
            tenant_id=tenant_id,
            run_id=run.id,
            actor_user_id=actor_user_id,
            event_type="approval.requested",
            payload={"approval_id": approval.id, "reason": reason},
        )
        return run, approval

    def get_run_view(self, run_id: str) -> RunView:
        run = self._require_run(run_id)
        checkpoints = self._checkpoint_store.list_checkpoints_for_run(run_id=run_id)
        approvals = self._approval_repository.list_approvals_for_run(run_id=run_id)
        audit_events = self._audit_service.timeline(run_id=run_id)
        return RunView(
            run=run,
            checkpoints=checkpoints,
            approvals=approvals,
            audit_events=audit_events,
        )

    def list_runs(self, tenant_id: str, limit: int) -> list[RunSummary]:
        return self._run_repository.list_runs(tenant_id=tenant_id, limit=limit)

    def _require_run(self, run_id: str):
        run = self._run_repository.get_run(run_id=run_id)
        if run is None:
            raise NotFoundError(f"Run '{run_id}' was not found.")
        return run

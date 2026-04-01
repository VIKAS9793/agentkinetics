from __future__ import annotations

from agentkinetics.audit.service import AuditService
from agentkinetics.policy.models import Approval, ApprovalStatus
from agentkinetics.policy.ports import ApprovalRepository, PolicyEvaluator
from agentkinetics.shared.errors import PolicyDeniedError


class PolicyService(PolicyEvaluator):
    def __init__(self, repository: ApprovalRepository, audit_service: AuditService) -> None:
        self._repository = repository
        self._audit_service = audit_service

    def decide_approval(
        self,
        approval_id: str,
        tenant_id: str,
        approved_by_user_id: str,
        approve: bool,
        reason: str,
    ) -> Approval:
        status = ApprovalStatus.APPROVED if approve else ApprovalStatus.DENIED
        approval = self._repository.decide_approval(
            approval_id=approval_id,
            approved_by_user_id=approved_by_user_id,
            status=status.value,
            reason=reason,
        )
        self._audit_service.record(
            tenant_id=tenant_id,
            run_id=approval.run_id,
            actor_user_id=approved_by_user_id,
            event_type="approval.decided",
            payload={
                "approval_id": approval.id,
                "status": approval.status.value,
                "reason": reason,
            },
        )
        return approval

    def assert_resume_allowed(self, run_id: str) -> None:
        approvals = self._repository.list_approvals_for_run(run_id=run_id)
        if not approvals:
            return
        latest = approvals[-1]
        if latest.status == ApprovalStatus.APPROVED:
            return
        if latest.status == ApprovalStatus.PENDING:
            raise PolicyDeniedError(
                "Run requires approval before it can resume.",
                policy_status="pending",
            )
        raise PolicyDeniedError(
            "Run resume was denied by policy.",
            policy_status="denied",
        )

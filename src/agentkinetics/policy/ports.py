from __future__ import annotations

from typing import Protocol

from agentkinetics.policy.models import Approval


class ApprovalRepository(Protocol):
    def decide_approval(
        self,
        approval_id: str,
        approved_by_user_id: str,
        status: str,
        reason: str,
    ) -> Approval:
        ...

    def list_approvals_for_run(self, run_id: str) -> list[Approval]:
        ...


class PolicyEvaluator(Protocol):
    def assert_resume_allowed(self, run_id: str) -> None:
        ...

from __future__ import annotations

from pathlib import Path

from agentkinetics.bootstrap import build_container
from agentkinetics.config import AppConfig
from agentkinetics.identity.models import Role
from agentkinetics.shared.errors import ConflictError, PolicyDeniedError


def build_test_container(tmp_path: Path):
    return build_container(
        config=AppConfig(
            database_path=tmp_path / "agentkinetics.sqlite3",
            artifacts_dir=tmp_path / "artifacts",
        )
    )


def test_replayable_timeline_and_checkpoints(tmp_path: Path) -> None:
    container = build_test_container(tmp_path=tmp_path)
    user = container.identity_service.create_local_user(
        username="operator",
        password="correct horse battery staple",
        display_name="Operator",
        role=Role.OPERATOR,
    )

    run = container.orchestration_service.create_run(
        tenant_id=user.tenant_id,
        user_id=user.id,
        objective="Run an offline-safe task.",
        input_payload={"offline": True},
    )
    container.orchestration_service.interrupt_run(
        run_id=run.id,
        actor_user_id=user.id,
        reason="Needs manual review.",
    )
    container.orchestration_service.retry_run(
        run_id=run.id,
        actor_user_id=user.id,
        reason="Retry after review.",
    )

    view = container.orchestration_service.get_run_view(run_id=run.id)
    assert [checkpoint.checkpoint_type.value for checkpoint in view.checkpoints] == [
        "created",
        "interrupted",
        "retried",
    ]
    assert [event.event_type for event in view.audit_events] == [
        "run.created",
        "run.interrupted",
        "run.retried",
    ]


def test_denied_approval_blocks_resume(tmp_path: Path) -> None:
    container = build_test_container(tmp_path=tmp_path)
    admin = container.identity_service.create_local_user(
        username="admin",
        password="correct horse battery staple",
        display_name="Administrator",
        role=Role.ADMIN,
    )
    operator = container.identity_service.create_local_user(
        username="operator",
        password="correct horse battery staple",
        display_name="Operator",
        role=Role.OPERATOR,
    )
    run = container.orchestration_service.create_run(
        tenant_id=admin.tenant_id,
        user_id=operator.id,
        objective="Needs approval",
        input_payload={},
    )
    _run, approval = container.orchestration_service.request_approval(
        run_id=run.id,
        actor_user_id=operator.id,
        tenant_id=admin.tenant_id,
        reason="Sensitive action requested.",
    )
    container.policy_service.decide_approval(
        approval_id=approval.id,
        tenant_id=admin.tenant_id,
        approved_by_user_id=admin.id,
        approve=False,
        reason="Policy denied the request.",
    )

    try:
        container.orchestration_service.resume_run(
            run_id=run.id,
            actor_user_id=operator.id,
            reason="Attempt to bypass denial.",
        )
    except PolicyDeniedError:
        pass
    else:
        raise AssertionError("Expected PolicyDeniedError when resuming denied run.")


def test_tool_execution_is_idempotent(tmp_path: Path) -> None:
    container = build_test_container(tmp_path=tmp_path)
    user = container.identity_service.create_local_user(
        username="builder",
        password="correct horse battery staple",
        display_name="Builder",
        role=Role.ADMIN,
    )
    run = container.orchestration_service.create_run(
        tenant_id=user.tenant_id,
        user_id=user.id,
        objective="Execute a deterministic tool",
        input_payload={},
    )

    container.tool_service.register("echo", lambda payload: {"echo": payload["value"]})
    first = container.tool_service.execute(
        tenant_id=user.tenant_id,
        run_id=run.id,
        actor_user_id=user.id,
        tool_name="echo",
        payload={"value": "hello"},
        operation_id="op_repeatable",
    )
    second = container.tool_service.execute(
        tenant_id=user.tenant_id,
        run_id=run.id,
        actor_user_id=user.id,
        tool_name="echo",
        payload={"value": "hello"},
        operation_id="op_repeatable",
    )

    assert first.output == {"echo": "hello"}
    assert second.output == first.output
    timeline = container.audit_service.timeline(run_id=run.id)
    assert [event.event_type for event in timeline] == ["run.created", "tool.executed"]


def test_request_approval_on_terminal_run_raises_conflict(tmp_path: Path) -> None:
    container = build_test_container(tmp_path=tmp_path)
    user = container.identity_service.create_local_user(
        username="admin",
        password="correct horse battery staple",
        display_name="Administrator",
        role=Role.ADMIN,
    )
    run = container.orchestration_service.create_run(
        tenant_id=user.tenant_id,
        user_id=user.id,
        objective="Will be canceled before approval requested.",
        input_payload={},
    )
    container.orchestration_service.cancel_run(
        run_id=run.id,
        actor_user_id=user.id,
        reason="Canceled by operator.",
    )

    try:
        container.orchestration_service.request_approval(
            run_id=run.id,
            actor_user_id=user.id,
            tenant_id=user.tenant_id,
            reason="Should fail.",
        )
    except ConflictError:
        pass
    else:
        raise AssertionError("Expected ConflictError when requesting approval on a canceled run.")


def test_request_approval_duplicate_pending_raises_conflict(tmp_path: Path) -> None:
    container = build_test_container(tmp_path=tmp_path)
    user = container.identity_service.create_local_user(
        username="admin",
        password="correct horse battery staple",
        display_name="Administrator",
        role=Role.ADMIN,
    )
    run = container.orchestration_service.create_run(
        tenant_id=user.tenant_id,
        user_id=user.id,
        objective="Test duplicate approval guard.",
        input_payload={},
    )
    container.orchestration_service.request_approval(
        run_id=run.id,
        actor_user_id=user.id,
        tenant_id=user.tenant_id,
        reason="First request.",
    )

    try:
        container.orchestration_service.request_approval(
            run_id=run.id,
            actor_user_id=user.id,
            tenant_id=user.tenant_id,
            reason="Second request — should fail.",
        )
    except ConflictError:
        pass
    else:
        raise AssertionError("Expected ConflictError on duplicate pending approval request.")


def test_resume_guard_blocks_run_with_pending_approval(tmp_path: Path) -> None:
    container = build_test_container(tmp_path=tmp_path)
    admin = container.identity_service.create_local_user(
        username="admin",
        password="correct horse battery staple",
        display_name="Administrator",
        role=Role.ADMIN,
    )
    operator = container.identity_service.create_local_user(
        username="operator",
        password="correct horse battery staple",
        display_name="Operator",
        role=Role.OPERATOR,
    )
    run = container.orchestration_service.create_run(
        tenant_id=admin.tenant_id,
        user_id=operator.id,
        objective="Resume guard must hold while approval is pending.",
        input_payload={},
    )
    container.orchestration_service.request_approval(
        run_id=run.id,
        actor_user_id=operator.id,
        tenant_id=admin.tenant_id,
        reason="Awaiting approval.",
    )

    try:
        container.orchestration_service.resume_run(
            run_id=run.id,
            actor_user_id=operator.id,
            reason="Should be blocked.",
        )
    except PolicyDeniedError:
        pass
    else:
        raise AssertionError("Expected PolicyDeniedError — resume guard must block pending approval.")

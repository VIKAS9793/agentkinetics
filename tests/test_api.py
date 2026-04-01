from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from agentkinetics.config import AppConfig
from agentkinetics.interfaces.api import create_app


def build_test_client(tmp_path: Path) -> TestClient:
    config = AppConfig(
        database_path=tmp_path / "agentkinetics.sqlite3",
        artifacts_dir=tmp_path / "artifacts",
    )
    app = create_app(config=config)
    return TestClient(app)


def test_create_run_resume_and_fetch(tmp_path: Path) -> None:
    client = build_test_client(tmp_path=tmp_path)

    create_user_response = client.post(
        "/auth/local/users",
        json={
            "username": "admin",
            "password": "correct horse battery staple",
            "display_name": "Administrator",
            "role": "admin",
        },
    )
    assert create_user_response.status_code == 201

    session_response = client.post(
        "/auth/local/sessions",
        json={
            "username": "admin",
            "password": "correct horse battery staple",
        },
    )
    assert session_response.status_code == 200
    assert session_response.json()["authenticated"] is True
    session_token = session_response.json()["session_token"]
    headers = {"X-Session-Token": session_token}

    create_run_response = client.post(
        "/runs",
        headers=headers,
        json={
            "objective": "Create a durable offline workflow.",
            "input_payload": {"priority": "high"},
        },
    )
    assert create_run_response.status_code == 200
    run_id = create_run_response.json()["run_id"]
    assert create_run_response.json()["status"] == "pending"

    list_runs_response = client.get(
        "/runs?limit=5",
        headers=headers,
    )
    assert list_runs_response.status_code == 200
    assert list_runs_response.json()["items"][0]["id"] == run_id

    resume_response = client.post(
        f"/runs/{run_id}/resume",
        headers={"X-Session-Token": session_token},
        json={"reason": "Operator approved continuation."},
    )
    assert resume_response.status_code == 200
    assert resume_response.json()["status"] == "running"

    fetch_response = client.get(
        f"/runs/{run_id}",
        headers={"X-Session-Token": session_token},
    )
    assert fetch_response.status_code == 200
    body = fetch_response.json()
    assert body["run"]["id"] == run_id
    assert body["run"]["status"] == "running"
    assert [checkpoint["type"] for checkpoint in body["checkpoints"]] == ["created", "resumed"]
    assert [event["type"] for event in body["audit_events"]] == ["run.created", "run.resumed"]


def test_favicon_route_exists(tmp_path: Path) -> None:
    client = build_test_client(tmp_path=tmp_path)

    response = client.get("/favicon.ico")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("image/svg+xml")
    assert "<svg" in response.text


def test_event_stream_route_exists(tmp_path: Path) -> None:
    client = build_test_client(tmp_path=tmp_path)

    client.post(
        "/auth/local/users",
        json={
            "username": "admin",
            "password": "correct horse battery staple",
            "display_name": "Administrator",
            "role": "admin",
        },
    )
    session_response = client.post(
        "/auth/local/sessions",
        json={
            "username": "admin",
            "password": "correct horse battery staple",
        },
    )
    assert session_response.json()["authenticated"] is True
    session_token = session_response.json()["session_token"]

    ticket_resp = client.post("/events/ticket", headers={"X-Session-Token": session_token})
    ticket = ticket_resp.json()["ticket"]

    response = client.get(f"/events/stream?ticket={ticket}&bootstrap_only=true")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")
    assert "event: ready" in response.text
    assert '"status": "connected"' in response.text


def test_event_stream_invalid_session_returns_auth_event(tmp_path: Path) -> None:
    client = build_test_client(tmp_path=tmp_path)

    response = client.get("/events/stream?ticket=stale-token&bootstrap_only=true")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")
    assert "event: auth" in response.text
    assert '"status": "invalid"' in response.text


def test_auth_session_route_returns_active_operator_context(tmp_path: Path) -> None:
    client = build_test_client(tmp_path=tmp_path)

    client.post(
        "/auth/local/users",
        json={
            "username": "admin",
            "password": "correct horse battery staple",
            "display_name": "Administrator",
            "role": "admin",
        },
    )
    session_response = client.post(
        "/auth/local/sessions",
        json={
            "username": "admin",
            "password": "correct horse battery staple",
        },
    )
    session_token = session_response.json()["session_token"]

    response = client.get(
        "/auth/session",
        headers={"X-Session-Token": session_token},
    )

    assert response.status_code == 200
    assert response.json()["authenticated"] is True
    assert response.json()["username"] == "admin"
    assert response.json()["display_name"] == "Administrator"
    assert response.json()["role"] == "admin"


def test_auth_session_route_returns_invalid_for_stale_token(tmp_path: Path) -> None:
    client = build_test_client(tmp_path=tmp_path)

    response = client.get(
        "/auth/session",
        headers={"X-Session-Token": "stale-token"},
    )

    assert response.status_code == 200
    assert response.json() == {"authenticated": False, "status": "invalid"}


def test_invalid_login_attempt_returns_401(tmp_path: Path) -> None:
    client = build_test_client(tmp_path=tmp_path)

    client.post(
        "/auth/local/users",
        json={
            "username": "admin",
            "password": "correct horse battery staple",
            "display_name": "Administrator",
            "role": "admin",
        },
    )

    response = client.post(
        "/auth/local/sessions",
        json={
            "username": "admin",
            "password": "wrong password",
        },
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid username or password."


def test_run_lifecycle_actions_and_approvals(tmp_path: Path) -> None:
    client = build_test_client(tmp_path=tmp_path)

    client.post(
        "/auth/local/users",
        json={
            "username": "admin",
            "password": "correct horse battery staple",
            "display_name": "Administrator",
            "role": "admin",
        },
    )
    session_response = client.post(
        "/auth/local/sessions",
        json={
            "username": "admin",
            "password": "correct horse battery staple",
        },
    )
    session_token = session_response.json()["session_token"]
    headers = {"X-Session-Token": session_token}

    create_run_response = client.post(
        "/runs",
        headers=headers,
        json={
            "objective": "Exercise the full run lifecycle.",
            "input_payload": {"mode": "test"},
        },
    )
    run_id = create_run_response.json()["run_id"]

    interrupt_response = client.post(
        f"/runs/{run_id}/interrupt",
        headers=headers,
        json={"reason": "Operator paused the run."},
    )
    assert interrupt_response.status_code == 200
    assert interrupt_response.json()["status"] == "interrupted"

    retry_response = client.post(
        f"/runs/{run_id}/retry",
        headers=headers,
        json={"reason": "Operator wants a clean retry."},
    )
    assert retry_response.status_code == 200
    assert retry_response.json()["status"] == "pending"

    approval_response = client.post(
        f"/runs/{run_id}/request-approval",
        headers=headers,
        json={"reason": "Sensitive action requires approval."},
    )
    assert approval_response.status_code == 200
    assert approval_response.json()["status"] == "waiting_approval"
    approval_id = approval_response.json()["approval_id"]

    decision_response = client.post(
        f"/approvals/{approval_id}/decide",
        headers=headers,
        json={"approve": True, "reason": "Approved for continuation."},
    )
    assert decision_response.status_code == 200
    assert decision_response.json()["status"] == "approved"

    resume_response = client.post(
        f"/runs/{run_id}/resume",
        headers=headers,
        json={"reason": "Approved continuation."},
    )
    assert resume_response.status_code == 200
    assert resume_response.json()["status"] == "running"

    cancel_response = client.post(
        f"/runs/{run_id}/cancel",
        headers=headers,
        json={"reason": "Operator closed the run."},
    )
    assert cancel_response.status_code == 200
    assert cancel_response.json()["status"] == "canceled"

    fetch_response = client.get(f"/runs/{run_id}", headers=headers)
    body = fetch_response.json()
    assert body["run"]["status"] == "canceled"
    assert [event["type"] for event in body["audit_events"]] == [
        "run.created",
        "run.interrupted",
        "run.retried",
        "run.waiting_approval",
        "approval.requested",
        "approval.decided",
        "run.resumed",
        "run.canceled",
    ]


def test_product_home_route_exists(tmp_path: Path) -> None:
    client = build_test_client(tmp_path=tmp_path)

    response = client.get("/")

    assert response.status_code == 200
    assert "AgentKinetics Workbench" in response.text
    assert "Create a bounded run" in response.text
    assert "Drive the selected workflow" in response.text
    assert "Request approval" in response.text


def test_login_rate_limit_enforced_with_429(tmp_path: Path) -> None:
    client = build_test_client(tmp_path=tmp_path)

    for _ in range(5):
        resp = client.post(
            "/auth/local/sessions",
            json={"username": "sys", "password": "x"},
        )
        assert resp.status_code == 401

    blocked_resp = client.post(
        "/auth/local/sessions",
        json={"username": "sys", "password": "x"},
    )
    assert blocked_resp.status_code == 429
    assert "Too many login attempts" in blocked_resp.json()["detail"]


def test_admin_endpoints_require_admin_role_returns_401(tmp_path: Path) -> None:
    client = build_test_client(tmp_path=tmp_path)

    client.post(
        "/auth/local/users",
        json={
            "username": "admin",
            "password": "correct horse battery staple",
            "display_name": "Administrator",
            "role": "admin",
        },
    )

    client.post(
        "/auth/local/users",
        headers={"X-Session-Token": "sys-token-which-wouldnt-work"},
        json={
            "username": "operator",
            "password": "correct password",
            "display_name": "Operator",
            "role": "operator",
        },
    )

    admin_session = client.post(
        "/auth/local/sessions",
        json={"username": "admin", "password": "correct horse battery staple"},
    ).json()

    client.post(
        "/auth/local/users",
        headers={"X-Session-Token": admin_session["session_token"]},
        json={
            "username": "operator",
            "password": "another password",
            "display_name": "Operator",
            "role": "operator",
        },
    )
    
    op_session = client.post(
        "/auth/local/sessions",
        json={"username": "operator", "password": "another password"},
    ).json()

    # Operator cannot access GET /admin
    op_admin_resp = client.get("/admin", headers={"X-Session-Token": op_session["session_token"]})
    assert op_admin_resp.status_code == 401
    
    # Admin CAN access GET /admin
    admin_admin_resp = client.get("/admin", headers={"X-Session-Token": admin_session["session_token"]})
    assert admin_admin_resp.status_code == 200

    # Operator cannot mint users
    op_mint_resp = client.post(
        "/auth/local/users",
        headers={"X-Session-Token": op_session["session_token"]},
        json={
            "username": "attacker",
            "password": "password123",
            "display_name": "Attacker",
            "role": "admin",
        },
    )
    assert op_mint_resp.status_code == 401


def test_policy_status_error(tmp_path: Path) -> None:
    client = build_test_client(tmp_path=tmp_path)
    client.post(
        "/auth/local/users",
        json={
            "username": "admin",
            "password": "correct horse battery staple",
            "display_name": "Administrator",
            "role": "admin",
        },
    )
    session_response = client.post(
        "/auth/local/sessions",
        json={
            "username": "admin",
            "password": "correct horse battery staple",
        },
    )
    session_token = session_response.json()["session_token"]
    headers = {"X-Session-Token": session_token}

    create_run_response = client.post(
        "/runs", headers=headers, json={"objective": "Test policy status", "input_payload": {}}
    )
    run_id = create_run_response.json()["run_id"]

    client.post(
        f"/runs/{run_id}/request-approval",
        headers=headers,
        json={"reason": "Sensitive action requires approval."},
    )

    resume_response = client.post(
        f"/runs/{run_id}/resume", headers=headers, json={"reason": "Approved continuation."}
    )

    # Should get a 409 Conflict mapped from PolicyDeniedError due to pending status
    assert resume_response.status_code == 409
    body = resume_response.json()
    assert body["detail"] == "Run requires approval before it can resume."
    assert body["policy_status"] == "pending"


def test_bootstrap_user_creation(tmp_path: Path) -> None:
    # Fresh client with no users in DB
    client = build_test_client(tmp_path=tmp_path)
    
    # Verify we can create the first user without a session token (bootstrap mode)
    response = client.post(
        "/auth/local/users",
        json={
            "username": "bootstrap_admin",
            "password": "Password123!",
            "display_name": "Bootstrap",
            "role": "admin",
        },
    )
    assert response.status_code == 201
    assert response.json()["username"] == "bootstrap_admin"
    
    # Second attempt should fail without a token because users now exist
    response2 = client.post(
        "/auth/local/users",
        json={
            "username": "second_user",
            "password": "Password123!",
            "display_name": "Second",
            "role": "admin",
        },
    )
    assert response2.status_code == 401


def test_user_creation_rate_limit(tmp_path: Path) -> None:
    client = build_test_client(tmp_path=tmp_path)
    
    # Bootstrap the first admin
    client.post(
        "/auth/local/users",
        json={
            "username": "main_admin",
            "password": "Password123!",
            "display_name": "Admin",
            "role": "admin",
        },
    )
    
    # Login to get admin token
    session_resp = client.post(
        "/auth/local/sessions",
        json={"username": "main_admin", "password": "Password123!"}
    )
    token = session_resp.json()["session_token"]
    headers = {"X-Session-Token": token}
    
    # Try creating users rapidly with admin authorization
    # Note: 1 slot already taken by 'main_admin' bootstrap
    for i in range(4):
        resp = client.post(
            "/auth/local/users",
            headers=headers,
            json={
                "username": f"user_{i}",
                "password": "Password123!",
                "display_name": f"User {i}",
                "role": "admin",
            },
        )
        assert resp.status_code == 201
        
    # The next should be rate limited (Total 6th attempt: 1 bootstrap + 4 success + 1 failure)
    response = client.post(
        "/auth/local/users",
        headers=headers,
        json={
            "username": "user_limit_exceeded",
            "password": "Password123!",
            "display_name": "Too Many",
            "role": "admin",
        },
    )
    assert response.status_code == 429
    assert response.json()["detail"] == "Too many user creation attempts. Please try again later."

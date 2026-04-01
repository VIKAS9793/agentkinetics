from __future__ import annotations

import asyncio
import json
import time
import uuid
from typing import Any

from agentkinetics.shared.rate_limit import SlidingWindowRateLimiter

from fastapi import Depends, FastAPI, Header, HTTPException, Query, Request
from fastapi.responses import HTMLResponse, JSONResponse, Response, StreamingResponse
from pydantic import BaseModel, ConfigDict, Field

from agentkinetics.bootstrap import AppContainer
from agentkinetics.config import AppConfig
from agentkinetics.identity.models import Role, SessionPrincipal
from agentkinetics.interfaces.product_ui import render_product_shell
from agentkinetics.shared.errors import ConflictError, DomainError, NotFoundError, PolicyDeniedError, UnauthorizedError
from agentkinetics.shared.time import to_iso8601
from agentkinetics.shared.logging import get_logger, log_context, set_trace_id
from fastapi.exceptions import RequestValidationError

logger = get_logger("api")


class CreateLocalUserRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    username: str = Field(min_length=3, max_length=64)
    password: str = Field(min_length=8, max_length=256)
    display_name: str = Field(min_length=1, max_length=128)
    role: Role = Role.ADMIN


class CreateSessionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    username: str
    password: str


class CreateRunRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    objective: str = Field(min_length=1, max_length=2048)
    input_payload: dict[str, Any] = Field(default_factory=dict)


class ResumeRunRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    reason: str = Field(min_length=1, max_length=1024)


class RunActionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    reason: str = Field(min_length=1, max_length=1024)


class DecideApprovalRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    approve: bool
    reason: str = Field(min_length=1, max_length=1024)


FAVICON_SVG = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64">
<defs>
  <linearGradient id="g" x1="0%" y1="0%" x2="100%" y2="100%">
    <stop offset="0%" stop-color="#7af6d6" />
    <stop offset="100%" stop-color="#2dd4bf" />
  </linearGradient>
</defs>
<rect width="64" height="64" rx="18" fill="#07131a" />
<path d="M16 19h13l7 9 12-14h0v12L36 42l-7-9H16z" fill="url(#g)" />
<circle cx="48" cy="18" r="6" fill="#f8b06d" />
</svg>"""


def _serialize_stream_event(event_type: str, event_id: str, payload: dict[str, object]) -> str:
    return f"id: {event_id}\nevent: {event_type}\ndata: {json.dumps(payload, sort_keys=True)}\n\n"


def _events_after_cursor(event_ids: list[str], cursor: str | None) -> int:
    if cursor is None:
        return 0
    try:
        return event_ids.index(cursor) + 1
    except ValueError:
        return 0


def _validate_payload_depth(payload: Any, max_depth: int = 10, current_depth: int = 0) -> None:
    if current_depth > max_depth:
        raise HTTPException(status_code=400, detail=f"Payload exceeds maximum allowed depth of {max_depth}")
    if isinstance(payload, dict):
        for value in payload.values():
            _validate_payload_depth(value, max_depth, current_depth + 1)
    elif isinstance(payload, list):
        for item in payload:
            _validate_payload_depth(item, max_depth, current_depth + 1)


def create_app(container: AppContainer | None = None, config: AppConfig | None = None) -> FastAPI:
    application_container = container
    if application_container is None:
        from agentkinetics.bootstrap import build_container

        application_container = build_container(config=config)

    app = FastAPI(title="AgentKinetics", version="0.1.0")
    app.state.container = application_container

    @app.middleware("http")
    async def deep_log_middleware(request: Request, call_next):
        trace_id = set_trace_id(request.headers.get("X-Trace-ID"))
        start_time = time.time()
        method = request.method
        url = str(request.url)
        path = request.url.path
        client_host = request.client.host if request.client else "unknown"

        with log_context(trace_id=trace_id, http_method=method, path=path, client=client_host):
            logger.info(
                "Incoming request",
                query=dict(request.query_params),
                has_session_token=bool(request.headers.get("X-Session-Token")),
                user_agent=request.headers.get("User-Agent"),
            )

            try:
                response = await call_next(request)
                duration = time.time() - start_time
                logger.info(
                    "Outgoing response",
                    status=response.status_code,
                    duration_ms=int(duration * 1000),
                )
                return response
            except Exception as exc:
                duration = time.time() - start_time
                logger.error(
                    "Request failed",
                    error=str(exc),
                    duration_ms=int(duration * 1000),
                    exc_info=True,
                )
                raise exc

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError):
        logger.warning(
            "Validation error",
            ledger_id="LDR-002" if request.url.path == "/runs" else None,
            method=request.method,
            url=str(request.url),
            query=dict(request.query_params),
            has_session_token=bool(request.headers.get("X-Session-Token")),
            errors=exc.errors(),
            body=await request.body() if request.method == "POST" else None,
        )
        return JSONResponse(
            status_code=422,
            content={"detail": exc.errors(), "body_received": "logged_to_trace"},
        )

    @app.exception_handler(DomainError)
    async def handle_domain_error(_, exc: DomainError) -> JSONResponse:
        if isinstance(exc, UnauthorizedError):
            status_code = 401
        elif isinstance(exc, NotFoundError):
            status_code = 404
        elif isinstance(exc, (ConflictError, PolicyDeniedError)):
            status_code = 409
        else:
            status_code = 400

        content: dict[str, str] = {"detail": str(exc)}
        if isinstance(exc, PolicyDeniedError):
            content["policy_status"] = exc.policy_status
        logger.warning(
            "Domain error handled",
            error_type=type(exc).__name__,
            detail=str(exc),
            status_code=status_code,
        )
            
        return JSONResponse(status_code=status_code, content=content)

    _sse_tickets: dict[str, tuple[str, float]] = {}
    
    # REM-07: Thread-safe sliding window rate limiters for auth endpoints.
    # 5 attempts per 60s per username for login; 5 creations per 60s for user registration.
    _auth_limiter = SlidingWindowRateLimiter(limit=5, window_seconds=60, name="auth_login")
    _create_user_limiter = SlidingWindowRateLimiter(limit=5, window_seconds=60, name="user_creation")

    def get_container() -> AppContainer:
        return app.state.container

    def require_principal(
        x_session_token: str = Header(alias="X-Session-Token"),
        current_container: AppContainer = Depends(get_container),
    ) -> SessionPrincipal:
        return current_container.identity_service.require_principal(session_token=x_session_token)

    def require_admin(
        principal: SessionPrincipal = Depends(require_principal),
    ) -> SessionPrincipal:
        if principal.role != Role.ADMIN:
            raise UnauthorizedError("Administrative privileges required.")
        return principal

    def require_admin_or_bootstrap(
        x_session_token: str | None = Header(default=None, alias="X-Session-Token"),
        current_container: AppContainer = Depends(get_container),
    ) -> SessionPrincipal | None:
        """
        Allows administrative access, or completely bypasses authentication IF the database is empty (bootstrap mode).
        """
        counts = current_container.gateway.counts()
        logger.debug(
            "Bootstrap access evaluation",
            ledger_id="LDR-001",
            counts=counts,
            has_session_token=bool(x_session_token),
        )
        if counts["users"] == 0:
            logger.info("Bootstrap mode granted", ledger_id="LDR-001")
            return None
            
        if not x_session_token:
            logger.warning("Bootstrap mode rejected due to missing session token", ledger_id="LDR-001")
            # If we have users, we MUST have a token.
            raise UnauthorizedError("Missing session token.")
            
        principal = current_container.identity_service.require_principal(session_token=x_session_token)
        if principal.role != Role.ADMIN:
            logger.warning(
                "Bootstrap mode rejected due to non-admin principal",
                ledger_id="LDR-001",
                user_id=principal.user_id,
                role=principal.role.value,
            )
            raise UnauthorizedError("Administrative privileges required.")
        return principal

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}
        return {"status": "ok"}

    @app.post("/events/ticket")
    def create_sse_ticket(
        principal: SessionPrincipal = Depends(require_principal),
        x_session_token: str = Header(alias="X-Session-Token"),
    ) -> dict[str, str]:
        ticket = str(uuid.uuid4())
        _sse_tickets[ticket] = (x_session_token, time.time() + 30.0)
        logger.info(
            "Issued SSE ticket",
            ledger_id="LDR-006",
            ticket=ticket,
            user_id=principal.user_id,
            session_id=principal.session_id,
            expires_in_seconds=30,
        )
        return {"ticket": ticket}

    @app.get("/events/stream")
    async def events_stream(
        request: Request,
        ticket: str = Query(min_length=1),
        bootstrap_only: bool = Query(default=False),
        current_container: AppContainer = Depends(get_container),
    ) -> StreamingResponse:
        try:
            ticket_data = _sse_tickets.pop(ticket, None)
            if not ticket_data or time.time() > ticket_data[1]:
                logger.warning(
                    "Rejected SSE stream ticket",
                    ledger_id="LDR-006",
                    ticket=ticket,
                    ticket_found=ticket_data is not None,
                )
                raise UnauthorizedError("Invalid or expired SSE ticket.")
            
            session_token = ticket_data[0]
            principal = current_container.identity_service.require_principal(session_token=session_token)
            logger.info(
                "Accepted SSE stream ticket",
                ledger_id="LDR-006",
                ticket=ticket,
                user_id=principal.user_id,
                session_id=principal.session_id,
            )
        except UnauthorizedError:
            async def invalid_session_iterator() -> object:
                yield _serialize_stream_event(
                    event_type="auth",
                    event_id="auth-invalid",
                    payload={"status": "invalid", "reason": "session_invalid"},
                )

            return StreamingResponse(
                invalid_session_iterator(),
                media_type="text/event-stream",
                headers={
                    "Cache-Control": "no-cache",
                    "Connection": "keep-alive",
                    "X-Accel-Buffering": "no",
                },
            )
        seed_events = current_container.audit_service.recent_for_tenant(
            tenant_id=principal.tenant_id,
            limit=50,
        )
        cursor = seed_events[-1].id if seed_events else None

        async def event_iterator() -> object:
            nonlocal cursor
            heartbeat_count = 0
            yield _serialize_stream_event(
                event_type="ready",
                event_id="ready",
                payload={"tenant_id": principal.tenant_id, "status": "connected"},
            )
            if bootstrap_only:
                return
            while True:
                if await request.is_disconnected():
                    break
                recent_events = current_container.audit_service.recent_for_tenant(
                    tenant_id=principal.tenant_id,
                    limit=50,
                )
                event_ids = [event.id for event in recent_events]
                start_index = _events_after_cursor(event_ids=event_ids, cursor=cursor)
                pending_events = recent_events[start_index:]
                if pending_events:
                    for event in pending_events:
                        cursor = event.id
                        yield _serialize_stream_event(
                            event_type="audit",
                            event_id=event.id,
                            payload={
                                "id": event.id,
                                "tenant_id": event.tenant_id,
                                "run_id": event.run_id,
                                "actor_user_id": event.actor_user_id,
                                "event_type": event.event_type,
                                "operation_id": event.operation_id,
                                "payload": event.payload,
                                "created_at": to_iso8601(event.created_at),
                            },
                        )
                    heartbeat_count = 0
                else:
                    heartbeat_count += 1
                    if heartbeat_count >= 15:
                        heartbeat_count = 0
                        yield ": keepalive\n\n"
                await asyncio.sleep(1.0)

        return StreamingResponse(
            event_iterator(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",
            },
        )

    @app.get("/auth/session")
    def get_session_context(
        x_session_token: str = Header(alias="X-Session-Token"),
        current_container: AppContainer = Depends(get_container),
    ) -> dict[str, Any]:
        try:
            session = current_container.identity_service.describe_session(session_token=x_session_token)
            counts = current_container.gateway.counts()
        except UnauthorizedError:
            logger.warning("Session context lookup failed", ledger_id="LDR-001")
            return {"authenticated": False, "status": "invalid"}
        logger.debug(
            "Session context resolved",
            user_id=session.user_id,
            role=session.role.value,
            counts=counts,
        )
        return {
            "authenticated": True,
            "session_id": session.session_id,
            "tenant_id": session.tenant_id,
            "user_id": session.user_id,
            "username": session.username,
            "display_name": session.display_name,
            "role": session.role.value,
            "metrics": counts,
        }

    @app.get("/", response_class=HTMLResponse)
    def product_home(current_container: AppContainer = Depends(get_container)) -> str:
        metrics = current_container.gateway.counts()
        return render_product_shell(initial_metrics=metrics)

    @app.get("/favicon.ico", include_in_schema=False)
    def favicon() -> Response:
        return Response(content=FAVICON_SVG, media_type="image/svg+xml")

    @app.get("/admin", response_class=HTMLResponse)
    def admin(
        principal: SessionPrincipal = Depends(require_admin),
        current_container: AppContainer = Depends(get_container),
    ) -> str:
        counts = current_container.gateway.counts()
        return (
            "<html><body>"
            "<h1>AgentKinetics Local Admin</h1>"
            f"<p>Tenants: {counts['tenants']}</p>"
            f"<p>Users: {counts['users']}</p>"
            f"<p>Runs: {counts['runs']}</p>"
            "</body></html>"
        )

    @app.post("/auth/local/users", status_code=201)
    def create_local_user(
        request_model: CreateLocalUserRequest,
        principal: SessionPrincipal | None = Depends(require_admin_or_bootstrap),
        current_container: AppContainer = Depends(get_container),
    ) -> dict[str, str]:
        counts_before = current_container.gateway.counts()
        logger.info(
            "Local user creation requested",
            ledger_id="LDR-001",
            username=request_model.username,
            role=request_model.role.value,
            bootstrap_mode=counts_before["users"] == 0,
            counts=counts_before,
        )
        # REM-07: Apply rate limiting to user creation. 
        # We use a fixed key to limit total creations across all usernames.
        if not _create_user_limiter.is_allowed("global_creation"):
             # For bootstrap or admin creation, we record failure to the system tenant.
            system_tenant = current_container.identity_service.ensure_default_tenant(
                name=current_container.config.default_tenant_name
            )
            current_container.audit_service.record(
                tenant_id=system_tenant.id,
                run_id=None,
                actor_user_id=principal.user_id if principal else None,
                event_type="auth.user_creation_blocked",
                payload={"username": request_model.username, "reason": "rate_limit"},
            )
            raise HTTPException(status_code=429, detail="Too many user creation attempts. Please try again later.")

        user = current_container.identity_service.create_local_user(
            username=request_model.username,
            password=request_model.password,
            display_name=request_model.display_name,
            role=request_model.role,
        )
        logger.info(
            "Local user creation succeeded",
            ledger_id="LDR-001",
            user_id=user.id,
            username=user.username,
            counts_after=current_container.gateway.counts(),
        )
        return {
            "user_id": user.id,
            "tenant_id": user.tenant_id,
            "username": user.username,
            "role": user.role.value,
        }

    @app.post("/auth/local/sessions")
    def create_session(
        request_model: CreateSessionRequest,
        current_container: AppContainer = Depends(get_container),
    ) -> dict[str, str | bool]:
        # Use the default tenant for authentication auditing before a session exists.
        system_tenant = current_container.identity_service.ensure_default_tenant(
            name=current_container.config.default_tenant_name
        )
        logger.info(
            "Login attempt received",
            username=request_model.username,
            ledger_id="LDR-003",
        )

        if not _auth_limiter.is_allowed(request_model.username):
            current_container.audit_service.record(
                tenant_id=system_tenant.id,
                run_id=None,
                actor_user_id=None,
                event_type="auth.login_blocked",
                payload={"username": request_model.username, "reason": "rate_limit"},
            )
            logger.warning(
                "Login attempt blocked by rate limiter",
                username=request_model.username,
                ledger_id="LDR-003",
            )
            raise HTTPException(status_code=429, detail="Too many login attempts. Please try again later.")

        try:
            session = current_container.identity_service.create_session(
                username=request_model.username,
                password=request_model.password,
            )
        except UnauthorizedError as exc:
            current_container.audit_service.record(
                tenant_id=system_tenant.id,
                run_id=None,
                actor_user_id=None,
                event_type="auth.login_failed",
                payload={"username": request_model.username},
            )
            logger.warning(
                "Login attempt failed",
                username=request_model.username,
                ledger_id="LDR-001",
            )
            raise exc

        session_context = current_container.identity_service.describe_session(session_token=session.token)
        logger.info(
            "Login attempt succeeded",
            username=session_context.username,
            user_id=session_context.user_id,
            ledger_id="LDR-001",
        )
        current_container.audit_service.record(
            tenant_id=session_context.tenant_id,
            run_id=None,
            actor_user_id=session_context.user_id,
            event_type="auth.login_success",
            payload={"session_id": session.id},
        )
        return {
            "authenticated": True,
            "session_id": session.id,
            "session_token": session.token,
            "expires_at": to_iso8601(session.expires_at),
            "username": session_context.username,
            "display_name": session_context.display_name,
            "role": session_context.role.value,
        }

    @app.post("/auth/session/logout")
    def logout(
        x_session_token: str = Header(alias="X-Session-Token"),
        principal: SessionPrincipal = Depends(require_principal),
        current_container: AppContainer = Depends(get_container),
    ) -> dict[str, bool]:
        current_container.identity_service.logout(session_token=x_session_token)
        return {"success": True}

    @app.post("/runs")
    def create_run(
        request_model: CreateRunRequest,
        principal: SessionPrincipal = Depends(require_principal),
        current_container: AppContainer = Depends(get_container),
    ) -> dict[str, str]:
        _validate_payload_depth(request_model.input_payload)
        run = current_container.orchestration_service.create_run(
            tenant_id=principal.tenant_id,
            user_id=principal.user_id,
            objective=request_model.objective,
            input_payload=request_model.input_payload,
        )
        return {"run_id": run.id, "status": run.status.value}

    @app.get("/runs")
    def list_runs(
        limit: int = Query(default=8, ge=1, le=50),
        principal: SessionPrincipal = Depends(require_principal),
        current_container: AppContainer = Depends(get_container),
    ) -> dict[str, object]:
        logger.info(
            "Run list requested",
            ledger_id="LDR-002",
            tenant_id=principal.tenant_id,
            user_id=principal.user_id,
            limit=limit,
        )
        items = current_container.orchestration_service.list_runs(
            tenant_id=principal.tenant_id,
            limit=limit,
        )
        logger.debug(
            "Run list resolved",
            ledger_id="LDR-002",
            tenant_id=principal.tenant_id,
            result_count=len(items),
        )
        return {
            "items": [
                {
                    "id": item.id,
                    "status": item.status.value,
                    "objective": item.objective,
                    "created_at": to_iso8601(item.created_at),
                    "updated_at": to_iso8601(item.updated_at),
                }
                for item in items
            ]
        }

    @app.post("/runs/{run_id}/resume")
    def resume_run(
        run_id: str,
        request_model: ResumeRunRequest,
        principal: SessionPrincipal = Depends(require_principal),
        current_container: AppContainer = Depends(get_container),
    ) -> dict[str, str]:
        run = current_container.orchestration_service.resume_run(
            run_id=run_id,
            actor_user_id=principal.user_id,
            reason=request_model.reason,
        )
        return {"run_id": run.id, "status": run.status.value}

    @app.post("/runs/{run_id}/interrupt")
    def interrupt_run(
        run_id: str,
        request_model: RunActionRequest,
        principal: SessionPrincipal = Depends(require_principal),
        current_container: AppContainer = Depends(get_container),
    ) -> dict[str, str]:
        run = current_container.orchestration_service.interrupt_run(
            run_id=run_id,
            actor_user_id=principal.user_id,
            reason=request_model.reason,
        )
        return {"run_id": run.id, "status": run.status.value}

    @app.post("/runs/{run_id}/retry")
    def retry_run(
        run_id: str,
        request_model: RunActionRequest,
        principal: SessionPrincipal = Depends(require_principal),
        current_container: AppContainer = Depends(get_container),
    ) -> dict[str, str]:
        run = current_container.orchestration_service.retry_run(
            run_id=run_id,
            actor_user_id=principal.user_id,
            reason=request_model.reason,
        )
        return {"run_id": run.id, "status": run.status.value}

    @app.post("/runs/{run_id}/cancel")
    def cancel_run(
        run_id: str,
        request_model: RunActionRequest,
        principal: SessionPrincipal = Depends(require_principal),
        current_container: AppContainer = Depends(get_container),
    ) -> dict[str, str]:
        run = current_container.orchestration_service.cancel_run(
            run_id=run_id,
            actor_user_id=principal.user_id,
            reason=request_model.reason,
        )
        return {"run_id": run.id, "status": run.status.value}

    @app.post("/runs/{run_id}/request-approval")
    def request_run_approval(
        run_id: str,
        request_model: RunActionRequest,
        principal: SessionPrincipal = Depends(require_principal),
        current_container: AppContainer = Depends(get_container),
    ) -> dict[str, str]:
        run, approval = current_container.orchestration_service.request_approval(
            run_id=run_id,
            actor_user_id=principal.user_id,
            tenant_id=principal.tenant_id,
            reason=request_model.reason,
        )
        return {
            "run_id": run.id,
            "status": run.status.value,
            "approval_id": approval.id,
            "approval_status": approval.status.value,
        }

    @app.post("/approvals/{approval_id}/decide")
    def decide_approval(
        approval_id: str,
        request_model: DecideApprovalRequest,
        principal: SessionPrincipal = Depends(require_principal),
        current_container: AppContainer = Depends(get_container),
    ) -> dict[str, str]:
        if principal.role != Role.ADMIN:
            raise UnauthorizedError("Only admin operators can decide approvals.")
        approval = current_container.policy_service.decide_approval(
            approval_id=approval_id,
            tenant_id=principal.tenant_id,
            approved_by_user_id=principal.user_id,
            approve=request_model.approve,
            reason=request_model.reason,
        )
        return {
            "approval_id": approval.id,
            "run_id": approval.run_id,
            "status": approval.status.value,
        }

    @app.get("/runs/{run_id}")
    def get_run(
        run_id: str,
        _: SessionPrincipal = Depends(require_principal),
        current_container: AppContainer = Depends(get_container),
    ) -> dict[str, object]:
        view = current_container.orchestration_service.get_run_view(run_id=run_id)
        return {
            "run": {
                "id": view.run.id,
                "tenant_id": view.run.tenant_id,
                "user_id": view.run.user_id,
                "status": view.run.status.value,
                "objective": view.run.objective,
                "input_payload": view.run.input_payload,
                "output_payload": view.run.output_payload,
                "error_message": view.run.error_message,
                "created_at": to_iso8601(view.run.created_at),
                "updated_at": to_iso8601(view.run.updated_at),
            },
            "checkpoints": [
                {
                    "id": checkpoint.id,
                    "type": checkpoint.checkpoint_type.value,
                    "state_payload": checkpoint.state_payload,
                    "created_at": to_iso8601(checkpoint.created_at),
                }
                for checkpoint in view.checkpoints
            ],
            "approvals": [
                {
                    "id": approval.id,
                    "status": approval.status.value,
                    "reason": approval.reason,
                    "requested_by_user_id": approval.requested_by_user_id,
                    "approved_by_user_id": approval.approved_by_user_id,
                    "created_at": to_iso8601(approval.created_at),
                    "decided_at": to_iso8601(approval.decided_at) if approval.decided_at else None,
                }
                for approval in view.approvals
            ],
            "audit_events": [
                {
                    "id": event.id,
                    "type": event.event_type,
                    "operation_id": event.operation_id,
                    "payload": event.payload,
                    "created_at": to_iso8601(event.created_at),
                }
                for event in view.audit_events
            ],
        }

    return app


# Support module-level app access for uvicorn agentkinetics.interfaces.api:app
app = create_app()

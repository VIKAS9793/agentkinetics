from __future__ import annotations

import json
import sqlite3
from datetime import datetime

from agentkinetics.audit.models import AuditEvent
from agentkinetics.identity.models import LocalIdentityRecord, Role, Session, Tenant, User
from agentkinetics.memory.models import MemoryKind, MemoryRecord
from agentkinetics.orchestration.models import Checkpoint, CheckpointType, Run, RunStatus, RunSummary
from agentkinetics.policy.models import Approval, ApprovalStatus
from agentkinetics.shared.errors import ConflictError, NotFoundError
from agentkinetics.shared.ids import new_id
from agentkinetics.shared.time import parse_timestamp, to_iso8601, utc_now
from agentkinetics.shared.types import JSONObject
from agentkinetics.storage.db import Database
from agentkinetics.shared.logging import get_logger

logger = get_logger("storage")


def _serialize(payload: JSONObject) -> str:
    return json.dumps(payload, sort_keys=True)


def _deserialize(raw: str) -> JSONObject:
    value = json.loads(raw)
    if not isinstance(value, dict):
        raise ValueError("Stored JSON payload is not an object.")
    return value


class SQLiteGateway:
    def __init__(self, database: Database) -> None:
        self._database = database

    def get_default_tenant(self) -> Tenant | None:
        logger.debug("Querying default tenant")
        with self._database.connection() as connection:
            row = connection.execute(
                "SELECT id, name, created_at FROM tenants ORDER BY created_at LIMIT 1"
            ).fetchone()
        if row is None:
            logger.debug("No default tenant found")
            return None
        return Tenant(
            id=str(row["id"]),
            name=str(row["name"]),
            created_at=parse_timestamp(str(row["created_at"])),
        )

    def create_default_tenant(self, name: str) -> Tenant:
        tenant_id = new_id("tenant")
        created_at = utc_now()
        logger.info("Creating default tenant", tenant_id=tenant_id, name=name)
        with self._database.connection() as connection:
            connection.execute(
                "INSERT INTO tenants (id, name, created_at) VALUES (?, ?, ?)",
                (tenant_id, name, to_iso8601(created_at)),
            )
        return Tenant(id=tenant_id, name=name, created_at=created_at)

    def create_user(
        self,
        tenant_id: str,
        username: str,
        display_name: str,
        role: str,
        password_hash: str,
        password_salt: str,
    ) -> User:
        user_id = new_id("user")
        created_at = utc_now()
        logger.info("Inserting user record", username=username, tenant_id=tenant_id)
        try:
            with self._database.connection() as connection:
                connection.execute(
                    """
                    INSERT INTO users (
                        id, tenant_id, username, display_name, password_hash,
                        password_salt, role, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        user_id,
                        tenant_id,
                        username,
                        display_name,
                        password_hash,
                        password_salt,
                        role,
                        to_iso8601(created_at),
                    ),
                )
        except sqlite3.IntegrityError as exc:
            logger.warning("DB Integrity Error during user creation", error=str(exc))
            if "UNIQUE constraint failed: users.username" in str(exc):
                raise ConflictError(f"Local user '{username}' already exists.") from exc
            raise ConflictError(f"Could not create user '{username}': {exc}") from exc
        except Exception as exc:  # noqa: BLE001
            logger.error("Unexpected DB Error during user creation", error=str(exc), exc_info=True)
            # Let other unexpected infrastructure failures bubble (handled by 500)
            raise exc
        return User(
            id=user_id,
            tenant_id=tenant_id,
            username=username,
            display_name=display_name,
            role=Role(role),
            created_at=created_at,
        )

    def get_local_identity_by_username(self, username: str) -> LocalIdentityRecord | None:
        logger.debug("Querying local identity by username", username=username)
        with self._database.connection() as connection:
            row = connection.execute(
                """
                SELECT id, tenant_id, username, display_name, role, created_at,
                       password_hash, password_salt
                FROM users
                WHERE username = ?
                """,
                (username,),
            ).fetchone()
        if row is None:
            logger.debug("Local identity not found", username=username)
            return None
        user = User(
            id=str(row["id"]),
            tenant_id=str(row["tenant_id"]),
            username=str(row["username"]),
            display_name=str(row["display_name"]),
            role=Role(str(row["role"])),
            created_at=parse_timestamp(str(row["created_at"])),
        )
        return LocalIdentityRecord(
            user=user,
            password_hash=str(row["password_hash"]),
            password_salt=str(row["password_salt"]),
        )

    def get_user_by_id(self, user_id: str) -> User | None:
        with self._database.connection() as connection:
            row = connection.execute(
                """
                SELECT id, tenant_id, username, display_name, role, created_at
                FROM users
                WHERE id = ?
                """,
                (user_id,),
            ).fetchone()
        if row is None:
            return None
        return User(
            id=str(row["id"]),
            tenant_id=str(row["tenant_id"]),
            username=str(row["username"]),
            display_name=str(row["display_name"]),
            role=Role(str(row["role"])),
            created_at=parse_timestamp(str(row["created_at"])),
        )

    def create_session(
        self,
        tenant_id: str,
        user_id: str,
        token: str,
        expires_at: datetime,
    ) -> Session:
        session_id = new_id("session")
        created_at = utc_now()
        logger.info(
            "Persisting session record",
            tenant_id=tenant_id,
            user_id=user_id,
            session_id=session_id,
            session_token_prefix=token[:8],
        )
        with self._database.connection() as connection:
            connection.execute(
                """
                INSERT INTO sessions (
                    id, tenant_id, user_id, token, expires_at, created_at, revoked_at
                ) VALUES (?, ?, ?, ?, ?, ?, NULL)
                """,
                (
                    session_id,
                    tenant_id,
                    user_id,
                    token,
                    to_iso8601(expires_at),
                    to_iso8601(created_at),
                ),
            )
        return Session(
            id=session_id,
            tenant_id=tenant_id,
            user_id=user_id,
            token=token,
            expires_at=expires_at,
            created_at=created_at,
            revoked_at=None,
        )

    def get_session_by_token(self, token: str) -> Session | None:
        logger.debug("Querying session by token", session_token_prefix=token[:8])
        with self._database.connection() as connection:
            row = connection.execute(
                """
                SELECT id, tenant_id, user_id, token, expires_at, created_at, revoked_at
                FROM sessions
                WHERE token = ?
                """,
                (token,),
            ).fetchone()
        if row is None:
            logger.warning("Session lookup missed", session_token_prefix=token[:8], ledger_id="LDR-006")
            return None
        revoked_at = row["revoked_at"]
        return Session(
            id=str(row["id"]),
            tenant_id=str(row["tenant_id"]),
            user_id=str(row["user_id"]),
            token=str(row["token"]),
            expires_at=parse_timestamp(str(row["expires_at"])),
            created_at=parse_timestamp(str(row["created_at"])),
            revoked_at=parse_timestamp(str(revoked_at)) if revoked_at is not None else None,
        )

    def revoke_session(self, token: str) -> None:
        now = to_iso8601(utc_now())
        logger.info("Revoking session record", session_token_prefix=token[:8], revoked_at=now)
        with self._database.connection() as connection:
            connection.execute(
                """
                UPDATE sessions
                SET revoked_at = ?
                WHERE token = ?
                """,
                (now, token),
            )

    def create_run(
        self,
        tenant_id: str,
        user_id: str,
        objective: str,
        input_payload: JSONObject,
    ) -> Run:
        run_id = new_id("run")
        created_at = utc_now()
        with self._database.connection() as connection:
            connection.execute(
                """
                INSERT INTO runs (
                    id, tenant_id, user_id, status, objective,
                    input_payload, output_payload, error_message,
                    created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, NULL, ?, ?)
                """,
                (
                    run_id,
                    tenant_id,
                    user_id,
                    RunStatus.PENDING.value,
                    objective,
                    _serialize(input_payload),
                    _serialize({}),
                    to_iso8601(created_at),
                    to_iso8601(created_at),
                ),
            )
        return Run(
            id=run_id,
            tenant_id=tenant_id,
            user_id=user_id,
            status=RunStatus.PENDING,
            objective=objective,
            input_payload=input_payload,
            output_payload={},
            error_message=None,
            created_at=created_at,
            updated_at=created_at,
        )

    def get_run(self, run_id: str) -> Run | None:
        with self._database.connection() as connection:
            row = connection.execute(
                """
                SELECT id, tenant_id, user_id, status, objective, input_payload,
                       output_payload, error_message, created_at, updated_at
                FROM runs
                WHERE id = ?
                """,
                (run_id,),
            ).fetchone()
        if row is None:
            return None
        return Run(
            id=str(row["id"]),
            tenant_id=str(row["tenant_id"]),
            user_id=str(row["user_id"]),
            status=RunStatus(str(row["status"])),
            objective=str(row["objective"]),
            input_payload=_deserialize(str(row["input_payload"])),
            output_payload=_deserialize(str(row["output_payload"])),
            error_message=str(row["error_message"]) if row["error_message"] is not None else None,
            created_at=parse_timestamp(str(row["created_at"])),
            updated_at=parse_timestamp(str(row["updated_at"])),
        )

    def list_runs(self, tenant_id: str, limit: int) -> list[RunSummary]:
        logger.debug("Querying run list", tenant_id=tenant_id, limit=limit, ledger_id="LDR-002")
        with self._database.connection() as connection:
            rows = connection.execute(
                """
                SELECT id, status, objective, created_at, updated_at
                FROM runs
                WHERE tenant_id = ?
                ORDER BY updated_at DESC
                LIMIT ?
                """,
                (tenant_id, limit),
            ).fetchall()
        logger.debug("Run list query complete", tenant_id=tenant_id, result_count=len(rows), ledger_id="LDR-002")
        return [
            RunSummary(
                id=str(row["id"]),
                status=RunStatus(str(row["status"])),
                objective=str(row["objective"]),
                created_at=parse_timestamp(str(row["created_at"])),
                updated_at=parse_timestamp(str(row["updated_at"])),
            )
            for row in rows
        ]

    def update_run_status(
        self,
        run_id: str,
        status: str,
        output_payload: JSONObject | None = None,
        error_message: str | None = None,
    ) -> Run:
        existing = self.get_run(run_id=run_id)
        if existing is None:
            raise NotFoundError(f"Run '{run_id}' was not found.")
        updated_at = utc_now()
        next_output = existing.output_payload if output_payload is None else output_payload
        with self._database.connection() as connection:
            connection.execute(
                """
                UPDATE runs
                SET status = ?, output_payload = ?, error_message = ?, updated_at = ?
                WHERE id = ?
                """,
                (
                    status,
                    _serialize(next_output),
                    error_message,
                    to_iso8601(updated_at),
                    run_id,
                ),
            )
        return Run(
            id=existing.id,
            tenant_id=existing.tenant_id,
            user_id=existing.user_id,
            status=RunStatus(status),
            objective=existing.objective,
            input_payload=existing.input_payload,
            output_payload=next_output,
            error_message=error_message,
            created_at=existing.created_at,
            updated_at=updated_at,
        )

    def append_checkpoint(
        self,
        run_id: str,
        checkpoint_type: str,
        state_payload: JSONObject,
    ) -> Checkpoint:
        checkpoint_id = new_id("checkpoint")
        created_at = utc_now()
        with self._database.connection() as connection:
            connection.execute(
                """
                INSERT INTO checkpoints (id, run_id, checkpoint_type, state_payload, created_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    checkpoint_id,
                    run_id,
                    checkpoint_type,
                    _serialize(state_payload),
                    to_iso8601(created_at),
                ),
            )
        return Checkpoint(
            id=checkpoint_id,
            run_id=run_id,
            checkpoint_type=CheckpointType(checkpoint_type),
            state_payload=state_payload,
            created_at=created_at,
        )

    def list_checkpoints_for_run(self, run_id: str) -> list[Checkpoint]:
        with self._database.connection() as connection:
            rows = connection.execute(
                """
                SELECT id, run_id, checkpoint_type, state_payload, created_at
                FROM checkpoints
                WHERE run_id = ?
                ORDER BY created_at
                """,
                (run_id,),
            ).fetchall()
        return [
            Checkpoint(
                id=str(row["id"]),
                run_id=str(row["run_id"]),
                checkpoint_type=CheckpointType(str(row["checkpoint_type"])),
                state_payload=_deserialize(str(row["state_payload"])),
                created_at=parse_timestamp(str(row["created_at"])),
            )
            for row in rows
        ]

    def upsert_memory(
        self,
        tenant_id: str,
        scope_type: str,
        scope_id: str,
        kind: str,
        name: str,
        content: JSONObject,
    ) -> MemoryRecord:
        # REM-04: Atomic upsert — one transaction, no TOCTOU window.
        # INSERT ... ON CONFLICT DO UPDATE executes atomically under a single write lock.
        # On conflict the existing id and created_at are preserved; only content and updated_at change.
        now = utc_now()
        memory_id = new_id("memory")

        with self._database.connection() as connection:
            connection.execute(
                """
                INSERT INTO memories (
                    id, tenant_id, scope_type, scope_id, kind,
                    name, content_payload, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(scope_type, scope_id, kind, name)
                DO UPDATE SET
                    content_payload = excluded.content_payload,
                    updated_at = excluded.updated_at
                """,
                (
                    memory_id,
                    tenant_id,
                    scope_type,
                    scope_id,
                    kind,
                    name,
                    _serialize(content),
                    to_iso8601(now),
                    to_iso8601(now),
                ),
            )
            # Fetch within the same connection/transaction for consistent post-upsert state.
            row = connection.execute(
                """
                SELECT id, created_at FROM memories
                WHERE scope_type = ? AND scope_id = ? AND kind = ? AND name = ?
                """,
                (scope_type, scope_id, kind, name),
            ).fetchone()

        return MemoryRecord(
            id=str(row["id"]),
            tenant_id=tenant_id,
            scope_type=scope_type,
            scope_id=scope_id,
            kind=MemoryKind(kind),
            name=name,
            content=content,
            created_at=parse_timestamp(str(row["created_at"])),
            updated_at=now,
        )

    def list_memories(self, scope_type: str, scope_id: str) -> list[MemoryRecord]:
        with self._database.connection() as connection:
            rows = connection.execute(
                """
                SELECT id, tenant_id, scope_type, scope_id, kind,
                       name, content_payload, created_at, updated_at
                FROM memories
                WHERE scope_type = ? AND scope_id = ?
                ORDER BY updated_at DESC
                """,
                (scope_type, scope_id),
            ).fetchall()
        return [
            MemoryRecord(
                id=str(row["id"]),
                tenant_id=str(row["tenant_id"]),
                scope_type=str(row["scope_type"]),
                scope_id=str(row["scope_id"]),
                kind=MemoryKind(str(row["kind"])),
                name=str(row["name"]),
                content=_deserialize(str(row["content_payload"])),
                created_at=parse_timestamp(str(row["created_at"])),
                updated_at=parse_timestamp(str(row["updated_at"])),
            )
            for row in rows
        ]

    def create_approval(self, run_id: str, requested_by_user_id: str, reason: str) -> Approval:
        approval_id = new_id("approval")
        created_at = utc_now()
        with self._database.connection() as connection:
            connection.execute(
                """
                INSERT INTO approvals (
                    id, run_id, requested_by_user_id, approved_by_user_id,
                    status, reason, created_at, decided_at
                ) VALUES (?, ?, ?, NULL, ?, ?, ?, NULL)
                """,
                (
                    approval_id,
                    run_id,
                    requested_by_user_id,
                    ApprovalStatus.PENDING.value,
                    reason,
                    to_iso8601(created_at),
                ),
            )
        return Approval(
            id=approval_id,
            run_id=run_id,
            requested_by_user_id=requested_by_user_id,
            approved_by_user_id=None,
            status=ApprovalStatus.PENDING,
            reason=reason,
            created_at=created_at,
            decided_at=None,
        )

    def mark_run_waiting_and_create_approval(
        self,
        run_id: str,
        requested_by_user_id: str,
        reason: str,
    ) -> tuple[Run, Approval]:
        existing = self.get_run(run_id=run_id)
        if existing is None:
            raise NotFoundError(f"Run '{run_id}' was not found.")

        approval_id = new_id("approval")
        updated_at = utc_now()
        created_at = updated_at

        with self._database.connection() as connection:
            connection.execute(
                """
                UPDATE runs
                SET status = ?, updated_at = ?
                WHERE id = ?
                """,
                (
                    RunStatus.WAITING_APPROVAL.value,
                    to_iso8601(updated_at),
                    run_id,
                ),
            )
            connection.execute(
                """
                INSERT INTO approvals (
                    id, run_id, requested_by_user_id, approved_by_user_id,
                    status, reason, created_at, decided_at
                ) VALUES (?, ?, ?, NULL, ?, ?, ?, NULL)
                """,
                (
                    approval_id,
                    run_id,
                    requested_by_user_id,
                    ApprovalStatus.PENDING.value,
                    reason,
                    to_iso8601(created_at),
                ),
            )

        run = Run(
            id=existing.id,
            tenant_id=existing.tenant_id,
            user_id=existing.user_id,
            status=RunStatus.WAITING_APPROVAL,
            objective=existing.objective,
            input_payload=existing.input_payload,
            output_payload=existing.output_payload,
            error_message=existing.error_message,
            created_at=existing.created_at,
            updated_at=updated_at,
        )
        approval = Approval(
            id=approval_id,
            run_id=run_id,
            requested_by_user_id=requested_by_user_id,
            approved_by_user_id=None,
            status=ApprovalStatus.PENDING,
            reason=reason,
            created_at=created_at,
            decided_at=None,
        )
        return run, approval

    def decide_approval(
        self,
        approval_id: str,
        approved_by_user_id: str,
        status: str,
        reason: str,
    ) -> Approval:
        with self._database.connection() as connection:
            existing = connection.execute(
                """
                SELECT id, run_id, requested_by_user_id, created_at, status
                FROM approvals
                WHERE id = ?
                """,
                (approval_id,),
            ).fetchone()
        if existing is None:
            raise NotFoundError(f"Approval '{approval_id}' was not found.")
        if str(existing["status"]) != ApprovalStatus.PENDING.value:
            raise ConflictError(f"Approval '{approval_id}' has already been decided.")
        decided_at = utc_now()
        with self._database.connection() as connection:
            connection.execute(
                """
                UPDATE approvals
                SET approved_by_user_id = ?, status = ?, reason = ?, decided_at = ?
                WHERE id = ?
                """,
                (
                    approved_by_user_id,
                    status,
                    reason,
                    to_iso8601(decided_at),
                    approval_id,
                ),
            )
        return Approval(
            id=str(existing["id"]),
            run_id=str(existing["run_id"]),
            requested_by_user_id=str(existing["requested_by_user_id"]),
            approved_by_user_id=approved_by_user_id,
            status=ApprovalStatus(status),
            reason=reason,
            created_at=parse_timestamp(str(existing["created_at"])),
            decided_at=decided_at,
        )

    def list_approvals_for_run(self, run_id: str) -> list[Approval]:
        with self._database.connection() as connection:
            rows = connection.execute(
                """
                SELECT id, run_id, requested_by_user_id, approved_by_user_id,
                       status, reason, created_at, decided_at
                FROM approvals
                WHERE run_id = ?
                ORDER BY created_at
                """,
                (run_id,),
            ).fetchall()
        return [
            Approval(
                id=str(row["id"]),
                run_id=str(row["run_id"]),
                requested_by_user_id=str(row["requested_by_user_id"]),
                approved_by_user_id=str(row["approved_by_user_id"]) if row["approved_by_user_id"] is not None else None,
                status=ApprovalStatus(str(row["status"])),
                reason=str(row["reason"]),
                created_at=parse_timestamp(str(row["created_at"])),
                decided_at=parse_timestamp(str(row["decided_at"])) if row["decided_at"] is not None else None,
            )
            for row in rows
        ]

    def append_event(
        self,
        tenant_id: str,
        run_id: str | None,
        actor_user_id: str | None,
        event_type: str,
        payload: JSONObject,
        operation_id: str | None = None,
    ) -> AuditEvent:
        event_id = new_id("audit")
        created_at = utc_now()
        try:
            with self._database.connection() as connection:
                connection.execute(
                    """
                    INSERT INTO audit_events (
                        id, tenant_id, run_id, actor_user_id, event_type,
                        operation_id, payload, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        event_id,
                        tenant_id,
                        run_id,
                        actor_user_id,
                        event_type,
                        operation_id,
                        _serialize(payload),
                        to_iso8601(created_at),
                    ),
                )
        except sqlite3.IntegrityError as exc:
            if "UNIQUE constraint failed: audit_events.operation_id" in str(exc):
                raise ConflictError("Duplicate audit operation ID.") from exc
            # Let foreign key or other integrity failures bubble up to be seen as 500/errors
            # rather than business logic "Conflict"
            raise exc
        except Exception as exc:  # noqa: BLE001
            raise exc
        return AuditEvent(
            id=event_id,
            tenant_id=tenant_id,
            run_id=run_id,
            actor_user_id=actor_user_id,
            event_type=event_type,
            operation_id=operation_id,
            payload=payload,
            created_at=created_at,
        )

    def list_events_for_run(self, run_id: str) -> list[AuditEvent]:
        with self._database.connection() as connection:
            rows = connection.execute(
                """
                SELECT id, tenant_id, run_id, actor_user_id, event_type,
                       operation_id, payload, created_at
                FROM audit_events
                WHERE run_id = ?
                ORDER BY created_at
                """,
                (run_id,),
            ).fetchall()
        return [
            AuditEvent(
                id=str(row["id"]),
                tenant_id=str(row["tenant_id"]),
                run_id=str(row["run_id"]) if row["run_id"] is not None else None,
                actor_user_id=str(row["actor_user_id"]) if row["actor_user_id"] is not None else None,
                event_type=str(row["event_type"]),
                operation_id=str(row["operation_id"]) if row["operation_id"] is not None else None,
                payload=_deserialize(str(row["payload"])),
                created_at=parse_timestamp(str(row["created_at"])),
            )
            for row in rows
        ]

    def list_recent_events_for_tenant(self, tenant_id: str, limit: int) -> list[AuditEvent]:
        with self._database.connection() as connection:
            rows = connection.execute(
                """
                SELECT id, tenant_id, run_id, actor_user_id, event_type,
                       operation_id, payload, created_at
                FROM audit_events
                WHERE tenant_id = ?
                ORDER BY created_at DESC
                LIMIT ?
                """,
                (tenant_id, limit),
            ).fetchall()
        return [
            AuditEvent(
                id=str(row["id"]),
                tenant_id=str(row["tenant_id"]),
                run_id=str(row["run_id"]) if row["run_id"] is not None else None,
                actor_user_id=str(row["actor_user_id"]) if row["actor_user_id"] is not None else None,
                event_type=str(row["event_type"]),
                operation_id=str(row["operation_id"]) if row["operation_id"] is not None else None,
                payload=_deserialize(str(row["payload"])),
                created_at=parse_timestamp(str(row["created_at"])),
            )
            for row in reversed(rows)
        ]

    def find_event_by_operation_id(self, operation_id: str) -> AuditEvent | None:
        with self._database.connection() as connection:
            row = connection.execute(
                """
                SELECT id, tenant_id, run_id, actor_user_id, event_type,
                       operation_id, payload, created_at
                FROM audit_events
                WHERE operation_id = ?
                """,
                (operation_id,),
            ).fetchone()
        if row is None:
            return None
        return AuditEvent(
            id=str(row["id"]),
            tenant_id=str(row["tenant_id"]),
            run_id=str(row["run_id"]) if row["run_id"] is not None else None,
            actor_user_id=str(row["actor_user_id"]) if row["actor_user_id"] is not None else None,
            event_type=str(row["event_type"]),
            operation_id=str(row["operation_id"]) if row["operation_id"] is not None else None,
            payload=_deserialize(str(row["payload"])),
            created_at=parse_timestamp(str(row["created_at"])),
        )

    def counts(self) -> dict[str, int]:
        with self._database.connection() as connection:
            tenants = connection.execute("SELECT COUNT(*) AS count FROM tenants").fetchone()
            users = connection.execute("SELECT COUNT(*) AS count FROM users").fetchone()
            runs = connection.execute("SELECT COUNT(*) AS count FROM runs").fetchone()
        result = {
            "tenants": int(tenants["count"]) if tenants is not None else 0,
            "users": int(users["count"]) if users is not None else 0,
            "runs": int(runs["count"]) if runs is not None else 0,
        }
        logger.debug("Database counts snapshot", ledger_id="LDR-001", counts=result)
        return result

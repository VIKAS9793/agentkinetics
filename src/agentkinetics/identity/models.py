from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum


class Role(StrEnum):
    ADMIN = "admin"
    OPERATOR = "operator"


@dataclass(frozen=True)
class Tenant:
    id: str
    name: str
    created_at: datetime


@dataclass(frozen=True)
class User:
    id: str
    tenant_id: str
    username: str
    display_name: str
    role: Role
    created_at: datetime


@dataclass(frozen=True)
class LocalIdentityRecord:
    user: User
    password_hash: str
    password_salt: str


@dataclass(frozen=True)
class Session:
    id: str
    tenant_id: str
    user_id: str
    token: str
    expires_at: datetime
    created_at: datetime
    revoked_at: datetime | None


@dataclass(frozen=True)
class SessionPrincipal:
    tenant_id: str
    user_id: str
    role: Role
    session_id: str


@dataclass(frozen=True)
class SessionContext:
    session_id: str
    tenant_id: str
    user_id: str
    username: str
    display_name: str
    role: Role

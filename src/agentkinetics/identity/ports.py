from __future__ import annotations

from datetime import datetime
from typing import Protocol

from agentkinetics.identity.models import LocalIdentityRecord, Session, Tenant, User


class IdentityRepository(Protocol):
    def get_default_tenant(self) -> Tenant | None:
        ...

    def create_default_tenant(self, name: str) -> Tenant:
        ...

    def create_user(
        self,
        tenant_id: str,
        username: str,
        display_name: str,
        role: str,
        password_hash: str,
        password_salt: str,
    ) -> User:
        ...

    def get_local_identity_by_username(self, username: str) -> LocalIdentityRecord | None:
        ...

    def get_user_by_id(self, user_id: str) -> User | None:
        ...

    def create_session(
        self,
        tenant_id: str,
        user_id: str,
        token: str,
        expires_at: datetime,
    ) -> Session:
        ...

    def get_session_by_token(self, token: str) -> Session | None:
        ...

    def revoke_session(self, token: str) -> None:
        ...


class AuthProvider(Protocol):
    def authenticate(self, username: str, password: str) -> Session:
        ...

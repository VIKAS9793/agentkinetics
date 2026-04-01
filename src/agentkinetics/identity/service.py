from __future__ import annotations

import hashlib
import hmac
import secrets
from datetime import timedelta

from agentkinetics.identity.models import Role, Session, SessionContext, SessionPrincipal, Tenant, User
from agentkinetics.identity.ports import AuthProvider, IdentityRepository
from agentkinetics.shared.errors import ConflictError, UnauthorizedError
from agentkinetics.shared.time import utc_now
from agentkinetics.shared.logging import get_logger

logger = get_logger("identity")


PBKDF2_ITERATIONS = 600_000
PBKDF2_DIGEST = "sha256"
SESSION_TOKEN_BYTES = 32


class LocalAuthProvider(AuthProvider):
    def __init__(self, repository: IdentityRepository, session_ttl_hours: int) -> None:
        self._repository = repository
        self._session_ttl_hours = session_ttl_hours

    def authenticate(self, username: str, password: str) -> Session:
        identity = self._repository.get_local_identity_by_username(username)
        if identity is None:
            logger.warning("Auth Failure: User not found", username=username)
            raise UnauthorizedError("Invalid username or password.")
            
        logger.debug("Verifying password hash", username=username)
        expected_hash = _hash_password(password=password, salt=identity.password_salt)
        if not hmac.compare_digest(expected_hash, identity.password_hash):
            logger.warning("Auth Failure: Password mismatch", username=username)
            raise UnauthorizedError("Invalid username or password.")
            
        logger.info("Auth Success", username=username, user_id=identity.user.id)
        expires_at = utc_now() + timedelta(hours=self._session_ttl_hours)
        token = secrets.token_hex(SESSION_TOKEN_BYTES)
        return self._repository.create_session(
            tenant_id=identity.user.tenant_id,
            user_id=identity.user.id,
            token=token,
            expires_at=expires_at,
        )


class IdentityService:
    def __init__(self, repository: IdentityRepository, auth_provider: AuthProvider) -> None:
        self._repository = repository
        self._auth_provider = auth_provider

    def ensure_default_tenant(self, name: str) -> Tenant:
        tenant = self._repository.get_default_tenant()
        if tenant is not None:
            logger.debug("Default tenant already present", tenant_id=tenant.id)
            return tenant
        logger.info("Creating default tenant through identity service", tenant_name=name)
        return self._repository.create_default_tenant(name)

    def create_local_user(
        self,
        username: str,
        password: str,
        display_name: str,
        role: Role,
    ) -> User:
        tenant = self._repository.get_default_tenant()
        if tenant is None:
            raise ConflictError("Default tenant must exist before creating users.")
        existing = self._repository.get_local_identity_by_username(username)
        if existing is not None:
            logger.warning("Registration Conflict: Username already exists", username=username)
            raise ConflictError(f"Local user '{username}' already exists.")
            
        logger.info("Creating local user", username=username, role=role.value)
        salt = secrets.token_hex(16)
        password_hash = _hash_password(password=password, salt=salt)
        return self._repository.create_user(
            tenant_id=tenant.id,
            username=username,
            display_name=display_name,
            role=role.value,
            password_hash=password_hash,
            password_salt=salt,
        )

    def create_session(self, username: str, password: str) -> Session:
        logger.debug("Delegating session creation to auth provider", username=username)
        return self._auth_provider.authenticate(username=username, password=password)

    def require_principal(self, session_token: str) -> SessionPrincipal:
        session = self._repository.get_session_by_token(session_token)
        if session is None or session.revoked_at is not None or session.expires_at <= utc_now():
            logger.warning(
                "Session principal rejected",
                session_token_prefix=session_token[:8],
                reason="missing_revoked_or_expired",
                ledger_id="LDR-006",
            )
            raise UnauthorizedError("Session token is invalid or expired.")
        user = self._repository.get_user_by_id(session.user_id)
        if user is None:
            logger.warning(
                "Session principal rejected",
                session_token_prefix=session_token[:8],
                reason="user_missing",
                ledger_id="LDR-006",
            )
            raise UnauthorizedError("Session user no longer exists.")
        logger.debug(
            "Session principal resolved",
            session_id=session.id,
            user_id=user.id,
            role=user.role.value,
        )
        return SessionPrincipal(
            tenant_id=user.tenant_id,
            user_id=user.id,
            role=user.role,
            session_id=session.id,
        )

    def describe_session(self, session_token: str) -> SessionContext:
        principal = self.require_principal(session_token=session_token)
        user = self._repository.get_user_by_id(principal.user_id)
        if user is None:
            logger.warning("Session description failed because user disappeared", user_id=principal.user_id)
            raise UnauthorizedError("Session user no longer exists.")
        logger.debug("Session description resolved", session_id=principal.session_id, user_id=user.id)
        return SessionContext(
            session_id=principal.session_id,
            tenant_id=principal.tenant_id,
            user_id=principal.user_id,
            username=user.username,
            display_name=user.display_name,
            role=user.role,
        )

    def logout(self, session_token: str) -> None:
        logger.info("Revoking session", session_token_prefix=session_token[:8])
        self._repository.revoke_session(token=session_token)


def _hash_password(password: str, salt: str) -> str:
    digest = hashlib.pbkdf2_hmac(
        PBKDF2_DIGEST,
        password.encode("utf-8"),
        salt.encode("utf-8"),
        PBKDF2_ITERATIONS,
    )
    return digest.hex()

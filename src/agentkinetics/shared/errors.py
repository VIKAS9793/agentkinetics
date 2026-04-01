class DomainError(Exception):
    """Base domain error for predictable application failures."""


class NotFoundError(DomainError):
    """Raised when a requested resource does not exist."""


class ConflictError(DomainError):
    """Raised when a resource violates uniqueness or state constraints."""


class UnauthorizedError(DomainError):
    """Raised when authentication or authorization fails."""


class PolicyDeniedError(DomainError):
    """Raised when policy evaluation denies an operation.

    Attributes:
        policy_status: Machine-readable reason — 'pending' means a human decision
            is still outstanding; 'denied' means the request was explicitly rejected.
    """

    def __init__(self, message: str, policy_status: str = "denied") -> None:
        super().__init__(message)
        self.policy_status = policy_status  # "pending" | "denied"

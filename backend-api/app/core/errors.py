class DomainError(Exception):
    """Base class for business-rule failures raised by the service layer.

    Services never import FastAPI. They raise subclasses of this error and the
    HTTP layer maps them to the standard error envelope.

    Attributes:
        code: Stable machine-readable error identifier.
        message: Human-readable explanation safe to show to clients.
        status_code: HTTP status the error maps to.
        commit_changes: When True the request transaction is committed instead
            of rolled back, for failures that must persist their side effects
            (for example recording a failed AI call or a revoked token family).
    """

    default_code = "DOMAIN_ERROR"
    default_status = 400

    def __init__(
        self,
        message: str,
        code: str | None = None,
        status_code: int | None = None,
        commit_changes: bool = False,
    ) -> None:
        """Initialize a domain error.

        Args:
            message: Human-readable explanation.
            code: Optional override of the class default error code.
            status_code: Optional override of the class default HTTP status.
            commit_changes: Persist pending writes even though the request fails.
        """
        self.code = code or self.default_code
        self.message = message
        self.status_code = status_code or self.default_status
        self.commit_changes = commit_changes
        super().__init__(message)


class ValidationFailedError(DomainError):
    """Input is well-formed but violates a business validation rule."""

    default_code = "VALIDATION_FAILED"
    default_status = 422


class AuthenticationError(DomainError):
    """Caller could not be authenticated."""

    default_code = "AUTHENTICATION_REQUIRED"
    default_status = 401


class QuotaExceededError(DomainError):
    """Plan quota or plan feature gate blocks the requested operation."""

    default_code = "QUOTA_EXCEEDED"
    default_status = 402


class PermissionDeniedError(DomainError):
    """Caller is authenticated but not allowed to perform the operation."""

    default_code = "PERMISSION_DENIED"
    default_status = 403


class NotFoundError(DomainError):
    """Requested resource does not exist or is not visible to the caller."""

    default_code = "NOT_FOUND"
    default_status = 404


class ConflictError(DomainError):
    """Operation conflicts with the current state of a resource."""

    default_code = "CONFLICT"
    default_status = 409


class InvalidStateError(ConflictError):
    """Resource is in a state that does not allow the requested transition."""

    default_code = "INVALID_STATE"


class AIUnavailableError(DomainError):
    """The AI service is unreachable or returned an unusable response.

    Attributes:
        retryable: True for transient failures (transport errors, upstream 5xx)
            that a background job may retry. Misconfiguration is not retryable.
    """

    default_code = "AI_UNAVAILABLE"
    default_status = 503

    def __init__(
        self,
        message: str,
        code: str | None = None,
        status_code: int | None = None,
        commit_changes: bool = False,
        retryable: bool = False,
    ) -> None:
        """Initialize the error.

        Args:
            message: Human-readable explanation.
            code: Optional override of the default error code.
            status_code: Optional override of the default HTTP status.
            commit_changes: Persist pending writes even though the request fails.
            retryable: Whether retrying the same call may succeed.
        """
        super().__init__(message, code, status_code, commit_changes)
        self.retryable = retryable

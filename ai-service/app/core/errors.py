class ServiceError(Exception):
    """Base error mapped to the standard ``{"error": {...}}`` response envelope.

    Attributes:
        code: Stable machine-readable error identifier.
        message: Human-readable explanation.
        status_code: HTTP status the error maps to.
    """

    default_code = "SERVICE_ERROR"
    default_status = 500

    def __init__(self, message: str, code: str | None = None, status_code: int | None = None) -> None:
        """Initialize the error.

        Args:
            message: Human-readable explanation.
            code: Optional override of the class default code.
            status_code: Optional override of the class default HTTP status.
        """
        self.code = code or self.default_code
        self.message = message
        self.status_code = status_code or self.default_status
        super().__init__(message)


class AuthenticationError(ServiceError):
    """The caller did not present a valid service token."""

    default_code = "INVALID_SERVICE_TOKEN"
    default_status = 401


class InvalidStorageKeyError(ServiceError):
    """A storage key was malformed or tried to escape the storage root."""

    default_code = "INVALID_STORAGE_KEY"
    default_status = 400


class AudioNotFoundError(ServiceError):
    """The referenced audio file does not exist in storage."""

    default_code = "AUDIO_NOT_FOUND"
    default_status = 404


class ProviderNotConfiguredError(ServiceError):
    """A required external provider (ASR, LLM, embeddings) has no credentials or model."""

    default_code = "PROVIDER_NOT_CONFIGURED"
    default_status = 503


class ProviderError(ServiceError):
    """An external provider failed or returned an unusable response."""

    default_code = "PROVIDER_ERROR"
    default_status = 502

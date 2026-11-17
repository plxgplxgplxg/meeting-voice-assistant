import secrets
from typing import Annotated

from fastapi import Header

from app.core.config import ai_settings
from app.core.errors import AuthenticationError


async def require_service_token(
    x_service_token: Annotated[str | None, Header()] = None,
) -> None:
    """Authenticate the calling backend by its shared service token.

    Args:
        x_service_token: Value of the ``X-Service-Token`` header.

    Raises:
        AuthenticationError: If the header is missing or does not match.
    """
    expected = ai_settings.ai_service_token.encode()
    provided = (x_service_token or "").encode()
    if not provided or not secrets.compare_digest(provided, expected):
        raise AuthenticationError("Missing or invalid service token.")

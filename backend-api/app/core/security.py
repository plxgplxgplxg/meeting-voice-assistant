import re
from datetime import timedelta
from typing import Any

import bcrypt
from jose import JWTError, jwt

from app.core.clock import utc_now
from app.core.config import settings
from app.core.errors import AuthenticationError

BCRYPT_MAX_PASSWORD_BYTES = 72


def sanitize_filename(filename: str) -> str:
    """Reduce an uploaded filename to a safe display name.

    Only used for the display name stored in the database. Files on disk are
    named from generated identifiers, never from user input.

    Args:
        filename: Original file name string.

    Returns:
        File name without path separators or control characters.
    """
    base = re.split(r"[\\/]", filename)[-1]
    cleaned = re.sub(r"[\x00-\x1f]", "", base).strip()
    return cleaned or "recording"


def hash_password(password: str) -> str:
    """Hash a plaintext password using bcrypt.

    Args:
        password: Plain text password string.

    Returns:
        Hashed password string.
    """
    pwd_bytes = password.encode("utf-8")[:BCRYPT_MAX_PASSWORD_BYTES]
    return bcrypt.hashpw(pwd_bytes, bcrypt.gensalt(rounds=settings.bcrypt_rounds)).decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plaintext password against a bcrypt hash.

    Args:
        plain_password: Plain text password to check.
        hashed_password: Stored bcrypt password hash.

    Returns:
        True if matching, False otherwise.
    """
    try:
        plain_bytes = plain_password.encode("utf-8")[:BCRYPT_MAX_PASSWORD_BYTES]
        return bcrypt.checkpw(plain_bytes, hashed_password.encode("utf-8"))
    except ValueError:
        return False


def _encode_token(data: dict[str, Any], token_type: str, lifetime: timedelta) -> str:
    now = utc_now()
    claims = {**data, "exp": now + lifetime, "iat": now, "type": token_type}
    return jwt.encode(claims, settings.secret_key, algorithm=settings.algorithm)


def create_access_token(data: dict[str, Any], expires_delta: timedelta | None = None) -> str:
    """Create a signed JWT access token.

    Args:
        data: Payload dictionary to encode (must include ``sub``).
        expires_delta: Optional custom lifetime.

    Returns:
        Encoded JWT token string.
    """
    return _encode_token(
        data, "access", expires_delta or timedelta(minutes=settings.access_token_expire_minutes)
    )


def create_refresh_token(data: dict[str, Any], expires_delta: timedelta | None = None) -> str:
    """Create a signed JWT refresh token.

    Args:
        data: Payload dictionary to encode (must include ``sub`` and ``jti``).
        expires_delta: Optional custom lifetime.

    Returns:
        Encoded JWT refresh token string.
    """
    return _encode_token(
        data, "refresh", expires_delta or timedelta(days=settings.refresh_token_expire_days)
    )


def decode_jwt_token(token: str) -> dict[str, Any]:
    """Decode and validate a JWT signature and expiration.

    Args:
        token: JWT string to decode.

    Returns:
        Decoded payload dictionary.

    Raises:
        AuthenticationError: If the token is invalid or expired. The parser
            error is deliberately not echoed to the client.
    """
    try:
        return jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
    except JWTError as exc:
        raise AuthenticationError(
            "Invalid or expired token.", code="INVALID_TOKEN"
        ) from exc

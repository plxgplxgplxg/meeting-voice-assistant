import uuid
from datetime import datetime, timedelta
from typing import Annotated, Any
from fastapi import Depends, HTTPException, Query, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db_session

import bcrypt

http_bearer = HTTPBearer(auto_error=False)

DatabaseSession = Annotated[AsyncSession, Depends(get_db_session)]


def sanitize_filename(filename: str) -> str:
    """Sanitize uploaded filename to prevent directory traversal attacks.

    Args:
        filename: Original file name string.

    Returns:
        Sanitized file name string.
    """
    return filename.replace("/", "").replace("\\", "").strip()


def hash_password(password: str) -> str:
    """Hash a plaintext password using bcrypt.

    Args:
        password: Plain text password string.

    Returns:
        Hashed password string.
    """
    pwd_bytes = password.encode("utf-8")[:72]
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(pwd_bytes, salt).decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plaintext password against a bcrypt hash.

    Args:
        plain_password: Plain text password to check.
        hashed_password: Stored bcrypt password hash.

    Returns:
        True if matching, False otherwise.
    """
    try:
        plain_bytes = plain_password.encode("utf-8")[:72]
        hash_bytes = hashed_password.encode("utf-8")
        return bcrypt.checkpw(plain_bytes, hash_bytes)
    except Exception:
        return False


def create_access_token(
    data: dict[str, Any], expires_delta: timedelta | None = None
) -> str:
    """Create a signed JWT access token.

    Args:
        data: Payload dictionary to encode.
        expires_delta: Optional custom expiration timedelta.

    Returns:
        Encoded JWT token string.
    """
    to_encode = data.copy()
    now = datetime.utcnow()
    expire = now + (
        expires_delta or timedelta(minutes=settings.access_token_expire_minutes)
    )
    to_encode.update({"exp": expire, "iat": now, "type": "access"})
    return jwt.encode(to_encode, settings.secret_key, algorithm=settings.algorithm)


def create_refresh_token(
    data: dict[str, Any], expires_delta: timedelta | None = None
) -> str:
    """Create a signed JWT refresh token.

    Args:
        data: Payload dictionary to encode.
        expires_delta: Optional custom expiration timedelta.

    Returns:
        Encoded JWT refresh token string.
    """
    to_encode = data.copy()
    now = datetime.utcnow()
    expire = now + (
        expires_delta or timedelta(days=settings.refresh_token_expire_days)
    )
    to_encode.update({"exp": expire, "iat": now, "type": "refresh"})
    return jwt.encode(to_encode, settings.secret_key, algorithm=settings.algorithm)


def decode_jwt_token(token: str) -> dict[str, Any]:
    """Decode and validate a JWT token signature and expiration.

    Args:
        token: JWT string to decode.

    Returns:
        Decoded payload dictionary.

    Raises:
        HTTPException: If token is expired or invalid.
    """
    try:
        payload = jwt.decode(
            token, settings.secret_key, algorithms=[settings.algorithm]
        )
        return payload
    except JWTError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid or expired token: {str(exc)}",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc


async def get_current_user_optional(
    auth: Annotated[HTTPAuthorizationCredentials | None, Depends(http_bearer)],
    db: DatabaseSession,
) -> Any:
    """Retrieve the authenticated user if Bearer token is provided, or None.

    Args:
        auth: HTTP authorization credentials header.
        db: Active database session.

    Returns:
        UserModel instance or None.
    """
    if not auth or not auth.credentials:
        return None

    try:
        payload = decode_jwt_token(auth.credentials)
        user_id_str = payload.get("sub")
        if not user_id_str:
            return None
        user_id = uuid.UUID(user_id_str)
    except Exception:
        return None

    from app.models.user import UserModel

    result = await db.execute(select(UserModel).where(UserModel.id == user_id))
    user = result.scalar_one_or_none()
    return user if user and user.is_active else None


async def get_current_user(
    auth: Annotated[HTTPAuthorizationCredentials | None, Depends(http_bearer)],
    db: DatabaseSession,
) -> Any:
    """Dependency ensuring the request is made by a verified, authenticated user.

    Args:
        auth: HTTP authorization credentials header.
        db: Active database session.

    Returns:
        Authenticated UserModel instance.

    Raises:
        HTTPException: If authentication fails or account is disabled.
    """
    if not auth or not auth.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    payload = decode_jwt_token(auth.credentials)
    user_id_str = payload.get("sub")
    if not user_id_str:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token payload missing subject.",
        )

    from app.models.user import UserModel

    user_id = uuid.UUID(user_id_str)
    result = await db.execute(select(UserModel).where(UserModel.id == user_id))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User associated with token not found.",
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is deactivated.",
        )

    return user

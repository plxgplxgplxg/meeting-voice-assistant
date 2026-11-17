import uuid
from datetime import timedelta

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.clock import utc_now
from app.core.config import settings
from app.core.errors import AuthenticationError, ConflictError, PermissionDeniedError
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_jwt_token,
    hash_password,
    verify_password,
)
from app.models.refresh_token import RefreshTokenModel
from app.models.user import UserModel
from app.schemas.auth import TokenResponse, UserLoginRequest, UserRegisterRequest
from app.services.billing.subscription_service import SubscriptionService


class AuthService:
    """Service handling registration, login, and rotating refresh tokens."""

    def __init__(
        self,
        session: AsyncSession,
        subscriptions: SubscriptionService | None = None,
    ) -> None:
        """Initialize the service.

        Args:
            session: Active SQLAlchemy session.
            subscriptions: Creates the Free subscription for new accounts.
        """
        self.session = session
        self.subscriptions = subscriptions or SubscriptionService(session)

    async def register(self, payload: UserRegisterRequest) -> tuple[UserModel, TokenResponse]:
        """Register a new user account with a Free subscription.

        Args:
            payload: User registration details.

        Returns:
            Tuple of the created user and a fresh token pair.

        Raises:
            ConflictError: If the email address is already registered.
        """
        existing = await self.session.execute(
            select(UserModel).where(UserModel.email == payload.email)
        )
        if existing.scalar_one_or_none():
            raise ConflictError(
                f"Email '{payload.email}' is already registered.", code="EMAIL_ALREADY_REGISTERED"
            )

        user = UserModel(
            email=payload.email,
            full_name=payload.full_name,
            password_hash=hash_password(payload.password),
            role="user",
            is_active=True,
        )
        self.session.add(user)
        await self.session.flush()
        await self.subscriptions.create_free_subscription(user.id)

        return user, await self.issue_tokens(user)

    async def login(self, payload: UserLoginRequest) -> tuple[UserModel, TokenResponse]:
        """Authenticate credentials and issue a new token family.

        Args:
            payload: Login credentials.

        Returns:
            Tuple of the authenticated user and a fresh token pair.

        Raises:
            AuthenticationError: If the credentials are wrong.
            PermissionDeniedError: If the account is deactivated.
        """
        result = await self.session.execute(
            select(UserModel).where(UserModel.email == payload.email)
        )
        user = result.scalar_one_or_none()

        if not user or not verify_password(payload.password, user.password_hash):
            raise AuthenticationError("Incorrect email or password.", code="INVALID_CREDENTIALS")
        if not user.is_active:
            raise PermissionDeniedError("Account is inactive.", code="ACCOUNT_DISABLED")

        return user, await self.issue_tokens(user)

    async def refresh_token(self, refresh_token: str) -> TokenResponse:
        """Rotate a refresh token and issue a new token pair.

        Each refresh token is single use. Presenting one that was already used
        revokes the entire token family, which limits the damage of a stolen
        token.

        Args:
            refresh_token: Signed JWT refresh token.

        Returns:
            New token pair in the same family.

        Raises:
            AuthenticationError: If the token is invalid, revoked, reused, or stale.
        """
        payload = decode_jwt_token(refresh_token)
        invalid = AuthenticationError("Invalid or expired token.", code="INVALID_TOKEN")
        if payload.get("type") != "refresh" or not payload.get("jti"):
            raise invalid

        record = await self.session.scalar(
            select(RefreshTokenModel)
            .where(RefreshTokenModel.jti == payload["jti"])
            .with_for_update()
        )
        if record is None:
            raise invalid

        if record.revoked_at is not None:
            await self._revoke_family(record.family_id)
            raise AuthenticationError(
                "Refresh token was already used. Please sign in again.",
                code="REFRESH_TOKEN_REUSED",
                commit_changes=True,
            )

        user = await self.session.get(UserModel, record.user_id)
        if not user or not user.is_active or payload.get("tv") != user.token_version:
            raise invalid

        record.revoked_at = utc_now()
        return await self.issue_tokens(user, family_id=record.family_id)

    async def issue_tokens(self, user: UserModel, family_id: str | None = None) -> TokenResponse:
        """Create an access token and a persisted, rotatable refresh token.

        Args:
            user: User the tokens are issued to.
            family_id: Existing token family when rotating, else a new family.

        Returns:
            Token pair response.
        """
        jti = uuid.uuid4().hex
        family = family_id or uuid.uuid4().hex
        lifetime = timedelta(days=settings.refresh_token_expire_days)

        self.session.add(
            RefreshTokenModel(
                jti=jti, family_id=family, user_id=user.id, expires_at=utc_now() + lifetime
            )
        )
        await self.session.flush()

        access_token = create_access_token(
            {
                "sub": str(user.id),
                "email": user.email,
                "role": user.role,
                "name": user.full_name,
                "tv": user.token_version,
            }
        )
        refresh_token = create_refresh_token(
            {"sub": str(user.id), "jti": jti, "tv": user.token_version}, lifetime
        )
        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="bearer",
            expires_in=settings.access_token_expire_minutes * 60,
        )

    async def _revoke_family(self, family_id: str) -> None:
        await self.session.execute(
            update(RefreshTokenModel)
            .where(RefreshTokenModel.family_id == family_id, RefreshTokenModel.revoked_at.is_(None))
            .values(revoked_at=utc_now())
        )
        await self.session.flush()

import uuid
from datetime import datetime, timedelta
from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_jwt_token,
    hash_password,
    verify_password,
)
from app.models.billing import PlanConfigModel, SubscriptionModel
from app.models.user import UserModel
from app.schemas.auth import (
    TokenResponse,
    UserLoginRequest,
    UserRegisterRequest,
)


class AuthService:
    """Service handling user registration, authentication, and session tokens."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def register(self, payload: UserRegisterRequest) -> tuple[UserModel, TokenResponse]:
        """Register a new user account with default Free subscription.

        Args:
            payload: User registration details.

        Returns:
            Tuple of created UserModel and TokenResponse.

        Raises:
            HTTPException: If the email address is already registered.
        """
        existing = await self.session.execute(
            select(UserModel).where(UserModel.email == payload.email)
        )
        if existing.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Email '{payload.email}' is already registered.",
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

        # Automatically bind default Free subscription if available
        free_plan = await self.session.scalar(
            select(PlanConfigModel).where(
                PlanConfigModel.slug == "free", PlanConfigModel.is_active == True
            )
        )
        if free_plan:
            now = datetime.utcnow()
            subscription = SubscriptionModel(
                user_id=user.id,
                plan_config_id=free_plan.id,
                status="active",
                current_period_start=now,
                current_period_end=now + timedelta(days=365 * 10),
                plan_snapshot={
                    "slug": free_plan.slug,
                    "name": free_plan.name,
                    "duration_limit": free_plan.total_duration_limit_minutes,
                },
            )
            self.session.add(subscription)
            await self.session.flush()

        tokens = self._generate_tokens(user)
        return user, tokens

    async def login(self, payload: UserLoginRequest) -> tuple[UserModel, TokenResponse]:
        """Authenticate user credentials and generate tokens.

        Args:
            payload: Login credentials.

        Returns:
            Tuple of authenticated UserModel and TokenResponse.

        Raises:
            HTTPException: If authentication fails.
        """
        result = await self.session.execute(
            select(UserModel).where(UserModel.email == payload.email)
        )
        user = result.scalar_one_or_none()

        if not user or not verify_password(payload.password, user.password_hash):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect email or password.",
            )

        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Account is inactive.",
            )

        tokens = self._generate_tokens(user)
        return user, tokens

    async def refresh_token(self, refresh_token: str) -> TokenResponse:
        """Issue a new access token using a valid refresh token.

        Args:
            refresh_token: Signed JWT refresh token.

        Returns:
            New TokenResponse with fresh access token.

        Raises:
            HTTPException: If token is invalid or user not found.
        """
        payload = decode_jwt_token(refresh_token)
        if payload.get("type") != "refresh":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid token type, refresh token expected.",
            )

        user_id_str = payload.get("sub")
        if not user_id_str:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Missing subject in token.",
            )

        user = await self.session.get(UserModel, uuid.UUID(user_id_str))
        if not user or not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User inactive or not found.",
            )

        return self._generate_tokens(user)

    def _generate_tokens(self, user: UserModel) -> TokenResponse:
        """Helper to create access and refresh token pair."""
        token_payload = {
            "sub": str(user.id),
            "email": user.email,
            "role": user.role,
            "name": user.full_name,
        }
        access_token = create_access_token(token_payload)
        refresh_token = create_refresh_token({"sub": str(user.id)})
        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="bearer",
            expires_in=settings.access_token_expire_minutes * 60,
        )

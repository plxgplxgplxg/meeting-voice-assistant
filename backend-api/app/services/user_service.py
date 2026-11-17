from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.clock import utc_now
from app.core.errors import ValidationFailedError
from app.core.security import hash_password, verify_password
from app.models.refresh_token import RefreshTokenModel
from app.models.user import UserModel
from app.schemas.user import ChangePasswordRequest, UserUpdateRequest


class UserService:
    """Service handling user profile updates and account security."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def update_profile(self, user: UserModel, payload: UserUpdateRequest) -> UserModel:
        """Update user profile information.

        Args:
            user: Current authenticated user.
            payload: New profile fields.

        Returns:
            Updated UserModel instance.
        """
        if payload.full_name is not None:
            user.full_name = payload.full_name
        if payload.avatar_url is not None:
            user.avatar_url = payload.avatar_url
        await self.session.flush()
        return user

    async def change_password(self, user: UserModel, payload: ChangePasswordRequest) -> None:
        """Change a user's password and invalidate every issued token.

        Bumping ``token_version`` makes all existing access and refresh tokens
        fail validation. Refresh token rows are also revoked.

        Args:
            user: Current authenticated user.
            payload: Old and new password.

        Raises:
            ValidationFailedError: If the old password does not match.
        """
        if not verify_password(payload.old_password, user.password_hash):
            raise ValidationFailedError(
                "Current password verification failed.",
                code="INVALID_CURRENT_PASSWORD",
                status_code=400,
            )

        user.password_hash = hash_password(payload.new_password)
        user.token_version += 1
        await self.session.execute(
            update(RefreshTokenModel)
            .where(RefreshTokenModel.user_id == user.id, RefreshTokenModel.revoked_at.is_(None))
            .values(revoked_at=utc_now())
        )
        await self.session.flush()

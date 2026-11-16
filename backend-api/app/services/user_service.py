from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_password, verify_password
from app.models.user import UserModel
from app.schemas.user import ChangePasswordRequest, UserUpdateRequest


class UserService:
    """Service handling user profile updates and account security."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def update_profile(
        self, user: UserModel, payload: UserUpdateRequest
    ) -> UserModel:
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

        self.session.add(user)
        await self.session.flush()
        return user

    async def change_password(
        self, user: UserModel, payload: ChangePasswordRequest
    ) -> None:
        """Change a user's password with old password verification.

        Args:
            user: Current authenticated user.
            payload: Old and new password.

        Raises:
            HTTPException: If old password does not match.
        """
        if not verify_password(payload.old_password, user.password_hash):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Current password verification failed.",
            )

        user.password_hash = hash_password(payload.new_password)
        self.session.add(user)
        await self.session.flush()

from typing import Annotated
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db_session
from app.core.security import get_current_user
from app.models.user import UserModel
from app.schemas.user import ChangePasswordRequest, UserResponse, UserUpdateRequest
from app.services.user_service import UserService

router = APIRouter(prefix="/users", tags=["Users"])

DatabaseSession = Annotated[AsyncSession, Depends(get_db_session)]
CurrentUser = Annotated[UserModel, Depends(get_current_user)]


@router.patch("/me", response_model=UserResponse)
async def update_my_profile(
    payload: UserUpdateRequest,
    current_user: CurrentUser,
    db: DatabaseSession,
) -> UserResponse:
    """Update profile attributes for currently authenticated user."""
    service = UserService(db)
    updated = await service.update_profile(current_user, payload)
    return UserResponse.model_validate(updated)


@router.post("/me/change-password")
async def change_my_password(
    payload: ChangePasswordRequest,
    current_user: CurrentUser,
    db: DatabaseSession,
) -> dict[str, str]:
    """Change account password verifying old password."""
    service = UserService(db)
    await service.change_password(current_user, payload)
    return {"message": "Password changed successfully."}

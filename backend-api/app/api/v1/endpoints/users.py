from fastapi import APIRouter

from app.api.deps import CurrentUser, DbSession
from app.schemas.auth import TokenResponse
from app.schemas.user import ChangePasswordRequest, UserResponse, UserUpdateRequest
from app.services.auth_service import AuthService
from app.services.user_service import UserService

router = APIRouter(prefix="/users", tags=["Users"])



@router.patch("/me", response_model=UserResponse)
async def update_my_profile(
    payload: UserUpdateRequest,
    current_user: CurrentUser,
    db: DbSession,
) -> UserResponse:
    """Update profile attributes for currently authenticated user."""
    service = UserService(db)
    updated = await service.update_profile(current_user, payload)
    return UserResponse.model_validate(updated)


@router.post("/me/change-password")
async def change_my_password(
    payload: ChangePasswordRequest,
    current_user: CurrentUser,
    db: DbSession,
) -> dict[str, str | TokenResponse]:
    """Change the password, invalidate old tokens, and return a fresh token pair."""
    await UserService(db).change_password(current_user, payload)
    tokens = await AuthService(db).issue_tokens(current_user)
    return {"message": "Password changed successfully.", "tokens": tokens}

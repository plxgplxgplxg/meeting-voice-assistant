from fastapi import APIRouter, status

from app.api.deps import CurrentUser, DbSession
from app.schemas.auth import (
    RefreshTokenRequest,
    TokenResponse,
    UserLoginRequest,
    UserRegisterRequest,
)
from app.schemas.user import UserResponse
from app.services.auth_service import AuthService

router = APIRouter(prefix="/auth", tags=["Authentication"])



@router.post(
    "/register",
    response_model=dict,
    status_code=status.HTTP_201_CREATED,
)
async def register_user(
    payload: UserRegisterRequest, db: DbSession
) -> dict:
    """Register a new user account with default Free quota."""
    service = AuthService(db)
    user, tokens = await service.register(payload)
    return {
        "user": UserResponse.model_validate(user),
        "tokens": tokens,
    }


@router.post("/login", response_model=TokenResponse)
async def login_user(
    payload: UserLoginRequest, db: DbSession
) -> TokenResponse:
    """Authenticate credentials and obtain JWT tokens."""
    service = AuthService(db)
    _, tokens = await service.login(payload)
    return tokens


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(
    payload: RefreshTokenRequest, db: DbSession
) -> TokenResponse:
    """Obtain a new access token using a refresh token."""
    service = AuthService(db)
    return await service.refresh_token(payload.refresh_token)


@router.get("/me", response_model=UserResponse)
async def get_current_authenticated_user(current_user: CurrentUser) -> UserResponse:
    """Retrieve profile of currently authenticated user."""
    return UserResponse.model_validate(current_user)

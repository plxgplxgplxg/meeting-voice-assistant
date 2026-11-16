from pydantic import BaseModel, EmailStr, Field


class UserRegisterRequest(BaseModel):
    """Schema for user account registration."""
    email: EmailStr
    full_name: str = Field(min_length=2, max_length=255)
    password: str = Field(min_length=6, max_length=128)


class UserLoginRequest(BaseModel):
    """Schema for user authentication credentials."""
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    """Schema for returning JWT tokens after successful authentication."""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int


class RefreshTokenRequest(BaseModel):
    """Schema for refreshing an expired access token."""
    refresh_token: str

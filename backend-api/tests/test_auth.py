import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_auth_register_and_login_flow(client: AsyncClient) -> None:
    """Test user registration, login, token refresh, and profile retrieval flow.

    Args:
        client: AsyncClient configured with test database session.
    """
    # 1. Register a new user
    register_payload = {
        "email": "testuser@example.com",
        "full_name": "Test User",
        "password": "Password123!",
    }
    reg_response = await client.post("/api/v1/auth/register", json=register_payload)
    assert reg_response.status_code == 201, reg_response.text
    reg_data = reg_response.json()
    assert reg_data["user"]["email"] == "testuser@example.com"
    assert reg_data["user"]["full_name"] == "Test User"
    assert "access_token" in reg_data["tokens"]
    assert "refresh_token" in reg_data["tokens"]

    access_token = reg_data["tokens"]["access_token"]
    refresh_token = reg_data["tokens"]["refresh_token"]

    # 2. Duplicate registration should fail with 409 Conflict
    dup_response = await client.post("/api/v1/auth/register", json=register_payload)
    assert dup_response.status_code == 409

    # 3. Login with correct credentials
    login_payload = {
        "email": "testuser@example.com",
        "password": "Password123!",
    }
    login_response = await client.post("/api/v1/auth/login", json=login_payload)
    assert login_response.status_code == 200
    login_tokens = login_response.json()
    assert "access_token" in login_tokens
    assert login_tokens["token_type"] == "bearer"

    # 4. Login with invalid password
    bad_login_response = await client.post(
        "/api/v1/auth/login",
        json={"email": "testuser@example.com", "password": "WrongPassword"},
    )
    assert bad_login_response.status_code == 401

    # 5. Get current user profile with Bearer token
    me_response = await client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {access_token}"},
    )
    assert me_response.status_code == 200
    me_data = me_response.json()
    assert me_data["email"] == "testuser@example.com"
    assert me_data["full_name"] == "Test User"

    # 6. Refresh token
    refresh_response = await client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": refresh_token},
    )
    assert refresh_response.status_code == 200
    refreshed_tokens = refresh_response.json()
    assert "access_token" in refreshed_tokens

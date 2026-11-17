from datetime import datetime

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core import database
from app.core.errors import ConflictError, DomainError
from app.models.refresh_token import RefreshTokenModel
from app.models.user import UserModel
from tests.conftest import RegisterUser


async def refresh(client: AsyncClient, token: str):
    return await client.post("/api/v1/auth/refresh", json={"refresh_token": token})


@pytest.mark.asyncio
async def test_password_change_invalidates_old_tokens_and_returns_new_ones(
    client: AsyncClient, register_user: RegisterUser
) -> None:
    """After a password change the previous access and refresh tokens stop working."""
    user = await register_user("u@example.com")

    change = await client.post(
        "/api/v1/users/me/change-password",
        headers=user.headers,
        json={"old_password": "Password123!", "new_password": "NewPassword456!"},
    )
    assert change.status_code == 200, change.text

    old_access = await client.get("/api/v1/auth/me", headers=user.headers)
    assert old_access.status_code == 401
    assert (await refresh(client, user.refresh_token)).status_code == 401

    new_headers = {"Authorization": f"Bearer {change.json()['tokens']['access_token']}"}
    assert (await client.get("/api/v1/auth/me", headers=new_headers)).status_code == 200


@pytest.mark.asyncio
async def test_refresh_token_is_single_use_and_reuse_revokes_the_family(
    client: AsyncClient, register_user: RegisterUser, db_session: AsyncSession
) -> None:
    """Rotating works once; replaying the old token kills every token in the family."""
    user = await register_user("u@example.com")

    first = await refresh(client, user.refresh_token)
    assert first.status_code == 200
    rotated = first.json()["refresh_token"]

    replay = await refresh(client, user.refresh_token)
    assert replay.status_code == 401
    assert replay.json()["error"]["code"] == "REFRESH_TOKEN_REUSED"

    after_revocation = await refresh(client, rotated)
    assert after_revocation.status_code == 401

    rows = (await db_session.scalars(select(RefreshTokenModel))).all()
    assert len({r.family_id for r in rows}) == 1
    assert all(r.revoked_at is not None for r in rows)


@pytest.mark.asyncio
async def test_token_types_are_not_interchangeable(
    client: AsyncClient, register_user: RegisterUser
) -> None:
    """A refresh token cannot authenticate requests and an access token cannot refresh."""
    user = await register_user("u@example.com")

    as_bearer = await client.get(
        "/api/v1/auth/me", headers={"Authorization": f"Bearer {user.refresh_token}"}
    )
    assert as_bearer.status_code == 401

    access = user.headers["Authorization"].removeprefix("Bearer ")
    assert (await refresh(client, access)).status_code == 401


@pytest.mark.asyncio
async def test_invalid_token_error_does_not_leak_parser_details(client: AsyncClient) -> None:
    """A malformed JWT yields a generic message."""
    response = await client.get(
        "/api/v1/auth/me", headers={"Authorization": "Bearer not.a.jwt"}
    )
    assert response.status_code == 401
    assert response.json()["error"]["message"] == "Invalid or expired token."


@pytest.mark.asyncio
async def test_db_dependency_commits_only_when_error_requests_it(test_engine) -> None:
    """DomainError(commit_changes=True) persists side effects, other errors roll back."""
    factory = async_sessionmaker(bind=test_engine, autoflush=False, expire_on_commit=False)
    async with factory() as setup:
        user = UserModel(email="dep@example.com", full_name="Dep", password_hash="x")
        setup.add(user)
        await setup.commit()
        user_id = user.id

    original = database.async_session_factory
    database.async_session_factory = factory
    try:

        async def fail_after_insert(jti: str, error: Exception) -> None:
            generator = database.get_db_session()
            session = await generator.__anext__()
            session.add(
                RefreshTokenModel(
                    jti=jti, family_id="f", user_id=user_id, expires_at=datetime(2030, 1, 1)
                )
            )
            await session.flush()
            with pytest.raises(type(error)):
                await generator.athrow(error)

        await fail_after_insert("kept", DomainError("keep", commit_changes=True))
        await fail_after_insert("discarded", ConflictError("discard"))
    finally:
        database.async_session_factory = original

    async with factory() as session:
        jtis = [row.jti for row in (await session.scalars(select(RefreshTokenModel))).all()]
    assert jtis == ["kept"]

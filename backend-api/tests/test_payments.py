from datetime import timedelta

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.clock import utc_now
from app.core.config import settings
from app.models.billing import PaymentOrderModel, SubscriptionModel
from tests.conftest import Account, RegisterUser

WEBHOOK_URL = "/api/v1/payments/sepay/webhook"


def webhook_headers() -> dict[str, str]:
    return {"Authorization": f"Apikey {settings.sepay_webhook_api_key}"}


async def create_order(client: AsyncClient, user: Account, plan: str = "pro") -> dict:
    response = await client.post(
        "/api/v1/payments/checkout", headers=user.headers, json={"plan_slug": plan}
    )
    assert response.status_code == 201, response.text
    return response.json()


def transfer(order_code: str, amount: float = 99000.0, txn: str = "TXN-1") -> dict:
    return {
        "id": txn,
        "transferAmount": amount,
        "content": f"Thanh toan don hang {order_code}",
        "accountNumber": "0388960805",
        "referenceCode": "MBVCB.123456",
    }


@pytest.mark.asyncio
async def test_checkout_and_webhook_activate_plan_from_today(
    client: AsyncClient, register_user: RegisterUser, db_session: AsyncSession
) -> None:
    """A confirmed payment starts the paid period now, not when the Free period ends."""
    user = await register_user("payer@example.com")
    checkout = await create_order(client, user)
    assert checkout["amount"] == 99000.0
    assert "qr.sepay.vn" in checkout["qr_url"]
    code = checkout["order_code"]
    assert len(code) == 13 and code.startswith("MVA")

    pending = await client.get(f"/api/v1/payments/orders/{code}", headers=user.headers)
    assert pending.json()["status"] == "pending"

    response = await client.post(WEBHOOK_URL, headers=webhook_headers(), json=transfer(code))
    assert response.status_code == 200
    assert response.json()["status"] == "success"

    done = await client.get(f"/api/v1/payments/orders/{code}", headers=user.headers)
    assert done.json()["status"] == "completed" and done.json()["paid_at"] is not None

    summary = await client.get("/api/v1/plans/my-subscription", headers=user.headers)
    body = summary.json()
    assert body["plan_slug"] == "pro"
    period_end = body["current_period_end"]
    assert period_end < (utc_now() + timedelta(days=31)).isoformat()

    subs = (await db_session.scalars(select(SubscriptionModel).where(SubscriptionModel.user_id == user.id))).all()
    assert sorted(s.status for s in subs) == ["active", "replaced"]


@pytest.mark.asyncio
@pytest.mark.parametrize("headers", [{}, {"Authorization": "Apikey wrong-key"}])
async def test_webhook_rejects_missing_or_wrong_key(
    client: AsyncClient, register_user: RegisterUser, headers: dict[str, str]
) -> None:
    """The webhook never skips authentication when the header is absent."""
    user = await register_user("payer@example.com")
    code = (await create_order(client, user))["order_code"]

    response = await client.post(WEBHOOK_URL, headers=headers, json=transfer(code))
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "INVALID_WEBHOOK_KEY"

    status = await client.get(f"/api/v1/payments/orders/{code}", headers=user.headers)
    assert status.json()["status"] == "pending"


@pytest.mark.asyncio
async def test_webhook_without_transaction_id_is_rejected(client: AsyncClient) -> None:
    """A payload with no id cannot be made idempotent, so it is refused."""
    payload = {"transferAmount": 99000, "content": "MVA0000000000"}
    response = await client.post(WEBHOOK_URL, headers=webhook_headers(), json=payload)
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "INVALID_WEBHOOK_PAYLOAD"


@pytest.mark.asyncio
async def test_duplicate_transaction_and_repeat_payment_activate_once(
    client: AsyncClient, register_user: RegisterUser, db_session: AsyncSession
) -> None:
    """Re-delivered or second transfers for a completed order never extend the plan twice."""
    user = await register_user("payer@example.com")
    code = (await create_order(client, user))["order_code"]

    first = await client.post(WEBHOOK_URL, headers=webhook_headers(), json=transfer(code, txn="A"))
    same_txn = await client.post(WEBHOOK_URL, headers=webhook_headers(), json=transfer(code, txn="A"))
    other_txn = await client.post(WEBHOOK_URL, headers=webhook_headers(), json=transfer(code, txn="B"))

    assert first.json()["status"] == "success"
    assert same_txn.json()["status"] == "duplicate"
    assert other_txn.json()["status"] == "duplicate"

    paid_subs = (
        await db_session.scalars(
            select(SubscriptionModel).where(
                SubscriptionModel.user_id == user.id, SubscriptionModel.status == "active"
            )
        )
    ).all()
    assert len([s for s in paid_subs if s.plan_snapshot["slug"] == "pro"]) == 1


@pytest.mark.asyncio
async def test_expired_order_is_not_activated(
    client: AsyncClient, register_user: RegisterUser, db_session: AsyncSession
) -> None:
    """A transfer that arrives after the order expired is recorded but does not activate a plan."""
    user = await register_user("payer@example.com")
    code = (await create_order(client, user))["order_code"]
    order = await db_session.scalar(select(PaymentOrderModel).where(PaymentOrderModel.order_code == code))
    order.expires_at = utc_now() - timedelta(minutes=1)
    await db_session.flush()

    response = await client.post(WEBHOOK_URL, headers=webhook_headers(), json=transfer(code))
    assert response.json()["status"] == "expired_order"

    status = await client.get(f"/api/v1/payments/orders/{code}", headers=user.headers)
    assert status.json()["status"] == "expired"
    summary = await client.get("/api/v1/plans/my-subscription", headers=user.headers)
    assert summary.json()["plan_slug"] == "free"


@pytest.mark.asyncio
async def test_partial_amount_does_not_activate(
    client: AsyncClient, register_user: RegisterUser
) -> None:
    """Underpaying leaves the order pending."""
    user = await register_user("payer@example.com")
    code = (await create_order(client, user))["order_code"]
    response = await client.post(WEBHOOK_URL, headers=webhook_headers(), json=transfer(code, amount=50000))
    assert response.json()["status"] == "partial_amount"
    status = await client.get(f"/api/v1/payments/orders/{code}", headers=user.headers)
    assert status.json()["status"] == "pending"


@pytest.mark.asyncio
async def test_order_status_requires_ownership(
    client: AsyncClient, register_user: RegisterUser
) -> None:
    """Order codes cannot be enumerated by other accounts or anonymous callers."""
    owner = await register_user("owner@example.com")
    stranger = await register_user("stranger@example.com")
    code = (await create_order(client, owner))["order_code"]

    assert (await client.get(f"/api/v1/payments/orders/{code}")).status_code == 401
    other = await client.get(f"/api/v1/payments/orders/{code}", headers=stranger.headers)
    assert other.status_code == 404


@pytest.mark.asyncio
async def test_checkout_rejects_free_and_unknown_plans(
    client: AsyncClient, register_user: RegisterUser
) -> None:
    """Only paid plans can be purchased."""
    user = await register_user("payer@example.com")
    for slug in ("free", "does-not-exist"):
        response = await client.post(
            "/api/v1/payments/checkout", headers=user.headers, json={"plan_slug": slug}
        )
        assert response.status_code == 422
        assert response.json()["error"]["code"] == "INVALID_PLAN"

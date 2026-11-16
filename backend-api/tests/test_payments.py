import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_payment_checkout_and_webhook_flow(client: AsyncClient) -> None:
    """Test full VietQR checkout session creation and SePay webhook fulfillment flow.

    Args:
        client: AsyncClient configured with test database session.
    """
    # 1. Register a user
    reg_response = await client.post(
        "/api/v1/auth/register",
        json={
            "email": "payuser@example.com",
            "full_name": "Paying User",
            "password": "Password123!",
        },
    )
    assert reg_response.status_code == 201
    tokens = reg_response.json()["tokens"]
    access_token = tokens["access_token"]
    auth_headers = {"Authorization": f"Bearer {access_token}"}

    # 2. Create VietQR checkout for 'pro' plan (99,000 VND)
    checkout_response = await client.post(
        "/api/v1/payments/checkout",
        headers=auth_headers,
        json={"plan_slug": "pro"},
    )
    assert checkout_response.status_code == 201
    checkout_data = checkout_response.json()
    assert checkout_data["amount"] == 99000.0
    assert "qr.sepay.vn" in checkout_data["qr_url"]
    order_code = checkout_data["order_code"]
    assert order_code.startswith("MVA")

    # 3. Check pending order status
    status_response = await client.get(f"/api/v1/payments/orders/{order_code}")
    assert status_response.status_code == 200
    assert status_response.json()["status"] == "pending"

    # 4. Trigger SePay webhook with matching order code in content
    webhook_payload = {
        "id": 1234567,
        "transactionId": "TXN_987654",
        "transferAmount": 99000.0,
        "content": f"Thanh toan don hang {order_code}",
        "accountNumber": "0388960805",
        "referenceCode": "MBVCB.123456",
    }
    webhook_response = await client.post(
        "/api/v1/payments/sepay/webhook",
        json=webhook_payload,
    )
    assert webhook_response.status_code == 200
    assert webhook_response.json()["status"] == "success"

    # 5. Order status is now completed
    completed_status = await client.get(f"/api/v1/payments/orders/{order_code}")
    assert completed_status.status_code == 200
    assert completed_status.json()["status"] == "completed"
    assert completed_status.json()["paid_at"] is not None

    # 6. Idempotency test: duplicate webhook call
    dup_webhook_res = await client.post(
        "/api/v1/payments/sepay/webhook",
        json=webhook_payload,
    )
    assert dup_webhook_res.status_code == 200
    assert dup_webhook_res.json()["status"] == "duplicate"

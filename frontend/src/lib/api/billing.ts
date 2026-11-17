import type { CheckoutDetails, OrderStatus, Plan, Subscription } from "@/types/api";
import { fetchApi } from "./client";

/**
 * List the plans available for purchase.
 *
 * @returns Active plans.
 */
export function listPlans(): Promise<Plan[]> {
  return fetchApi<Plan[]>("/plans");
}

/**
 * Fetch the subscription and quota usage of the signed-in user.
 *
 * @returns Current subscription.
 */
export function getMySubscription(): Promise<Subscription> {
  return fetchApi<Subscription>("/plans/my-subscription");
}

/**
 * Start a VietQR checkout for a plan.
 *
 * @param planSlug - Slug of the plan to buy.
 * @returns Bank transfer details and QR image URL.
 */
export function createCheckout(planSlug: string): Promise<CheckoutDetails> {
  return fetchApi<CheckoutDetails>("/payments/checkout", {
    method: "POST",
    body: JSON.stringify({ plan_slug: planSlug }),
  });
}

/**
 * Check whether a payment order has been fulfilled.
 *
 * @param orderCode - Order code returned by the checkout.
 * @returns Order status and payment time.
 */
export function getOrderStatus(orderCode: string): Promise<OrderStatus> {
  return fetchApi<OrderStatus>(`/payments/orders/${orderCode}`);
}

"use client";

import { useEffect, useRef } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  createCheckout,
  getMySubscription,
  getOrderStatus,
  listPlans,
} from "@/lib/api/billing";
import { useAuth } from "@/lib/auth-context";
import { queryKeys } from "@/lib/query-keys";

const ORDER_POLL_INTERVAL_MS = 2500;

/**
 * Load the plan and quota usage of the signed-in user.
 *
 * @returns Subscription query, disabled while signed out.
 */
export function useSubscription() {
  const { user } = useAuth();
  const userId = user?.id ?? null;

  return useQuery({
    queryKey: queryKeys.subscription(userId),
    queryFn: getMySubscription,
    enabled: userId !== null,
  });
}

/**
 * Load the purchasable plans.
 *
 * @param enabled - Whether the pricing view is open.
 * @returns Plans query.
 */
export function usePlans(enabled: boolean) {
  return useQuery({
    queryKey: queryKeys.plans,
    queryFn: listPlans,
    enabled,
  });
}

/**
 * Start a VietQR checkout for a plan.
 *
 * @returns Mutation resolving to the bank transfer details.
 */
export function useCheckout() {
  return useMutation({ mutationFn: createCheckout });
}

/**
 * Poll a payment order until it completes, then refresh the subscription.
 *
 * @param orderCode - Order to watch, or null when no checkout is open.
 * @returns Order status query.
 */
export function useOrderStatus(orderCode: string | null) {
  const { user } = useAuth();
  const queryClient = useQueryClient();
  const refreshedOrder = useRef<string | null>(null);

  const query = useQuery({
    queryKey: queryKeys.order(orderCode ?? ""),
    queryFn: () => getOrderStatus(orderCode ?? ""),
    enabled: orderCode !== null,
    staleTime: 0,
    gcTime: 0,
    refetchInterval: (current) =>
      current.state.data?.status === "completed" ? false : ORDER_POLL_INTERVAL_MS,
  });

  const isCompleted = query.data?.status === "completed";
  const userId = user?.id ?? null;

  useEffect(() => {
    if (!isCompleted || !orderCode || refreshedOrder.current === orderCode) return;
    refreshedOrder.current = orderCode;
    void queryClient.invalidateQueries({ queryKey: queryKeys.subscription(userId) });
  }, [isCompleted, orderCode, userId, queryClient]);

  return query;
}

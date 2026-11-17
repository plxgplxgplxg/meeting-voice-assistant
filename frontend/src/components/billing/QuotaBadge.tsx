"use client";

import React, { useState } from "react";
import { Zap } from "lucide-react";
import { useSubscription } from "@/hooks/useSubscription";
import { useAuth } from "@/lib/auth-context";
import type { Subscription } from "@/types/api";
import { PricingModal } from "./PricingModal";

const FREE_PLAN_FALLBACK: Subscription = {
  id: "fallback",
  plan_slug: "free",
  plan_name: "Gói Miễn Phí",
  status: "active",
  current_period_end: "",
  total_duration_limit_minutes: 60,
  used_duration_minutes: 0,
  remaining_duration_minutes: 60,
};

export function QuotaBadge() {
  const { user } = useAuth();
  const subscription = useSubscription();
  const [isPricingOpen, setIsPricingOpen] = useState(false);

  const quota =
    subscription.data ?? (subscription.isError ? FREE_PLAN_FALLBACK : null);

  if (!user || !quota) return null;

  const isUnlimited = quota.total_duration_limit_minutes >= 10000;
  const isLow = !isUnlimited && quota.remaining_duration_minutes <= 10;

  return (
    <>
      <button
        onClick={() => setIsPricingOpen(true)}
        className="flex items-center gap-2.5 px-3 py-1.5 rounded-xl border border-slate-200 bg-white hover:border-slate-300 hover:bg-slate-50 transition shadow-sm text-left group"
        title="Bảng giá"
      >
        <div
          className={`p-1 rounded-lg ${
            isUnlimited
              ? "bg-purple-100 text-purple-700"
              : isLow
              ? "bg-amber-100 text-amber-700"
              : "bg-emerald-100 text-emerald-700"
          }`}
        >
          <Zap className="w-3.5 h-3.5 fill-current" />
        </div>

        <div>
          <div className="text-xs font-bold text-slate-800">{quota.plan_name}</div>
          <div className="text-xs font-medium text-slate-600">
            {isUnlimited ? (
              <span>Không giới hạn</span>
            ) : (
              <span>
                {Math.round(quota.used_duration_minutes)}/
                {quota.total_duration_limit_minutes} phút
              </span>
            )}
          </div>
        </div>
      </button>

      <PricingModal
        isOpen={isPricingOpen}
        onClose={() => setIsPricingOpen(false)}
        currentPlanSlug={quota.plan_slug}
      />
    </>
  );
}

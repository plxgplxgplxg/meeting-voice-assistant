"use client";

import React, { useEffect, useState } from "react";
import { Zap, Clock } from "lucide-react";
import { fetchApi } from "@/lib/api";
import { useAuth } from "@/lib/auth-context";
import { PricingModal } from "./PricingModal";

interface QuotaSummary {
  id: string;
  plan_slug: string;
  plan_name: string;
  status: string;
  current_period_end: string;
  total_duration_limit_minutes: number;
  used_duration_minutes: number;
  remaining_duration_minutes: number;
}

export function QuotaBadge() {
  const { user } = useAuth();
  const [quota, setQuota] = useState<QuotaSummary | null>(null);
  const [isPricingOpen, setIsPricingOpen] = useState(false);

  const fetchQuota = async () => {
    if (!user) return;
    try {
      const data = await fetchApi<QuotaSummary>("/plans/my-subscription");
      setQuota(data);
    } catch {
      // Default to free quota indicator
      setQuota({
        plan_slug: "free",
        plan_name: "Gói Miễn Phí",
        id: "fallback",
        current_period_end: "",
        total_duration_limit_minutes: 60,
        used_duration_minutes: 0,
        remaining_duration_minutes: 60,
        status: "active",
      });
    }
  };

  useEffect(() => {
    fetchQuota();
  }, [user]);

  if (!user || !quota) return null;

  const isUnlimited = quota.total_duration_limit_minutes >= 10000;
  const isLow = !isUnlimited && quota.remaining_duration_minutes <= 10;

  return (
    <>
      <button
        onClick={() => setIsPricingOpen(true)}
        className="flex items-center gap-2.5 px-3 py-1.5 rounded-xl border border-slate-200 bg-white hover:border-slate-300 hover:bg-slate-50 transition shadow-sm text-left group"
        title="Bấm để xem bảng giá và nâng cấp"
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
          <div className="flex items-center gap-1.5">
            <span className="text-xs font-bold text-slate-800">
              {quota.plan_name}
            </span>
          </div>
          <div className="text-[11px] font-medium text-slate-500">
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
        onPlanUpgraded={() => {
          fetchQuota();
        }}
      />
    </>
  );
}

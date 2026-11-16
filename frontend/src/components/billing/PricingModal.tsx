"use client";

import React, { useState } from "react";
import { X, Check, Zap, Sparkles, Shield, ArrowRight, Loader2 } from "lucide-react";
import { fetchApi } from "@/lib/api";
import { VietQRModal, CheckoutDetails } from "./VietQRModal";

interface PlanConfig {
  id: string;
  slug: string;
  name: string;
  description: string;
  price_amount: number;
  currency: string;
  total_duration_limit_minutes: number;
  features: Record<string, any>;
  is_default: boolean;
}

interface PricingModalProps {
  isOpen: boolean;
  onClose: () => void;
  currentPlanSlug?: string;
  onPlanUpgraded?: () => void;
}

export function PricingModal({
  isOpen,
  onClose,
  currentPlanSlug = "free",
  onPlanUpgraded,
}: PricingModalProps) {
  const [plans, setPlans] = useState<PlanConfig[]>([]);
  const [loading, setLoading] = useState(false);
  const [checkoutData, setCheckoutData] = useState<CheckoutDetails | null>(null);
  const [isQrOpen, setIsQrOpen] = useState(false);
  const [checkingOutSlug, setCheckingOutSlug] = useState<string | null>(null);

  React.useEffect(() => {
    if (!isOpen) return;

    const loadPlans = async () => {
      setLoading(true);
      try {
        const data = await fetchApi<PlanConfig[]>("/plans");
        setPlans(data);
      } catch {
        // Fallback default plans if API fails
        setPlans([
          {
            id: "1",
            slug: "free",
            name: "Gói Miễn Phí",
            description: "Dành cho cá nhân trải nghiệm tính năng cơ bản",
            price_amount: 0,
            currency: "VND",
            total_duration_limit_minutes: 60,
            features: {
              max_meetings: 5,
              export_formats: ["txt", "json"],
            },
            is_default: true,
          },
          {
            id: "2",
            slug: "pro",
            name: "Gói Chuyên Nghiệp",
            description: "Dành cho chuyên viên họp trực tuyến thường xuyên",
            price_amount: 99000,
            currency: "VND",
            total_duration_limit_minutes: 600,
            features: {
              max_meetings: "Không giới hạn",
              export_formats: ["docx", "txt", "srt", "vtt", "json"],
              speaker_diarization: true,
            },
            is_default: false,
          },
          {
            id: "3",
            slug: "unlimited",
            name: "Gói Vô Hạn",
            description: "Toàn bộ tính năng cao cấp không giới hạn thời lượng",
            price_amount: 299000,
            currency: "VND",
            total_duration_limit_minutes: 999999,
            features: {
              max_meetings: "Không giới hạn",
              export_formats: ["docx", "txt", "srt", "vtt", "json"],
              speaker_diarization: true,
              priority_gpu: true,
            },
            is_default: false,
          },
        ]);
      } finally {
        setLoading(false);
      }
    };

    loadPlans();
  }, [isOpen]);

  const handleCheckout = async (slug: string) => {
    setCheckingOutSlug(slug);
    try {
      const res = await fetchApi<CheckoutDetails>("/payments/checkout", {
        method: "POST",
        body: JSON.stringify({ plan_slug: slug }),
      });
      setCheckoutData(res);
      setIsQrOpen(true);
    } catch (err: any) {
      alert(err.message || "Không thể tạo mã QR thanh toán.");
    } finally {
      setCheckingOutSlug(null);
    }
  };

  if (!isOpen) return null;

  return (
    <>
      <div className="fixed inset-0 z-40 flex items-center justify-center p-4 bg-slate-900/50 backdrop-blur-sm animate-in fade-in">
        <div className="bg-white rounded-3xl max-w-4xl w-full border border-slate-200 shadow-2xl overflow-hidden max-h-[90vh] flex flex-col">
          {/* Modal Header */}
          <div className="flex items-center justify-between px-8 py-5 border-b border-slate-100">
            <div>
              <h2 className="text-xl font-bold text-slate-900">
                Bảng Giá & Gói Dịch Vụ
              </h2>
              <p className="text-xs font-medium text-slate-500 mt-0.5">
                Nâng cấp dung lượng và mở khóa toàn bộ tính năng phân tích cuộc họp
              </p>
            </div>
            <button
              onClick={onClose}
              className="p-1.5 rounded-xl text-slate-400 hover:text-slate-600 hover:bg-slate-100 transition"
            >
              <X className="w-5 h-5" />
            </button>
          </div>

          {/* Plans Grid */}
          <div className="p-8 overflow-y-auto">
            {loading ? (
              <div className="py-20 flex justify-center items-center text-slate-400">
                <Loader2 className="w-6 h-6 animate-spin text-emerald-600" />
              </div>
            ) : (
              <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                {plans.map((p) => {
                  const isCurrent = currentPlanSlug === p.slug;
                  const isPro = p.slug === "pro";
                  const isFree = p.price_amount === 0;

                  return (
                    <div
                      key={p.slug}
                      className={`relative flex flex-col justify-between p-6 rounded-2xl border transition-all ${
                        isPro
                          ? "border-emerald-500 shadow-md ring-2 ring-emerald-500/10 bg-emerald-50/20"
                          : "border-slate-200 hover:border-slate-300 bg-white"
                      }`}
                    >
                      {isPro && (
                        <div className="absolute -top-3 left-1/2 -translate-x-1/2 px-3 py-0.5 rounded-full bg-emerald-600 text-white text-[11px] font-bold uppercase tracking-wider shadow-sm">
                          Phổ Biến Nhất
                        </div>
                      )}

                      <div>
                        <div className="flex items-center justify-between mb-2">
                          <h3 className="text-base font-bold text-slate-900">
                            {p.name}
                          </h3>
                          {isCurrent && (
                            <span className="px-2 py-0.5 rounded-full text-[11px] font-bold bg-slate-100 text-slate-700">
                              Đang Dùng
                            </span>
                          )}
                        </div>

                        <p className="text-xs text-slate-500 min-h-[32px]">
                          {p.description}
                        </p>

                        <div className="mt-4 mb-6">
                          <span className="text-3xl font-extrabold text-slate-900">
                            {p.price_amount > 0
                              ? new Intl.NumberFormat("vi-VN").format(
                                  p.price_amount
                                )
                              : "0"}
                          </span>
                          <span className="text-xs font-semibold text-slate-500 ml-1">
                            ₫ / tháng
                          </span>
                        </div>

                        <div className="space-y-3 pt-4 border-t border-slate-100 text-xs">
                          <div className="flex items-center gap-2 text-slate-700">
                            <Check className="w-4 h-4 text-emerald-600 shrink-0" />
                            <span>
                              {p.total_duration_limit_minutes > 10000
                                ? "Không giới hạn thời lượng họp"
                                : `${p.total_duration_limit_minutes} phút ghi âm / tháng`}
                            </span>
                          </div>

                          <div className="flex items-center gap-2 text-slate-700">
                            <Check className="w-4 h-4 text-emerald-600 shrink-0" />
                            <span>
                              Xuất Word (.docx), SRT, VTT, JSON
                            </span>
                          </div>

                          <div className="flex items-center gap-2 text-slate-700">
                            <Check className="w-4 h-4 text-emerald-600 shrink-0" />
                            <span>Trợ lý AI hỏi đáp theo ngữ cảnh</span>
                          </div>

                          {p.slug !== "free" && (
                            <div className="flex items-center gap-2 text-slate-700 font-medium">
                              <Sparkles className="w-4 h-4 text-emerald-600 shrink-0" />
                              <span>Phân tách người nói (Diarization)</span>
                            </div>
                          )}
                        </div>
                      </div>

                      <div className="mt-8 pt-4">
                        {isCurrent ? (
                          <button
                            disabled
                            className="w-full py-2.5 rounded-xl text-xs font-bold bg-slate-100 text-slate-400 cursor-not-allowed"
                          >
                            Gói Hiện Tại
                          </button>
                        ) : isFree ? (
                          <button
                            disabled
                            className="w-full py-2.5 rounded-xl text-xs font-bold border border-slate-200 text-slate-500"
                          >
                            Mặc Định
                          </button>
                        ) : (
                          <button
                            onClick={() => handleCheckout(p.slug)}
                            disabled={checkingOutSlug === p.slug}
                            className={`w-full py-2.5 rounded-xl text-xs font-bold flex items-center justify-center gap-2 transition ${
                              isPro
                                ? "bg-emerald-600 hover:bg-emerald-700 text-white shadow-sm"
                                : "bg-slate-900 hover:bg-slate-800 text-white"
                            }`}
                          >
                            {checkingOutSlug === p.slug ? (
                              <Loader2 className="w-4 h-4 animate-spin" />
                            ) : (
                              <>
                                <span>Thanh Toán VietQR</span>
                                <ArrowRight className="w-3.5 h-3.5" />
                              </>
                            )}
                          </button>
                        )}
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        </div>
      </div>

      <VietQRModal
        isOpen={isQrOpen}
        onClose={() => setIsQrOpen(false)}
        checkout={checkoutData}
        onPaymentSuccess={() => {
          if (onPlanUpgraded) {
            onPlanUpgraded();
          }
        }}
      />
    </>
  );
}

"use client";

import React, { useState } from "react";
import { X, Copy, Check, QrCode, AlertCircle, CheckCircle2, Loader2 } from "lucide-react";
import { useOrderStatus } from "@/hooks/useSubscription";
import type { CheckoutDetails } from "@/types/api";

interface VietQRModalProps {
  isOpen: boolean;
  onClose: () => void;
  checkout: CheckoutDetails | null;
}

export function VietQRModal({ isOpen, onClose, checkout }: VietQRModalProps) {
  const [copiedField, setCopiedField] = useState<string | null>(null);
  const order = useOrderStatus(isOpen && checkout ? checkout.order_code : null);
  const orderStatus = order.data?.status === "completed" ? "completed" : "pending";

  if (!isOpen || !checkout) return null;

  const copyToClipboard = async (text: string, field: string): Promise<void> => {
    try {
      await navigator.clipboard.writeText(text);
      setCopiedField(field);
      setTimeout(() => setCopiedField(null), 2000);
    } catch {
      setCopiedField(null);
    }
  };

  const formattedAmount = new Intl.NumberFormat("vi-VN", {
    style: "currency",
    currency: "VND",
  }).format(checkout.amount);

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/50 backdrop-blur-sm animate-in fade-in">
      <div className="bg-white rounded-2xl max-w-lg w-full border border-slate-200 shadow-xl overflow-hidden">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-slate-100 bg-slate-50">
          <div className="flex items-center gap-2.5">
            <div className="p-2 rounded-lg bg-emerald-600 text-white">
              <QrCode className="w-4 h-4" />
            </div>
            <div>
              <h2 className="text-base font-bold text-slate-900">
                Thanh Toán VietQR
              </h2>
              <p className="text-xs text-slate-600">Mã đơn: {checkout.order_code}</p>
            </div>
          </div>
          <button
            onClick={onClose}
            aria-label="Đóng"
            className="p-1 rounded-lg text-slate-500 hover:text-slate-800 hover:bg-slate-200/60 transition"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Content */}
        <div className="p-6">
          {orderStatus === "completed" ? (
            <div className="py-8 text-center space-y-4">
              <div className="w-16 h-16 mx-auto rounded-full bg-emerald-100 text-emerald-600 flex items-center justify-center">
                <CheckCircle2 className="w-10 h-10" />
              </div>
              <div>
                <h3 className="text-lg font-bold text-slate-900">
                  Thanh Toán Thành Công
                </h3>
              </div>
              <button
                onClick={onClose}
                className="mt-4 px-6 py-2.5 text-sm font-semibold rounded-xl text-white bg-slate-900 hover:bg-slate-800 transition"
              >
                Đóng
              </button>
            </div>
          ) : (
            <div className="space-y-6">
              {/* QR Image Box */}
              <div className="flex flex-col items-center justify-center p-4 rounded-xl border border-slate-200 bg-slate-50">
                {/* eslint-disable-next-line @next/next/no-img-element */}
                <img
                  src={checkout.qr_url}
                  alt="Mã VietQR Chuyển Khoản"
                  className="w-56 h-56 object-contain rounded-lg shadow-sm bg-white p-2"
                />
                <div className="flex items-center gap-2 mt-3 text-xs font-semibold text-emerald-700 bg-emerald-50 px-3 py-1 rounded-full border border-emerald-200">
                  <Loader2 className="w-3.5 h-3.5 animate-spin text-emerald-600" />
                  <span>Đang chờ chuyển khoản</span>
                </div>
              </div>

              {/* Bank Details Table */}
              <div className="space-y-2.5 text-xs">
                <div className="flex items-center justify-between p-2.5 rounded-lg bg-slate-50 border border-slate-100">
                  <span className="text-slate-700 font-medium">Ngân Hàng:</span>
                  <span className="font-bold text-slate-800">{checkout.bank_code}</span>
                </div>

                <div className="flex items-center justify-between p-2.5 rounded-lg bg-slate-50 border border-slate-100">
                  <span className="text-slate-700 font-medium">Chủ Tài Khoản:</span>
                  <span className="font-bold text-slate-800">{checkout.account_name}</span>
                </div>

                <div className="flex items-center justify-between p-2.5 rounded-lg bg-slate-50 border border-slate-100">
                  <span className="text-slate-700 font-medium">Số Tài Khoản:</span>
                  <div className="flex items-center gap-2">
                    <span className="font-bold text-slate-900 font-mono">
                      {checkout.account_number}
                    </span>
                    <button
                      onClick={() => copyToClipboard(checkout.account_number, "acc")}
                      className="p-1 rounded hover:bg-slate-200 text-slate-600 transition"
                    >
                      {copiedField === "acc" ? (
                        <Check className="w-3.5 h-3.5 text-emerald-600" />
                      ) : (
                        <Copy className="w-3.5 h-3.5" />
                      )}
                    </button>
                  </div>
                </div>

                <div className="flex items-center justify-between p-2.5 rounded-lg bg-slate-50 border border-slate-100">
                  <span className="text-slate-700 font-medium">Số Tiền:</span>
                  <div className="flex items-center gap-2">
                    <span className="font-bold text-emerald-700 font-mono text-sm">
                      {formattedAmount}
                    </span>
                    <button
                      onClick={() =>
                        copyToClipboard(checkout.amount.toString(), "amount")
                      }
                      className="p-1 rounded hover:bg-slate-200 text-slate-600 transition"
                    >
                      {copiedField === "amount" ? (
                        <Check className="w-3.5 h-3.5 text-emerald-600" />
                      ) : (
                        <Copy className="w-3.5 h-3.5" />
                      )}
                    </button>
                  </div>
                </div>

                <div className="flex items-center justify-between p-2.5 rounded-lg bg-emerald-50/60 border border-emerald-200">
                  <span className="text-emerald-900 font-semibold">
                    Nội Dung Chuyển Khoản:
                  </span>
                  <div className="flex items-center gap-2">
                    <span className="font-extrabold text-emerald-900 font-mono text-sm">
                      {checkout.transfer_content}
                    </span>
                    <button
                      onClick={() =>
                        copyToClipboard(checkout.transfer_content, "content")
                      }
                      className="p-1 rounded hover:bg-emerald-200 text-emerald-800 transition"
                    >
                      {copiedField === "content" ? (
                        <Check className="w-3.5 h-3.5 text-emerald-700" />
                      ) : (
                        <Copy className="w-3.5 h-3.5" />
                      )}
                    </button>
                  </div>
                </div>
              </div>

              <div className="p-3 rounded-xl bg-amber-50 border border-amber-200 text-xs text-amber-900 flex items-start gap-2">
                <AlertCircle className="w-4 h-4 text-amber-600 shrink-0 mt-0.5" />
                <span>
                  Giữ nguyên nội dung chuyển khoản{" "}
                  <strong>{checkout.transfer_content}</strong>
                </span>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

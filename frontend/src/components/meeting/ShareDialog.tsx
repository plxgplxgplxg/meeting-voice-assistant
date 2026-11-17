"use client";

import React, { useEffect, useState } from "react";
import { AlertCircle, Check, Copy, Loader2, X } from "lucide-react";

interface ShareDialogProps {
  isOpen: boolean;
  shareUrl: string | null;
  isLoading: boolean;
  errorMessage: string | null;
  onRetry: () => void;
  onClose: () => void;
}

const COPIED_RESET_MS = 2000;

/**
 * Dialog showing the guest link of a meeting with a copy action.
 *
 * @param props - Link state, retry handler and close handler.
 * @returns The dialog, or null when closed.
 */
export function ShareDialog({
  isOpen,
  shareUrl,
  isLoading,
  errorMessage,
  onRetry,
  onClose,
}: ShareDialogProps) {
  const [copied, setCopied] = useState(false);
  const [copyFailed, setCopyFailed] = useState(false);

  useEffect(() => {
    if (!copied) return;
    const timer = setTimeout(() => setCopied(false), COPIED_RESET_MS);
    return () => clearTimeout(timer);
  }, [copied]);

  if (!isOpen) return null;

  const handleCopy = async (): Promise<void> => {
    if (!shareUrl) return;
    try {
      await navigator.clipboard.writeText(shareUrl);
      setCopyFailed(false);
      setCopied(true);
    } catch {
      setCopyFailed(true);
    }
  };

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-labelledby="share-dialog-title"
      className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/50 backdrop-blur-sm"
    >
      <div className="bg-white rounded-2xl max-w-md w-full border border-slate-200 shadow-xl p-6">
        <div className="flex items-center justify-between gap-3 mb-4">
          <div className="flex items-center gap-2">
            <h3
              id="share-dialog-title"
              className="text-base font-bold text-slate-900"
            >
              Chia Sẻ Cuộc Họp
            </h3>
            <span className="px-2 py-0.5 rounded-full text-xs font-semibold bg-slate-100 text-slate-700">
              Chỉ xem
            </span>
          </div>
          <button
            onClick={onClose}
            aria-label="Đóng"
            className="p-1 rounded-lg text-slate-500 hover:text-slate-800 hover:bg-slate-100 transition"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {isLoading && (
          <div className="flex items-center gap-2 py-3 text-sm text-slate-700">
            <Loader2 className="w-4 h-4 animate-spin text-emerald-600" />
            <span>Đang tạo liên kết</span>
          </div>
        )}

        {errorMessage && !isLoading && (
          <div className="p-3 rounded-xl bg-rose-50 border border-rose-200 flex items-center justify-between gap-3">
            <div className="flex items-center gap-2 text-sm text-rose-800">
              <AlertCircle className="w-4 h-4 text-rose-600 shrink-0" />
              <span>{errorMessage}</span>
            </div>
            <button
              onClick={onRetry}
              className="px-3 py-1.5 text-xs font-semibold rounded-lg bg-rose-600 text-white hover:bg-rose-700 transition shrink-0"
            >
              Thử Lại
            </button>
          </div>
        )}

        {shareUrl && !isLoading && (
          <>
            <div className="flex items-center gap-2 p-2 rounded-xl bg-slate-50 border border-slate-200">
              <input
                type="text"
                readOnly
                value={shareUrl}
                aria-label="Liên kết chia sẻ"
                className="flex-1 bg-transparent text-xs font-mono text-slate-800 focus:outline-none truncate"
              />
              <button
                onClick={handleCopy}
                className="px-3 py-1.5 rounded-lg bg-slate-900 text-white text-xs font-semibold hover:bg-slate-800 transition flex items-center gap-1.5 shrink-0"
              >
                {copied ? (
                  <>
                    <Check className="w-3.5 h-3.5" />
                    <span>Đã Chép</span>
                  </>
                ) : (
                  <>
                    <Copy className="w-3.5 h-3.5" />
                    <span>Sao Chép</span>
                  </>
                )}
              </button>
            </div>
            {copyFailed && (
              <p className="mt-2 text-xs font-medium text-rose-700">
                Không thể sao chép, hãy chọn và chép thủ công
              </p>
            )}
          </>
        )}
      </div>
    </div>
  );
}

"use client";

import React from "react";
import { AlertTriangle, Loader2, RefreshCw } from "lucide-react";
import { useRegenerateSummary, useSummary } from "@/hooks/useSummary";
import { getErrorMessage } from "@/lib/api";
import type { SummaryStatus } from "@/types/api";
import { ActionItemsPanel } from "./ActionItemsPanel";

interface SummaryPanelProps {
  meetingId: string;
  summaryStatus: SummaryStatus;
}

/**
 * Executive summary, key points and action items of a meeting.
 *
 * @param props - Meeting identifier and the state of its summary.
 * @returns The scrollable summary card.
 */
export function SummaryPanel({ meetingId, summaryStatus }: SummaryPanelProps) {
  const { data: summary, isLoading, isError, error } = useSummary(meetingId);
  const regenerate = useRegenerateSummary(meetingId);

  return (
    <div className="bg-white border border-slate-200 rounded-2xl p-5 shadow-sm space-y-6 h-full overflow-y-auto">
      {summaryStatus === "stale" && (
        <div className="p-3 rounded-xl bg-amber-50 border border-amber-200 flex items-center justify-between gap-3 text-sm font-semibold text-amber-900">
          <span className="flex items-center gap-2">
            <AlertTriangle className="w-4 h-4 text-amber-600 shrink-0" />
            <span>Tóm tắt đã cũ so với phiên âm</span>
          </span>
          <button
            onClick={() => regenerate.mutate()}
            disabled={regenerate.isPending}
            className="px-3 py-1.5 text-xs font-semibold rounded-lg bg-amber-600 text-white hover:bg-amber-700 disabled:opacity-50 transition flex items-center gap-1.5 shrink-0"
          >
            {regenerate.isPending ? (
              <Loader2 className="w-3.5 h-3.5 animate-spin" />
            ) : (
              <RefreshCw className="w-3.5 h-3.5" />
            )}
            <span>Tạo lại</span>
          </button>
        </div>
      )}

      {summaryStatus === "pending" && (
        <div className="p-3 rounded-xl bg-slate-50 border border-slate-200 flex items-center gap-2 text-sm font-semibold text-slate-800">
          <Loader2 className="w-4 h-4 animate-spin text-emerald-600" />
          <span>Đang tạo tóm tắt</span>
        </div>
      )}

      {regenerate.isError && (
        <p className="text-sm font-medium text-rose-700">
          {getErrorMessage(regenerate.error, "Không thể tạo lại tóm tắt.")}
        </p>
      )}

      {isLoading && <Loader2 className="w-4 h-4 animate-spin text-emerald-600" />}

      {isError && (
        <p className="text-sm font-medium text-rose-700">
          {getErrorMessage(error, "Không thể tải bản tóm tắt.")}
        </p>
      )}

      {!isLoading && !isError && (
        <>
          <section>
            <h3 className="text-sm font-bold text-slate-900 mb-2">Tóm Tắt</h3>
            <div className="p-3.5 rounded-xl bg-slate-50 border border-slate-200 text-sm text-slate-800 leading-relaxed">
              {summary?.executive_summary || "Chưa có tóm tắt"}
            </div>
          </section>

          <section>
            <h3 className="text-sm font-bold text-slate-900 mb-2">Điểm Chính</h3>
            {summary && summary.key_points.length > 0 ? (
              <ul className="space-y-2 text-sm text-slate-800">
                {summary.key_points.map((point, index) => (
                  <li key={index} className="flex items-start gap-2">
                    <span className="w-1.5 h-1.5 rounded-full bg-emerald-600 mt-2 shrink-0" />
                    <span>{point}</span>
                  </li>
                ))}
              </ul>
            ) : (
              <p className="text-sm text-slate-600">Chưa có dữ liệu</p>
            )}
          </section>
        </>
      )}

      <div className="pt-4 border-t border-slate-200">
        <ActionItemsPanel meetingId={meetingId} />
      </div>
    </div>
  );
}

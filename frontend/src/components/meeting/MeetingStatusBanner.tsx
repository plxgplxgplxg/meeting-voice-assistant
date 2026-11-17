"use client";

import React from "react";
import { AlertCircle, Loader2, RotateCcw } from "lucide-react";
import { useReprocessMeeting } from "@/hooks/useMeeting";
import { getErrorMessage } from "@/lib/api";
import { isProcessingStatus, statusLabel } from "@/lib/meeting-status";
import type { Meeting } from "@/types/api";

interface MeetingStatusBannerProps {
  meeting: Meeting;
}

/**
 * Live banner for a processing meeting, or failure banner with retry.
 *
 * @param props - The meeting whose status is shown.
 * @returns A banner, or null when the meeting needs none.
 */
export function MeetingStatusBanner({ meeting }: MeetingStatusBannerProps) {
  const reprocess = useReprocessMeeting(meeting.id);

  if (isProcessingStatus(meeting.status)) {
    return (
      <div className="p-4 rounded-2xl bg-amber-50 border border-amber-200 flex items-center justify-between shadow-sm">
        <div className="flex items-center gap-3">
          <span className="relative flex h-3 w-3">
            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-amber-400 opacity-75" />
            <span className="relative inline-flex rounded-full h-3 w-3 bg-amber-600" />
          </span>
          <h4 className="text-sm font-bold text-amber-950">
            {statusLabel(meeting.status)}
          </h4>
        </div>
        <Loader2 className="w-4 h-4 animate-spin text-amber-700" />
      </div>
    );
  }

  if (meeting.status !== "failed") return null;

  return (
    <div className="p-4 rounded-2xl bg-rose-50 border border-rose-200 flex items-center justify-between gap-4 shadow-sm">
      <div className="flex items-center gap-3">
        <AlertCircle className="w-4 h-4 text-rose-600 shrink-0" />
        <div>
          <h4 className="text-sm font-bold text-rose-950">Xử Lý Thất Bại</h4>
          {meeting.failure_reason && (
            <p className="text-xs text-rose-800 mt-0.5">{meeting.failure_reason}</p>
          )}
          {reprocess.isError && (
            <p className="text-xs font-semibold text-rose-900 mt-0.5">
              {getErrorMessage(reprocess.error, "Không thể xử lý lại cuộc họp.")}
            </p>
          )}
        </div>
      </div>
      <button
        onClick={() => reprocess.mutate()}
        disabled={reprocess.isPending}
        className="px-3.5 py-1.5 text-xs font-semibold rounded-xl bg-rose-600 text-white hover:bg-rose-700 transition shadow-sm flex items-center gap-1.5 disabled:opacity-60 shrink-0"
      >
        {reprocess.isPending ? (
          <Loader2 className="w-3.5 h-3.5 animate-spin" />
        ) : (
          <RotateCcw className="w-3.5 h-3.5" />
        )}
        <span>Thử Lại</span>
      </button>
    </div>
  );
}

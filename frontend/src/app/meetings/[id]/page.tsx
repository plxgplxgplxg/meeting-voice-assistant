"use client";

import React from "react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { AlertCircle, ArrowLeft, Loader2, RefreshCw } from "lucide-react";
import { MeetingHeader } from "@/components/meeting/MeetingHeader";
import { MeetingStatusBanner } from "@/components/meeting/MeetingStatusBanner";
import { MeetingWorkspace } from "@/components/meeting/MeetingWorkspace";
import { useMeeting } from "@/hooks/useMeeting";
import { getErrorMessage, isApiError } from "@/lib/api";
import { ShareTokenProvider } from "@/lib/share-token";

function MeetingDetail({ meetingId }: { meetingId: string }) {
  const { data: meeting, isLoading, error, refetch } = useMeeting(meetingId);

  if (isLoading) {
    return (
      <div className="py-24 flex justify-center">
        <Loader2 className="w-8 h-8 animate-spin text-emerald-600" />
      </div>
    );
  }

  if (!meeting) {
    const isDenied = isApiError(error) && error.status >= 400 && error.status < 500;
    return (
      <div className="max-w-md mx-auto py-16 text-center space-y-4">
        <AlertCircle className="w-10 h-10 text-rose-500 mx-auto" />
        <h2 className="text-lg font-bold text-slate-900">
          {isDenied ? "Không Tìm Thấy Cuộc Họp" : "Không Tải Được Cuộc Họp"}
        </h2>
        <p className="text-sm text-slate-700">
          {getErrorMessage(error, "Cuộc họp không tồn tại hoặc bạn không có quyền truy cập.")}
        </p>
        <div className="flex justify-center gap-2">
          {!isDenied && (
            <button
              onClick={() => void refetch()}
              className="inline-flex items-center gap-2 px-4 py-2 text-xs font-semibold rounded-xl border border-slate-200 bg-white text-slate-800 hover:bg-slate-50"
            >
              <RefreshCw className="w-3.5 h-3.5" />
              <span>Thử Lại</span>
            </button>
          )}
          <Link
            href="/"
            className="inline-flex items-center gap-2 px-4 py-2 text-xs font-semibold rounded-xl bg-slate-900 text-white hover:bg-slate-800"
          >
            <ArrowLeft className="w-3.5 h-3.5" />
            <span>Trang Chủ</span>
          </Link>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <MeetingHeader meeting={meeting} />
      <MeetingStatusBanner meeting={meeting} />
      <MeetingWorkspace meeting={meeting} />
    </div>
  );
}

export default function MeetingDetailPage({
  params,
}: {
  params: { id: string };
}) {
  const shareToken = useSearchParams().get("share");

  return (
    <ShareTokenProvider token={shareToken}>
      <MeetingDetail meetingId={params.id} />
    </ShareTokenProvider>
  );
}

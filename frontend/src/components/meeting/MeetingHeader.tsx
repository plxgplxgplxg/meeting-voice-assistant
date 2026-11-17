"use client";

import React, { useState } from "react";
import Link from "next/link";
import { ArrowLeft, Share2 } from "lucide-react";
import { useCreateShareLink } from "@/hooks/useMeeting";
import { useTranscript } from "@/hooks/useTranscript";
import { getErrorMessage } from "@/lib/api";
import { statusBadgeClasses, statusLabel } from "@/lib/meeting-status";
import { buildShareUrl } from "@/lib/share-token";
import type { Meeting } from "@/types/api";
import { ExportDropdown } from "./ExportDropdown";
import { ShareDialog } from "./ShareDialog";

interface MeetingHeaderProps {
  meeting: Meeting;
}

/**
 * Title bar of a meeting: back link, badges, metadata, share and export actions.
 *
 * @param props - The meeting to describe.
 * @returns The header with its share dialog.
 */
export function MeetingHeader({ meeting }: MeetingHeaderProps) {
  const transcript = useTranscript(meeting.id);
  const createShare = useCreateShareLink(meeting.id);
  const [isShareOpen, setIsShareOpen] = useState(false);

  const shareUrl = createShare.data
    ? buildShareUrl(meeting.id, createShare.data.share_token)
    : null;

  const handleOpenShare = (): void => {
    setIsShareOpen(true);
    createShare.mutate();
  };

  return (
    <>
      <div className="flex flex-wrap items-center justify-between gap-4 pb-4 border-b border-slate-200">
        <div className="flex items-center gap-3">
          <Link
            href="/"
            aria-label="Quay lại danh sách"
            className="p-2 rounded-xl border border-slate-200 hover:bg-slate-100 text-slate-700 transition"
          >
            <ArrowLeft className="w-4 h-4" />
          </Link>
          <div>
            <div className="flex flex-wrap items-center gap-2">
              <h1 className="text-xl font-bold text-slate-900 tracking-tight">
                {meeting.title}
              </h1>
              {meeting.is_demo && (
                <span className="text-xs font-bold px-2.5 py-0.5 rounded-full bg-violet-100 text-violet-800">
                  Dữ Liệu Mẫu
                </span>
              )}
              <span
                className={`text-xs font-bold px-2.5 py-0.5 rounded-full ${statusBadgeClasses(meeting.status)}`}
              >
                {statusLabel(meeting.status)}
              </span>
            </div>
            <div className="flex items-center gap-3 text-sm text-slate-600 mt-1">
              <span>Mã: {meeting.id.slice(0, 8)}</span>
              <span aria-hidden="true">•</span>
              <span>{new Date(meeting.created_at).toLocaleDateString("vi-VN")}</span>
              <span aria-hidden="true">•</span>
              <span>{transcript.data?.length ?? 0} lượt phát biểu</span>
            </div>
          </div>
        </div>

        <div className="flex items-center gap-2.5">
          <button
            onClick={handleOpenShare}
            className="flex items-center gap-1.5 px-3 py-2 text-xs font-semibold rounded-xl border border-slate-200 bg-white hover:bg-slate-50 text-slate-800 transition shadow-sm"
          >
            <Share2 className="w-3.5 h-3.5" />
            <span>Chia Sẻ</span>
          </button>

          <ExportDropdown meetingId={meeting.id} meetingTitle={meeting.title} />
        </div>
      </div>

      <ShareDialog
        isOpen={isShareOpen}
        shareUrl={shareUrl}
        isLoading={createShare.isPending}
        errorMessage={
          createShare.isError
            ? getErrorMessage(createShare.error, "Không thể tạo liên kết chia sẻ.")
            : null
        }
        onRetry={() => createShare.mutate()}
        onClose={() => setIsShareOpen(false)}
      />
    </>
  );
}

"use client";

import React from "react";
import { Download, FileText, Loader2, Trash2 } from "lucide-react";
import { useArtifacts } from "@/hooks/useArtifacts";
import { getErrorMessage } from "@/lib/api";
import type { ArtifactKind } from "@/types/api";

interface ArtifactsPanelProps {
  meetingId: string;
  canDelete: boolean;
}

const KIND_LABELS: Record<ArtifactKind, string> = {
  minutes_docx: "Biên bản",
  email_draft: "Email",
  srt: "Phụ đề",
  custom_md: "Tài liệu",
};

function formatSize(bytes: number): string {
  return bytes < 1024 * 1024 ? `${Math.max(1, Math.round(bytes / 1024))} KB` : `${(bytes / 1024 / 1024).toFixed(1)} MB`;
}

/**
 * Documents the assistant generated for the meeting, with download and delete.
 *
 * @param props - Meeting identifier and whether the viewer may delete (creator only).
 * @returns The artifacts list card.
 */
export function ArtifactsPanel({ meetingId, canDelete }: ArtifactsPanelProps) {
  const { artifacts, isLoading, error, download, remove } = useArtifacts(meetingId);
  const failure = download.error ?? remove.error;

  return (
    <div className="bg-white border border-slate-200 rounded-2xl p-5 shadow-sm space-y-3 h-full overflow-y-auto">
      {isLoading && <Loader2 className="w-4 h-4 animate-spin text-emerald-600" />}
      {error && <p className="text-sm text-rose-700">{getErrorMessage(error, "Không thể tải danh sách tài liệu.")}</p>}
      {failure && <p className="text-sm font-medium text-rose-700">{getErrorMessage(failure, "Thao tác thất bại.")}</p>}

      {!isLoading && !error && artifacts.length === 0 && (
        <p className="text-sm text-slate-600">Chưa có tài liệu nào</p>
      )}

      {artifacts.map((artifact) => (
        <div key={artifact.id} className="flex items-center gap-3 p-3 rounded-xl border border-slate-200">
          <FileText className="w-5 h-5 text-emerald-700 shrink-0" />
          <div className="flex-1 min-w-0">
            <p className="text-sm font-semibold text-slate-900 truncate">{artifact.title}</p>
            <p className="text-xs text-slate-500">
              {KIND_LABELS[artifact.kind]} • {formatSize(artifact.size_bytes)} •{" "}
              {new Date(artifact.created_at).toLocaleString("vi-VN")}
            </p>
          </div>
          <button
            onClick={() => download.mutate(artifact)}
            disabled={download.isPending}
            aria-label="Tải xuống"
            className="p-2 rounded-lg hover:bg-slate-100 text-slate-700 disabled:opacity-40"
          >
            <Download className="w-4 h-4" />
          </button>
          {canDelete && (
            <button
              onClick={() => {
                if (confirm("Xóa tài liệu này?")) remove.mutate(artifact.id);
              }}
              disabled={remove.isPending}
              aria-label="Xóa"
              className="p-2 rounded-lg hover:bg-rose-50 text-rose-600 disabled:opacity-40"
            >
              <Trash2 className="w-4 h-4" />
            </button>
          )}
        </div>
      ))}
    </div>
  );
}

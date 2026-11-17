"use client";

import React, { useState } from "react";
import {
  Download,
  FileText,
  FileCode,
  File,
  ChevronDown,
  Loader2,
  Check,
} from "lucide-react";
import { getErrorMessage } from "@/lib/api";
import { downloadMeetingExport } from "@/lib/api/meetings";
import type { ExportFormat } from "@/types/api";

interface ExportDropdownProps {
  meetingId: string;
  meetingTitle?: string;
}

const EXPORT_OPTIONS: { type: ExportFormat; label: string; icon: typeof File }[] = [
  { type: "docx", label: "Microsoft Word (.docx)", icon: FileText },
  { type: "txt", label: "Văn bản (.txt)", icon: File },
  { type: "srt", label: "Phụ đề SubRip (.srt)", icon: FileCode },
  { type: "vtt", label: "Phụ đề WebVTT (.vtt)", icon: FileCode },
  { type: "json", label: "Dữ liệu JSON (.json)", icon: FileCode },
];

export function ExportDropdown({
  meetingId,
  meetingTitle = "cuoc_hop",
}: ExportDropdownProps) {
  const [isOpen, setIsOpen] = useState(false);
  const [downloadingType, setDownloadingType] = useState<ExportFormat | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const handleDownload = async (type: ExportFormat) => {
    setDownloadingType(type);
    setErrorMessage(null);
    try {
      const sanitizedTitle = meetingTitle
        .toLowerCase()
        .replace(/[^a-z0-9]/gi, "_")
        .slice(0, 30);
      const filename = `${sanitizedTitle}_${type}.${type}`;
      await downloadMeetingExport(meetingId, type, filename);
      setIsOpen(false);
    } catch (error: unknown) {
      setErrorMessage(getErrorMessage(error, "Không thể tải tệp xuất biên bản."));
    } finally {
      setDownloadingType(null);
    }
  };

  return (
    <div className="relative">
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="flex items-center gap-2 px-3.5 py-2 text-xs font-semibold rounded-xl bg-slate-900 text-white hover:bg-slate-800 transition shadow-sm"
      >
        <Download className="w-3.5 h-3.5" />
        <span>Xuất Biên Bản</span>
        <ChevronDown className="w-3.5 h-3.5 text-slate-300" />
      </button>

      {isOpen && (
        <div className="absolute right-0 mt-1.5 w-64 rounded-2xl bg-white border border-slate-200 shadow-xl p-1.5 z-30 animate-in fade-in">
          {errorMessage && (
            <p className="px-3 py-1.5 text-xs font-medium text-rose-700">
              {errorMessage}
            </p>
          )}

          <div className="space-y-0.5">
            {EXPORT_OPTIONS.map((opt) => {
              const Icon = opt.icon;
              const isDownloading = downloadingType === opt.type;

              return (
                <button
                  key={opt.type}
                  onClick={() => handleDownload(opt.type)}
                  disabled={isDownloading}
                  className="w-full text-left p-2.5 rounded-xl hover:bg-slate-50 transition flex items-center gap-2.5 group disabled:opacity-50"
                >
                  <div className="p-1 rounded-lg bg-slate-100 group-hover:bg-emerald-50 group-hover:text-emerald-700 text-slate-600 transition shrink-0">
                    {isDownloading ? (
                      <Loader2 className="w-3.5 h-3.5 animate-spin text-emerald-600" />
                    ) : (
                      <Icon className="w-3.5 h-3.5" />
                    )}
                  </div>
                  <span className="block text-sm font-semibold text-slate-800 group-hover:text-emerald-900">
                    {opt.label}
                  </span>
                </button>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
}

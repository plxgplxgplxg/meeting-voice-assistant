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
import { downloadFile } from "@/lib/api";

interface ExportDropdownProps {
  meetingId: string;
  meetingTitle?: string;
}

const EXPORT_OPTIONS = [
  {
    type: "docx",
    label: "Microsoft Word (.docx)",
    description: "Bản in đẹp có bảng phân vai và tóm tắt",
    icon: FileText,
  },
  {
    type: "txt",
    label: "Văn bản thuần (.txt)",
    description: "Nội dung gọn nhẹ dễ lưu trữ",
    icon: File,
  },
  {
    type: "srt",
    label: "Phụ đề SubRip (.srt)",
    description: "Dùng chèn phụ đề video và phát lại",
    icon: FileCode,
  },
  {
    type: "vtt",
    label: "Phụ đề WebVTT (.vtt)",
    description: "Chuẩn phụ đề web HTML5",
    icon: FileCode,
  },
  {
    type: "json",
    label: "Dữ liệu JSON (.json)",
    description: "Đầy đủ timestamps và siêu dữ liệu",
    icon: FileCode,
  },
] as const;

export function ExportDropdown({
  meetingId,
  meetingTitle = "cuoc_hop",
}: ExportDropdownProps) {
  const [isOpen, setIsOpen] = useState(false);
  const [downloadingType, setDownloadingType] = useState<string | null>(null);

  const handleDownload = async (type: string) => {
    setDownloadingType(type);
    try {
      const sanitizedTitle = meetingTitle
        .toLowerCase()
        .replace(/[^a-z0-9]/gi, "_")
        .slice(0, 30);
      const filename = `${sanitizedTitle}_${type}.${type}`;
      await downloadFile(`/meetings/${meetingId}/exports/${type}`, filename);
      setIsOpen(false);
    } catch (err: any) {
      alert(err.message || "Không thể tải tệp xuất biên bản.");
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
        <ChevronDown className="w-3.5 h-3.5 text-slate-400" />
      </button>

      {isOpen && (
        <div className="absolute right-0 mt-1.5 w-64 rounded-2xl bg-white border border-slate-200 shadow-xl p-1.5 z-30 animate-in fade-in">
          <div className="px-3 py-1.5 text-[10px] font-bold text-slate-400 uppercase tracking-wider">
            Chọn định dạng tệp:
          </div>

          <div className="space-y-0.5">
            {EXPORT_OPTIONS.map((opt) => {
              const Icon = opt.icon;
              const isDownloading = downloadingType === opt.type;

              return (
                <button
                  key={opt.type}
                  onClick={() => handleDownload(opt.type)}
                  disabled={isDownloading}
                  className="w-full text-left p-2.5 rounded-xl hover:bg-slate-50 transition flex items-start gap-2.5 group disabled:opacity-50"
                >
                  <div className="p-1 rounded-lg bg-slate-100 group-hover:bg-emerald-50 group-hover:text-emerald-700 text-slate-600 transition shrink-0 mt-0.5">
                    {isDownloading ? (
                      <Loader2 className="w-3.5 h-3.5 animate-spin text-emerald-600" />
                    ) : (
                      <Icon className="w-3.5 h-3.5" />
                    )}
                  </div>
                  <div>
                    <span className="block text-xs font-bold text-slate-800 group-hover:text-emerald-900">
                      {opt.label}
                    </span>
                    <span className="block text-[11px] text-slate-400 mt-0.5">
                      {opt.description}
                    </span>
                  </div>
                </button>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
}

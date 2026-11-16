"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import {
  Plus,
  Search,
  UploadCloud,
  FileAudio,
  Calendar,
  Clock,
  Users,
  ChevronRight,
  Loader2,
  AlertCircle,
  PlayCircle,
  Sparkles,
} from "lucide-react";
import { fetchApi } from "@/lib/api";
import { useAuth } from "@/lib/auth-context";
import { formatDuration } from "@/lib/utils";
import { ProjectSelector, Project } from "@/components/project/ProjectSelector";

interface MeetingItem {
  id: string;
  title: string;
  status: "created" | "processing" | "completed" | "failed";
  duration_seconds: number;
  created_at: string;
  segments_count?: number;
}

export default function MeetingsDashboard() {
  const { user } = useAuth();
  const [meetings, setMeetings] = useState<MeetingItem[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [selectedProjectId, setSelectedProjectId] = useState<string | null>(null);
  const [selectedProject, setSelectedProject] = useState<Project | null>(null);

  const [searchQuery, setSearchQuery] = useState("");
  const [statusFilter, setStatusFilter] = useState<string>("all");

  // Upload Audio Modal
  const [isUploadOpen, setIsUploadOpen] = useState(false);
  const [audioFile, setAudioFile] = useState<File | null>(null);
  const [meetingTitle, setMeetingTitle] = useState("");
  const [isUploading, setIsUploading] = useState(false);
  const [uploadError, setUploadError] = useState<string | null>(null);

  const fetchMeetings = async () => {
    try {
      let path = "/meetings";
      if (selectedProjectId) {
        path = `/projects/${selectedProjectId}/meetings`;
      }
      const data = await fetchApi<MeetingItem[]>(path);
      setMeetings(data);
    } catch {
      setMeetings([]);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchMeetings();
  }, [selectedProjectId, user]);

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      setAudioFile(file);
      if (!meetingTitle) {
        setMeetingTitle(file.name.replace(/\.[^/.]+$/, ""));
      }
    }
  };

  const handleUploadAudio = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!audioFile) return;

    setUploadError(null);
    setIsUploading(true);

    try {
      // 1. Create meeting first
      const newMeeting = await fetchApi<{ id: string }>("/meetings", {
        method: "POST",
        body: JSON.stringify({
          title: meetingTitle.trim() || audioFile.name,
          project_id: selectedProjectId,
        }),
      });

      // 2. Upload audio file multipart
      const formData = new FormData();
      formData.append("file", audioFile);

      await fetchApi(`/audio/meetings/${newMeeting.id}/upload`, {
        method: "POST",
        body: formData,
      });

      setIsUploadOpen(false);
      setAudioFile(null);
      setMeetingTitle("");

      // Redirect directly to the meeting studio
      window.location.href = `/meetings/${newMeeting.id}`;
    } catch (err: any) {
      setUploadError(err.message || "Tải lên tệp âm thanh thất bại.");
    } finally {
      setIsUploading(false);
    }
  };

  // Filter meetings
  const filteredMeetings = meetings.filter((m) => {
    if (statusFilter !== "all" && m.status !== statusFilter) return false;
    if (searchQuery.trim()) {
      return m.title.toLowerCase().includes(searchQuery.toLowerCase());
    }
    return true;
  });

  const activeProcessingMeeting = meetings.find((m) => m.status === "processing");

  return (
    <div className="space-y-6">
      {/* Workspace & Action Header */}
      <div className="flex flex-wrap items-center justify-between gap-4 pb-4 border-b border-slate-200">
        <div className="flex items-center gap-3">
          <ProjectSelector
            selectedProjectId={selectedProjectId}
            onSelectProject={(id, p) => {
              setSelectedProjectId(id);
              setSelectedProject(p);
            }}
          />

          <div className="h-5 w-px bg-slate-200" />

          <div>
            <h1 className="text-xl font-bold text-slate-900">
              {selectedProject ? selectedProject.name : "Tất Cả Cuộc Họp"}
            </h1>
            <p className="text-xs text-slate-500">
              {selectedProject?.description || "Quản lý và tra cứu biên bản các phiên làm việc"}
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2.5">
          <button
            onClick={() => setIsUploadOpen(true)}
            className="flex items-center gap-2 px-4 py-2 text-xs font-semibold rounded-xl bg-slate-900 text-white hover:bg-slate-800 transition shadow-sm"
          >
            <UploadCloud className="w-4 h-4" />
            <span>Tải Lên File Ghi Âm</span>
          </button>
        </div>
      </div>

      {/* Real-time Running Job Mission Control Banner (clean-minimalist Rule 4) */}
      {activeProcessingMeeting && (
        <div className="p-4 rounded-2xl border border-amber-200 bg-amber-50/70 shadow-xs flex items-center justify-between">
          <div className="flex items-center gap-3">
            <span className="relative flex h-3 w-3">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-amber-400 opacity-75"></span>
              <span className="relative inline-flex rounded-full h-3 w-3 bg-amber-600"></span>
            </span>
            <div>
              <h3 className="text-xs font-bold text-amber-950">
                Tiến trình đang xử lý: {activeProcessingMeeting.title}
              </h3>
              <p className="text-[11px] text-amber-800 mt-0.5">
                Mô hình Whisper ASR & Diarization đang phân tích âm thanh trong nền
              </p>
            </div>
          </div>

          <Link
            href={`/meetings/${activeProcessingMeeting.id}`}
            className="px-3.5 py-1.5 text-xs font-semibold rounded-xl bg-amber-600 text-white hover:bg-amber-700 transition shadow-xs flex items-center gap-1.5"
          >
            <span>Xem Tiến Trình</span>
            <ChevronRight className="w-3.5 h-3.5" />
          </Link>
        </div>
      )}

      {/* Filters Toolbar */}
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="relative flex-1 max-w-sm">
          <Search className="w-4 h-4 text-slate-400 absolute left-3.5 top-1/2 -translate-y-1/2" />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Tìm theo tiêu đề cuộc họp..."
            className="w-full pl-10 pr-4 py-2 text-xs bg-white border border-slate-200 rounded-xl text-slate-900 focus:outline-none focus:ring-1 focus:ring-slate-400"
          />
        </div>

        <div className="flex items-center bg-slate-100 p-1 rounded-xl text-xs font-semibold">
          {[
            { key: "all", label: "Tất Cả" },
            { key: "completed", label: "Đã Xử Lý" },
            { key: "processing", label: "Đang Xử Lý" },
          ].map((tab) => (
            <button
              key={tab.key}
              onClick={() => setStatusFilter(tab.key)}
              className={`px-3 py-1.5 rounded-lg transition ${
                statusFilter === tab.key
                  ? "bg-white text-slate-900 shadow-xs"
                  : "text-slate-600 hover:text-slate-900"
              }`}
            >
              {tab.label}
            </button>
          ))}
        </div>
      </div>

      {/* Meeting Cards Grid */}
      {isLoading ? (
        <div className="py-20 flex justify-center text-slate-400">
          <Loader2 className="w-7 h-7 animate-spin text-emerald-600" />
        </div>
      ) : filteredMeetings.length === 0 ? (
        <div className="py-16 text-center border border-dashed border-slate-200 rounded-2xl bg-white p-8">
          <FileAudio className="w-10 h-10 text-slate-300 mx-auto mb-3" />
          <h3 className="text-sm font-bold text-slate-700">Chưa có cuộc họp nào</h3>
          <p className="text-xs text-slate-400 mt-1 mb-4">
            Tải lên tệp âm thanh hoặc bắt đầu ghi âm trực tiếp để tạo cuộc họp mới.
          </p>
          <button
            onClick={() => setIsUploadOpen(true)}
            className="inline-flex items-center gap-1.5 px-4 py-2 text-xs font-semibold rounded-xl bg-slate-900 text-white hover:bg-slate-800 transition"
          >
            <UploadCloud className="w-4 h-4" />
            <span>Tải Lên Tệp Đầu Tiên</span>
          </button>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {filteredMeetings.map((item) => (
            <Link
              key={item.id}
              href={`/meetings/${item.id}`}
              className="p-5 bg-white border border-slate-200 hover:border-slate-300 rounded-2xl hover:shadow-md transition flex flex-col justify-between group"
            >
              <div>
                <div className="flex items-center justify-between mb-3">
                  <span className="text-[11px] font-semibold text-slate-400 font-mono">
                    #{item.id.slice(0, 8)}
                  </span>
                  <span
                    className={`text-[10px] font-bold px-2 py-0.5 rounded-full uppercase tracking-wider ${
                      item.status === "completed"
                        ? "bg-emerald-100 text-emerald-800"
                        : item.status === "processing"
                        ? "bg-amber-100 text-amber-800 animate-pulse"
                        : "bg-slate-100 text-slate-700"
                    }`}
                  >
                    {item.status === "completed"
                      ? "Đã Xong"
                      : item.status === "processing"
                      ? "Đang Phân Tích"
                      : "Khởi Tạo"}
                  </span>
                </div>

                <h3 className="text-sm font-bold text-slate-900 group-hover:text-emerald-700 transition line-clamp-2">
                  {item.title}
                </h3>
              </div>

              <div className="flex items-center justify-between text-xs text-slate-500 mt-5 pt-3 border-t border-slate-100">
                <div className="flex items-center gap-1.5">
                  <Clock className="w-3.5 h-3.5 text-slate-400" />
                  <span>{formatDuration(item.duration_seconds || 0)}</span>
                </div>

                <div className="flex items-center gap-1 text-slate-400">
                  <Calendar className="w-3.5 h-3.5" />
                  <span>{new Date(item.created_at).toLocaleDateString("vi-VN")}</span>
                </div>
              </div>
            </Link>
          ))}
        </div>
      )}

      {/* Modal: Upload Audio File */}
      {isUploadOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/50 backdrop-blur-sm animate-in fade-in">
          <div className="bg-white rounded-2xl max-w-lg w-full border border-slate-200 shadow-2xl p-6">
            <h3 className="text-base font-bold text-slate-900 pb-3 border-b border-slate-100">
              Tải Lên File Ghi Âm Cuộc Họp
            </h3>

            {uploadError && (
              <div className="mt-4 p-3 rounded-xl bg-rose-50 border border-rose-200 text-xs text-rose-800 flex items-center gap-2">
                <AlertCircle className="w-4 h-4 text-rose-600 shrink-0" />
                <span>{uploadError}</span>
              </div>
            )}

            <form onSubmit={handleUploadAudio} className="mt-4 space-y-4">
              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1.5">
                  Tiêu Đề Cuộc Họp
                </label>
                <input
                  type="text"
                  required
                  value={meetingTitle}
                  onChange={(e) => setMeetingTitle(e.target.value)}
                  placeholder="Ví dụ: Họp Đánh Giá Tiến Độ Tuần 6"
                  className="w-full px-3.5 py-2 text-sm bg-white border border-slate-300 rounded-xl text-slate-900 focus:outline-none focus:ring-2 focus:ring-emerald-600/20 focus:border-emerald-600"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1.5">
                  Chọn Tệp Âm Thanh (.mp3, .wav, .m4a)
                </label>
                <div className="border-2 border-dashed border-slate-200 hover:border-slate-300 rounded-xl p-6 text-center cursor-pointer bg-slate-50/50 relative">
                  <input
                    type="file"
                    accept="audio/*,.mp3,.wav,.m4a,.aac,.flac,.ogg"
                    required
                    onChange={handleFileChange}
                    className="absolute inset-0 opacity-0 cursor-pointer w-full h-full"
                  />
                  <FileAudio className="w-8 h-8 text-emerald-600 mx-auto mb-2" />
                  {audioFile ? (
                    <div className="text-xs font-bold text-slate-800">
                      {audioFile.name} (
                      {Math.round(audioFile.size / (1024 * 1024) * 10) / 10} MB)
                    </div>
                  ) : (
                    <div>
                      <span className="text-xs font-semibold text-slate-700">
                        Kéo thả file vào đây hoặc bấm để chọn tệp
                      </span>
                      <p className="text-[11px] text-slate-400 mt-1">
                        Hỗ trợ MP3, WAV, M4A, AAC, OGG
                      </p>
                    </div>
                  )}
                </div>
              </div>

              <div className="flex justify-end gap-2 pt-2">
                <button
                  type="button"
                  onClick={() => setIsUploadOpen(false)}
                  className="px-4 py-2 text-xs font-semibold rounded-xl text-slate-600 hover:bg-slate-100 transition"
                >
                  Hủy
                </button>
                <button
                  type="submit"
                  disabled={isUploading || !audioFile}
                  className="px-5 py-2 text-xs font-semibold rounded-xl text-white bg-slate-900 hover:bg-slate-800 disabled:opacity-50 transition flex items-center gap-2"
                >
                  {isUploading ? (
                    <>
                      <Loader2 className="w-3.5 h-3.5 animate-spin" />
                      <span>Đang Tải Lên...</span>
                    </>
                  ) : (
                    <span>Bắt Đầu Xử Lý</span>
                  )}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}

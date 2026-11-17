"use client";

import React, { useEffect, useRef, useState } from "react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import {
  ArrowLeft,
  Share2,
  Trash2,
  Sparkles,
  ListTodo,
  MessageSquare,
  CheckCircle2,
  Clock,
  Loader2,
  Copy,
  Check,
  AlertCircle,
  RotateCcw,
} from "lucide-react";
import { buildBackendUrl, fetchApi, setShareToken } from "@/lib/api";
import {
  MeetingStatus,
  isProcessingStatus,
  statusBadgeClasses,
  statusLabel,
} from "@/lib/meeting-status";
import {
  SpeakerTimeline,
  SpeakerTimelineHandle,
  TimelineSegment,
} from "@/components/meeting/SpeakerTimeline";
import { TranscriptFeed } from "@/components/meeting/TranscriptFeed";
import { AssistantChatPane } from "@/components/meeting/AssistantChatPane";
import { ExportDropdown } from "@/components/meeting/ExportDropdown";

interface MeetingDetail {
  id: string;
  title: string;
  status: MeetingStatus;
  is_demo?: boolean;
  failure_stage?: string | null;
  failure_reason?: string | null;
  duration_seconds: number;
  created_at: string;
  created_by?: string;
  share_token?: string;
  share_permission?: string;
}

interface SummaryData {
  id: string;
  executive_summary: string;
  key_points: string[];
}

interface ActionItem {
  id: string;
  description: string;
  assignee: string;
  status: "pending" | "completed";
}

export default function MeetingDetailPage({
  params,
}: {
  params: { id: string };
}) {
  const meetingId = params.id;
  const searchParams = useSearchParams();
  const shareToken = searchParams.get("share");
  const timelineRef = useRef<SpeakerTimelineHandle | null>(null);

  const [meeting, setMeeting] = useState<MeetingDetail | null>(null);
  const [segments, setSegments] = useState<TimelineSegment[]>([]);
  const [summary, setSummary] = useState<SummaryData | null>(null);
  const [actionItems, setActionItems] = useState<ActionItem[]>([]);
  const [currentTime, setCurrentTime] = useState(0);
  const [isLoading, setIsLoading] = useState(true);

  // Tab: 'summary' or 'chat'
  const [activeTab, setActiveTab] = useState<"summary" | "chat">("summary");

  // Share Link Modal
  const [isShareOpen, setIsShareOpen] = useState(false);
  const [shareLink, setShareLink] = useState("");
  const [copiedLink, setCopiedLink] = useState(false);

  const [audioUrl, setAudioUrl] = useState<string | null>(null);
  const [isRetrying, setIsRetrying] = useState(false);

  const loadMeetingData = async () => {
    try {
      const shareQuery = shareToken
        ? `?share=${encodeURIComponent(shareToken)}`
        : "";
      const m = await fetchApi<MeetingDetail>(
        `/meetings/${meetingId}${shareQuery}`
      );
      setMeeting(m);

      const segs = await fetchApi<TimelineSegment[]>(`/meetings/${meetingId}/transcript`);
      setSegments(segs);

      try {
        const sum = await fetchApi<SummaryData>(
          `/meetings/${meetingId}/summary`
        );
        setSummary(sum);
      } catch {
        // Summary might not exist yet if still processing
      }

      try {
        const actions = await fetchApi<ActionItem[]>(
          `/meetings/${meetingId}/action-items`
        );
        setActionItems(actions);
      } catch {
        // Optional action items
      }
    } catch (err: any) {
      // Handled in UI
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    setShareToken(shareToken);
    loadMeetingData();
    return () => setShareToken(null);
  }, [meetingId, shareToken]);

  const loadAudioUrl = async () => {
    try {
      const res = await fetchApi<{ url: string }>(
        `/meetings/${meetingId}/audio/stream-url`
      );
      setAudioUrl(buildBackendUrl(res.url));
    } catch {
      setAudioUrl(null);
    }
  };

  useEffect(() => {
    if (meeting?.status === "ready") loadAudioUrl();
  }, [meeting?.status, meetingId]);

  const handleRetryProcessing = async () => {
    setIsRetrying(true);
    try {
      await fetchApi(`/meetings/${meetingId}/reprocess`, { method: "POST" });
      await loadMeetingData();
    } catch (err: any) {
      alert(err.message || "Không thể xử lý lại cuộc họp.");
    } finally {
      setIsRetrying(false);
    }
  };

  // Polling if meeting is processing
  useEffect(() => {
    if (!meeting || !isProcessingStatus(meeting.status)) return;
    const interval = setInterval(() => {
      loadMeetingData();
    }, 4000);
    return () => clearInterval(interval);
  }, [meeting?.status]);

  const handleSeek = (seconds: number) => {
    timelineRef.current?.seekTo(seconds, { play: true });
    setCurrentTime(seconds);
  };

  const handleUpdateSegment = async (segmentId: string, newContent: string) => {
    await fetchApi(`/meetings/${meetingId}/transcript/segments/${segmentId}`, {
      method: "PATCH",
      body: JSON.stringify({ content: newContent }),
    });
    setSegments((prev) =>
      prev.map((s) => (s.id === segmentId ? { ...s, content: newContent } : s))
    );
  };

  const handleRenameSpeaker = async (oldSpeaker: string, newSpeaker: string) => {
    await fetchApi(`/meetings/${meetingId}/transcript/rename-speaker`, {
      method: "POST",
      body: JSON.stringify({
        old_speaker_label: oldSpeaker,
        new_speaker_label: newSpeaker,
      }),
    });
    setSegments((prev) =>
      prev.map((s) =>
        s.speaker_label === oldSpeaker ? { ...s, speaker_label: newSpeaker } : s
      )
    );
  };

  const handleDeleteSegment = async (segmentId: string) => {
    if (!confirm("Bạn có chắc chắn muốn xóa đoạn này không?")) return;
    await fetchApi(`/meetings/${meetingId}/transcript/delete-segments`, {
      method: "POST",
      body: JSON.stringify({ segment_ids: [segmentId] }),
    });
    setSegments((prev) => prev.filter((s) => s.id !== segmentId));
  };

  const handleGenerateShareLink = async () => {
    try {
      const res = await fetchApi<{ share_token: string; share_url: string }>(
        `/meetings/${meetingId}/share?permission=viewer`,
        { method: "POST" }
      );
      const fullUrl = `${window.location.origin}/meetings/${meetingId}?share=${res.share_token}`;
      setShareLink(fullUrl);
      setIsShareOpen(true);
    } catch (err: any) {
      alert(err.message || "Không thể tạo liên kết chia sẻ.");
    }
  };

  const copyShareLink = () => {
    navigator.clipboard.writeText(shareLink);
    setCopiedLink(true);
    setTimeout(() => setCopiedLink(false), 2000);
  };

  if (isLoading) {
    return (
      <div className="py-24 flex flex-col items-center justify-center text-slate-400 gap-3">
        <Loader2 className="w-8 h-8 animate-spin text-emerald-600" />
        <span className="text-xs font-semibold">Đang tải dữ liệu cuộc họp...</span>
      </div>
    );
  }

  if (!meeting) {
    return (
      <div className="max-w-md mx-auto py-16 text-center space-y-4">
        <AlertCircle className="w-10 h-10 text-rose-500 mx-auto" />
        <h2 className="text-lg font-bold text-slate-900">
          Không Tìm Thấy Cuộc Họp
        </h2>
        <p className="text-xs text-slate-500">
          Cuộc họp không tồn tại hoặc bạn không có quyền truy cập.
        </p>
        <Link
          href="/"
          className="inline-flex items-center gap-2 px-4 py-2 text-xs font-semibold rounded-xl bg-slate-900 text-white hover:bg-slate-800"
        >
          <ArrowLeft className="w-3.5 h-3.5" />
          <span>Về Trang Chủ</span>
        </Link>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Top Header Bar */}
      <div className="flex flex-wrap items-center justify-between gap-4 pb-4 border-b border-slate-200">
        <div className="flex items-center gap-3">
          <Link
            href="/"
            className="p-2 rounded-xl border border-slate-200 hover:bg-slate-100 text-slate-600 transition"
            title="Quay lại danh sách"
          >
            <ArrowLeft className="w-4 h-4" />
          </Link>
          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-xl font-bold text-slate-900 tracking-tight">
                {meeting.title}
              </h1>
              {meeting.is_demo && (
                <span className="text-[11px] font-bold px-2.5 py-0.5 rounded-full bg-violet-100 text-violet-800">
                  Dữ Liệu Mẫu
                </span>
              )}
              <span
                className={`text-[11px] font-bold px-2.5 py-0.5 rounded-full ${statusBadgeClasses(meeting.status)}`}
              >
                {statusLabel(meeting.status)}
              </span>
            </div>
            <div className="flex items-center gap-3 text-xs text-slate-500 mt-1">
              <span>Mã: {meeting.id.slice(0, 8)}</span>
              <span>•</span>
              <span>
                Ngày họp: {new Date(meeting.created_at).toLocaleDateString("vi-VN")}
              </span>
              <span>•</span>
              <span>{segments.length} lượt phát biểu</span>
            </div>
          </div>
        </div>

        <div className="flex items-center gap-2.5">
          <button
            onClick={handleGenerateShareLink}
            className="flex items-center gap-1.5 px-3 py-2 text-xs font-semibold rounded-xl border border-slate-200 bg-white hover:bg-slate-50 text-slate-700 transition shadow-sm"
          >
            <Share2 className="w-3.5 h-3.5" />
            <span>Chia Sẻ</span>
          </button>

          <ExportDropdown
            meetingId={meeting.id}
            meetingTitle={meeting.title}
          />
        </div>
      </div>

      {/* Processing Live Banner (clean-minimalist Rule 4) */}
      {isProcessingStatus(meeting.status) && (
        <div className="p-4 rounded-2xl bg-amber-50/80 border border-amber-200 flex items-center justify-between shadow-xs">
          <div className="flex items-center gap-3">
            <span className="relative flex h-3 w-3">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-amber-400 opacity-75"></span>
              <span className="relative inline-flex rounded-full h-3 w-3 bg-amber-600"></span>
            </span>
            <div>
              <h4 className="text-xs font-bold text-amber-950">
                {statusLabel(meeting.status)}
              </h4>
            </div>
          </div>
          <Loader2 className="w-4 h-4 animate-spin text-amber-700" />
        </div>
      )}

      {meeting.status === "failed" && (
        <div className="p-4 rounded-2xl bg-rose-50/80 border border-rose-200 flex items-center justify-between shadow-xs">
          <div className="flex items-center gap-3">
            <AlertCircle className="w-4 h-4 text-rose-600" />
            <div>
              <h4 className="text-xs font-bold text-rose-950">Xử Lý Thất Bại</h4>
              {meeting.failure_reason && (
                <p className="text-[11px] text-rose-800 mt-0.5">
                  {meeting.failure_reason}
                </p>
              )}
            </div>
          </div>
          <button
            onClick={handleRetryProcessing}
            disabled={isRetrying}
            className="px-3.5 py-1.5 text-xs font-semibold rounded-xl bg-rose-600 text-white hover:bg-rose-700 transition shadow-xs flex items-center gap-1.5 disabled:opacity-60"
          >
            {isRetrying ? (
              <Loader2 className="w-3.5 h-3.5 animate-spin" />
            ) : (
              <RotateCcw className="w-3.5 h-3.5" />
            )}
            <span>Thử Lại</span>
          </button>
        </div>
      )}

      {/* Audio Timeline Scrubber */}
      <SpeakerTimeline
        ref={timelineRef}
        audioUrl={audioUrl}
        onAudioError={loadAudioUrl}
        durationSec={meeting.duration_seconds}
        segments={segments}
        currentTime={currentTime}
        onTimeUpdate={setCurrentTime}
        onSegmentClick={(seg) => handleSeek(seg.start_time)}
      />

      {/* Split Workspace: Left = Transcript Feed, Right = AI Summary & RAG Assistant */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Left Column: Transcript */}
        <div className="lg:col-span-7 flex flex-col h-[700px]">
          <TranscriptFeed
            segments={segments}
            currentTime={currentTime}
            onSegmentClick={(seg) => handleSeek(seg.start_time)}
            onUpdateContent={handleUpdateSegment}
            onRenameSpeaker={handleRenameSpeaker}
            onDeleteSegment={handleDeleteSegment}
          />
        </div>

        {/* Right Column: Flat 2-Tab Switcher (Summary & RAG) */}
        <div className="lg:col-span-5 flex flex-col h-[700px]">
          <div className="flex items-center gap-2 p-1 bg-slate-200/60 rounded-xl mb-3">
            <button
              onClick={() => setActiveTab("summary")}
              className={`flex-1 py-1.5 px-3 rounded-lg text-xs font-bold transition flex items-center justify-center gap-2 ${
                activeTab === "summary"
                  ? "bg-white text-slate-900 shadow-xs"
                  : "text-slate-600 hover:text-slate-900"
              }`}
            >
              <Sparkles className="w-3.5 h-3.5 text-emerald-600" />
              <span>Tóm Tắt & Việc Cần Làm</span>
            </button>

            <button
              onClick={() => setActiveTab("chat")}
              className={`flex-1 py-1.5 px-3 rounded-lg text-xs font-bold transition flex items-center justify-center gap-2 ${
                activeTab === "chat"
                  ? "bg-white text-slate-900 shadow-xs"
                  : "text-slate-600 hover:text-slate-900"
              }`}
            >
              <MessageSquare className="w-3.5 h-3.5 text-emerald-600" />
              <span>Trợ Lý Hỏi Đáp (RAG)</span>
            </button>
          </div>

          <div className="flex-1 overflow-hidden">
            {activeTab === "summary" ? (
              <div className="bg-white border border-slate-200 rounded-2xl p-5 shadow-sm space-y-6 h-full overflow-y-auto">
                {/* Executive Summary */}
                <div>
                  <h3 className="text-xs font-bold uppercase tracking-wider text-slate-400 mb-2">
                    Tóm Tắt Điều Hành
                  </h3>
                  <div className="p-3.5 rounded-xl bg-slate-50 border border-slate-100 text-xs text-slate-800 leading-relaxed">
                    {summary?.executive_summary ||
                      "Chưa có bản tóm tắt tự động cho cuộc họp này."}
                  </div>
                </div>

                {/* Key Points */}
                <div>
                  <h3 className="text-xs font-bold uppercase tracking-wider text-slate-400 mb-2">
                    Điểm Trọng Tâm
                  </h3>
                  {summary?.key_points && summary.key_points.length > 0 ? (
                    <ul className="space-y-2 text-xs text-slate-800">
                      {summary.key_points.map((pt, idx) => (
                        <li key={idx} className="flex items-start gap-2">
                          <span className="w-1.5 h-1.5 rounded-full bg-emerald-600 mt-1.5 shrink-0" />
                          <span>{pt}</span>
                        </li>
                      ))}
                    </ul>
                  ) : (
                    <p className="text-xs text-slate-400">Chưa có dữ liệu.</p>
                  )}
                </div>

                {/* Action Items */}
                <div className="pt-4 border-t border-slate-100">
                  <div className="flex items-center gap-2 mb-3">
                    <ListTodo className="w-4 h-4 text-emerald-600" />
                    <h3 className="text-xs font-bold uppercase tracking-wider text-slate-700">
                      Danh Sách Việc Cần Làm
                    </h3>
                  </div>

                  {actionItems.length === 0 ? (
                    <p className="text-xs text-slate-400">
                      Không phát hiện việc cần làm được giao trong cuộc họp.
                    </p>
                  ) : (
                    <div className="space-y-2">
                      {actionItems.map((act) => (
                        <div
                          key={act.id}
                          className="p-3 rounded-xl border border-slate-100 bg-slate-50 flex items-start justify-between gap-3 text-xs"
                        >
                          <div className="space-y-1">
                            <span className="font-semibold text-slate-900 block">
                              {act.description}
                            </span>
                            <span className="text-[11px] text-slate-500">
                              Phụ trách: <strong>{act.assignee}</strong>
                            </span>
                          </div>

                          <span
                            className={`px-2 py-0.5 rounded-full text-[10px] font-bold uppercase shrink-0 ${
                              act.status === "completed"
                                ? "bg-emerald-100 text-emerald-800"
                                : "bg-amber-100 text-amber-800"
                            }`}
                          >
                            {act.status === "completed" ? "Xong" : "Chờ Xử Lý"}
                          </span>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              </div>
            ) : (
              <AssistantChatPane meetingId={meeting.id} onSeek={handleSeek} />
            )}
          </div>
        </div>
      </div>

      {/* Modal: Share Link */}
      {isShareOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/50 backdrop-blur-sm animate-in fade-in">
          <div className="bg-white rounded-2xl max-w-md w-full border border-slate-200 shadow-xl p-6">
            <h3 className="text-base font-bold text-slate-900 mb-1">
              Chia Sẻ Cuộc Họp
            </h3>
            <p className="text-xs text-slate-500 mb-4">
              Người có liên kết này có thể xem nội dung phiên âm mà không cần đăng nhập.
            </p>

            <div className="flex items-center gap-2 p-2 rounded-xl bg-slate-50 border border-slate-200 mb-4">
              <input
                type="text"
                readOnly
                value={shareLink}
                className="flex-1 bg-transparent text-xs font-mono text-slate-700 focus:outline-none truncate"
              />
              <button
                onClick={copyShareLink}
                className="px-3 py-1.5 rounded-lg bg-slate-900 text-white text-xs font-semibold hover:bg-slate-800 transition flex items-center gap-1 shrink-0"
              >
                {copiedLink ? (
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

            <div className="flex justify-end">
              <button
                onClick={() => setIsShareOpen(false)}
                className="px-4 py-2 text-xs font-semibold rounded-xl text-slate-600 hover:bg-slate-100 transition"
              >
                Đóng
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

"use client";

import React, { useRef, useState } from "react";
import { AlertCircle, FileText, History, MessageSquare, RefreshCw, Sparkles } from "lucide-react";
import { useAudioStreamUrl } from "@/hooks/useAudioStreamUrl";
import { EMPTY_SEGMENTS, useTranscript } from "@/hooks/useTranscript";
import { useTranscriptOperations } from "@/hooks/useTranscriptOperations";
import { getErrorMessage } from "@/lib/api";
import { useAuth } from "@/lib/auth-context";
import type { Meeting } from "@/types/api";
import { ArtifactsPanel } from "./ArtifactsPanel";
import { AssistantPane } from "./AssistantPane";
import { ChangeHistoryDrawer } from "./ChangeHistoryDrawer";
import { SpeakerTimeline, SpeakerTimelineHandle } from "./SpeakerTimeline";
import { SummaryPanel } from "./SummaryPanel";
import { TranscriptFeed } from "./TranscriptFeed";

type WorkspaceTab = "summary" | "chat" | "docs";

interface MeetingWorkspaceProps {
  meeting: Meeting;
}

const TABS: { key: WorkspaceTab; label: string; icon: typeof Sparkles }[] = [
  { key: "summary", label: "Tóm Tắt & Việc Cần Làm", icon: Sparkles },
  { key: "chat", label: "Trợ Lý", icon: MessageSquare },
  { key: "docs", label: "Tài Liệu", icon: FileText },
];

/**
 * Playback timeline, transcript editor and the summary or chat side panel.
 *
 * Owns the playback position shared by the timeline, the transcript and the
 * chat citations.
 *
 * @param props - The meeting being worked on.
 * @returns The workspace layout.
 */
export function MeetingWorkspace({ meeting }: MeetingWorkspaceProps) {
  const timelineRef = useRef<SpeakerTimelineHandle | null>(null);
  const [currentTime, setCurrentTime] = useState(0);
  const [activeTab, setActiveTab] = useState<WorkspaceTab>("summary");
  const [historyOpen, setHistoryOpen] = useState(false);
  const { user } = useAuth();

  const transcript = useTranscript(meeting.id);
  const { updateSegment, renameSpeakerLabel, deleteSegments } =
    useTranscriptOperations(meeting.id);
  const audio = useAudioStreamUrl(meeting.id, meeting.status === "ready");
  const segments = transcript.data ?? EMPTY_SEGMENTS;

  const handleSeek = (seconds: number): void => {
    timelineRef.current?.seekTo(seconds, { play: true });
    setCurrentTime(seconds);
  };

  const handleUpdateSegment = async (
    segmentId: string,
    content: string
  ): Promise<void> => {
    await updateSegment.mutateAsync({ segmentId, content });
  };

  const handleRenameSpeaker = async (
    oldLabel: string,
    newLabel: string
  ): Promise<void> => {
    await renameSpeakerLabel.mutateAsync({ oldLabel, newLabel });
  };

  const handleDeleteSegment = async (segmentId: string): Promise<void> => {
    if (!confirm("Xóa đoạn này?")) return;
    await deleteSegments.mutateAsync([segmentId]);
  };

  return (
    <div className="space-y-6">
      <SpeakerTimeline
        ref={timelineRef}
        audioUrl={audio.data ?? null}
        onAudioError={() => void audio.refetch()}
        durationSec={meeting.duration_seconds}
        segments={segments}
        currentTime={currentTime}
        onTimeUpdate={setCurrentTime}
        onSegmentClick={(segment) => handleSeek(segment.start_time)}
      />

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        <div className="lg:col-span-7 flex flex-col h-[700px]">
          {transcript.isError ? (
            <div className="p-4 rounded-2xl bg-rose-50 border border-rose-200 flex items-center justify-between gap-3">
              <div className="flex items-center gap-2 text-sm text-rose-800">
                <AlertCircle className="w-4 h-4 text-rose-600 shrink-0" />
                <span>
                  {getErrorMessage(transcript.error, "Không thể tải phiên âm.")}
                </span>
              </div>
              <button
                onClick={() => void transcript.refetch()}
                className="px-3 py-1.5 text-xs font-semibold rounded-lg bg-rose-600 text-white hover:bg-rose-700 transition flex items-center gap-1.5 shrink-0"
              >
                <RefreshCw className="w-3.5 h-3.5" />
                <span>Thử Lại</span>
              </button>
            </div>
          ) : (
            <TranscriptFeed
              segments={segments}
              currentTime={currentTime}
              onSegmentClick={(segment) => handleSeek(segment.start_time)}
              onUpdateContent={handleUpdateSegment}
              onRenameSpeaker={handleRenameSpeaker}
              onDeleteSegment={handleDeleteSegment}
            />
          )}
        </div>

        <div className="lg:col-span-5 flex flex-col h-[700px]">
          <div
            role="tablist"
            className="flex items-center gap-2 p-1 bg-slate-200/60 rounded-xl mb-3"
          >
            {TABS.map(({ key, label, icon: Icon }) => (
              <button
                key={key}
                role="tab"
                aria-selected={activeTab === key}
                onClick={() => setActiveTab(key)}
                className={`flex-1 py-1.5 px-3 rounded-lg text-xs font-bold transition flex items-center justify-center gap-2 ${
                  activeTab === key
                    ? "bg-white text-slate-900 shadow-sm"
                    : "text-slate-700 hover:text-slate-900"
                }`}
              >
                <Icon className="w-3.5 h-3.5 text-emerald-600" />
                <span>{label}</span>
              </button>
            ))}
            <button
              onClick={() => setHistoryOpen(true)}
              aria-label="Lịch sử thay đổi"
              title="Lịch sử thay đổi"
              className="p-1.5 rounded-lg text-slate-700 hover:bg-white hover:text-slate-900 transition"
            >
              <History className="w-4 h-4" />
            </button>
          </div>

          <div className="flex-1 overflow-hidden">
            {activeTab === "summary" && (
              <SummaryPanel
                meetingId={meeting.id}
                summaryStatus={meeting.summary_status}
              />
            )}
            {activeTab === "chat" && <AssistantPane meetingId={meeting.id} onSeek={handleSeek} />}
            {activeTab === "docs" && (
              <ArtifactsPanel
                meetingId={meeting.id}
                canDelete={user !== null && meeting.created_by === user.id}
              />
            )}
          </div>
        </div>
      </div>

      <ChangeHistoryDrawer
        meetingId={meeting.id}
        open={historyOpen}
        onClose={() => setHistoryOpen(false)}
        canEdit={user !== null}
      />
    </div>
  );
}

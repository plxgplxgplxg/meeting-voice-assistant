"use client";

import React, { useEffect, useRef, useState } from "react";
import {
  AlertCircle,
  Edit2,
  Trash2,
  User,
  Search,
  Check,
  X,
  Play,
  ArrowDownCircle,
} from "lucide-react";
import { getErrorMessage } from "@/lib/api";
import { formatDuration } from "@/lib/utils";
import { TimelineSegment } from "./SpeakerTimeline";

interface TranscriptFeedProps {
  segments: TimelineSegment[];
  currentTime: number;
  onSegmentClick: (segment: TimelineSegment) => void;
  onUpdateContent?: (segmentId: string, newContent: string) => Promise<void>;
  onRenameSpeaker?: (oldSpeaker: string, newSpeaker: string) => Promise<void>;
  onDeleteSegment?: (segmentId: string) => Promise<void>;
  readOnly?: boolean;
}

export function TranscriptFeed({
  segments,
  currentTime,
  onSegmentClick,
  onUpdateContent,
  onRenameSpeaker,
  onDeleteSegment,
  readOnly = false,
}: TranscriptFeedProps) {
  const [searchQuery, setSearchQuery] = useState("");
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editContent, setEditContent] = useState("");
  const [autoScroll, setAutoScroll] = useState(true);
  const [actionError, setActionError] = useState<string | null>(null);
  const [renameError, setRenameError] = useState<string | null>(null);

  // Rename Speaker State
  const [renameSpeakerModal, setRenameSpeakerModal] = useState<string | null>(null);
  const [newSpeakerName, setNewSpeakerName] = useState("");

  const activeSegmentRef = useRef<HTMLDivElement | null>(null);
  const feedContainerRef = useRef<HTMLDivElement | null>(null);

  // Filtered segments
  const filteredSegments = segments.filter((seg) => {
    if (!searchQuery.trim()) return true;
    const q = searchQuery.toLowerCase();
    return (
      seg.content.toLowerCase().includes(q) ||
      seg.speaker_label.toLowerCase().includes(q)
    );
  });

  // Auto-scroll to active playing segment
  useEffect(() => {
    if (autoScroll && activeSegmentRef.current && feedContainerRef.current) {
      activeSegmentRef.current.scrollIntoView({
        behavior: "smooth",
        block: "nearest",
      });
    }
  }, [currentTime, autoScroll]);

  const handleStartEdit = (seg: TimelineSegment) => {
    if (readOnly) return;
    setEditingId(seg.id);
    setEditContent(seg.content);
  };

  const handleSaveEdit = async (segmentId: string) => {
    if (!onUpdateContent) return;
    setActionError(null);
    try {
      await onUpdateContent(segmentId, editContent);
      setEditingId(null);
    } catch (error: unknown) {
      setActionError(getErrorMessage(error, "Không thể cập nhật đoạn phiên âm."));
    }
  };

  const handleDelete = async (segmentId: string) => {
    if (!onDeleteSegment) return;
    setActionError(null);
    try {
      await onDeleteSegment(segmentId);
    } catch (error: unknown) {
      setActionError(getErrorMessage(error, "Không thể xóa đoạn phiên âm."));
    }
  };

  const handleConfirmRename = async () => {
    if (!onRenameSpeaker || !renameSpeakerModal || !newSpeakerName.trim()) return;
    setRenameError(null);
    try {
      await onRenameSpeaker(renameSpeakerModal, newSpeakerName.trim());
      setRenameSpeakerModal(null);
      setNewSpeakerName("");
    } catch (error: unknown) {
      setRenameError(getErrorMessage(error, "Không thể đổi tên người nói."));
    }
  };

  return (
    <div className="bg-white border border-slate-200 rounded-2xl shadow-sm flex flex-col h-full max-h-[700px] overflow-hidden">
      {/* Feed Toolbar */}
      <div className="p-4 border-b border-slate-100 flex items-center justify-between gap-3 bg-slate-50/50">
        <div className="relative flex-1 max-w-sm">
          <Search className="w-3.5 h-3.5 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Tìm kiếm nội dung hoặc người nói..."
            className="w-full pl-9 pr-3 py-1.5 text-xs bg-white border border-slate-200 rounded-xl text-slate-800 focus:outline-none focus:ring-1 focus:ring-slate-400"
          />
        </div>

        <button
          onClick={() => setAutoScroll(!autoScroll)}
          className={`flex items-center gap-1.5 px-2.5 py-1.5 rounded-xl text-xs font-semibold border transition ${
            autoScroll
              ? "bg-emerald-50 text-emerald-800 border-emerald-200"
              : "bg-white text-slate-600 border-slate-200 hover:bg-slate-50"
          }`}
          title="Tự động cuộn theo tiến trình phát"
        >
          <ArrowDownCircle className="w-3.5 h-3.5" />
          <span className="hidden sm:inline">Cuộn Tự Động</span>
        </button>
      </div>

      {actionError && (
        <div className="mx-4 mt-3 p-2.5 rounded-xl bg-rose-50 border border-rose-200 flex items-center justify-between gap-2 text-sm text-rose-800">
          <div className="flex items-center gap-2">
            <AlertCircle className="w-4 h-4 text-rose-600 shrink-0" />
            <span>{actionError}</span>
          </div>
          <button
            onClick={() => setActionError(null)}
            aria-label="Đóng thông báo"
            className="p-0.5 rounded text-rose-700 hover:bg-rose-100"
          >
            <X className="w-3.5 h-3.5" />
          </button>
        </div>
      )}

      {/* Segments List */}
      <div
        ref={feedContainerRef}
        className="flex-1 overflow-y-auto p-4 space-y-3 divide-y divide-slate-100"
      >
        {filteredSegments.length === 0 ? (
          <div className="py-12 text-center text-sm text-slate-600">
            Không có đoạn phù hợp
          </div>
        ) : (
          filteredSegments.map((seg) => {
            const isActive =
              currentTime >= seg.start_time && currentTime <= seg.end_time;
            const isEditing = editingId === seg.id;

            return (
              <div
                key={seg.id}
                ref={isActive ? activeSegmentRef : null}
                className={`pt-3 first:pt-0 transition-colors rounded-xl p-2.5 ${
                  isActive
                    ? "bg-emerald-50/60 border border-emerald-200 shadow-xs"
                    : "hover:bg-slate-50 border border-transparent"
                }`}
              >
                {/* Speaker Header */}
                <div className="flex items-center justify-between mb-1.5">
                  <div className="flex items-center gap-2">
                    <button
                      onClick={() => {
                        if (!readOnly) {
                          setRenameSpeakerModal(seg.speaker_label);
                          setNewSpeakerName(seg.speaker_label);
                          setRenameError(null);
                        }
                      }}
                      className="flex items-center gap-1.5 px-2 py-0.5 rounded-full text-xs font-bold bg-slate-100 hover:bg-slate-200 text-slate-800 transition"
                      title="Bấm để đổi tên người nói"
                    >
                      <User className="w-3 h-3 text-slate-500" />
                      <span>{seg.speaker_label}</span>
                    </button>

                    <button
                      onClick={() => onSegmentClick(seg)}
                      className="flex items-center gap-1 font-mono text-xs font-semibold text-slate-600 hover:text-emerald-700 transition"
                    >
                      <Play className="w-2.5 h-2.5 fill-current" />
                      <span>
                        {formatDuration(seg.start_time)} -{" "}
                        {formatDuration(seg.end_time)}
                      </span>
                    </button>
                  </div>

                  {!readOnly && (
                    <div className="flex items-center gap-1 opacity-60 hover:opacity-100 transition">
                      <button
                        onClick={() => handleStartEdit(seg)}
                        className="p-1 rounded text-slate-500 hover:text-slate-800 hover:bg-slate-200"
                        title="Chỉnh sửa nội dung"
                      >
                        <Edit2 className="w-3 h-3" />
                      </button>

                      {onDeleteSegment && (
                        <button
                          onClick={() => handleDelete(seg.id)}
                          className="p-1 rounded text-slate-400 hover:text-rose-600 hover:bg-rose-50"
                          title="Xóa đoạn này"
                        >
                          <Trash2 className="w-3 h-3" />
                        </button>
                      )}
                    </div>
                  )}
                </div>

                {/* Content */}
                {isEditing ? (
                  <div className="mt-2 space-y-2">
                    <textarea
                      rows={2}
                      value={editContent}
                      onChange={(e) => setEditContent(e.target.value)}
                      className="w-full p-2.5 text-xs bg-white border border-slate-300 rounded-xl text-slate-900 focus:outline-none focus:ring-1 focus:ring-emerald-600"
                    />
                    <div className="flex justify-end gap-2">
                      <button
                        onClick={() => setEditingId(null)}
                        className="px-2.5 py-1 text-xs font-semibold rounded-lg text-slate-600 hover:bg-slate-200"
                      >
                        Hủy
                      </button>
                      <button
                        onClick={() => handleSaveEdit(seg.id)}
                        className="px-3 py-1 text-xs font-semibold rounded-lg text-white bg-slate-900 hover:bg-slate-800 flex items-center gap-1"
                      >
                        <Check className="w-3 h-3" />
                        <span>Lưu</span>
                      </button>
                    </div>
                  </div>
                ) : (
                  <p
                    onDoubleClick={() => handleStartEdit(seg)}
                    className="text-xs text-slate-800 leading-relaxed cursor-pointer select-text"
                  >
                    {seg.content}
                  </p>
                )}
              </div>
            );
          })
        )}
      </div>

      {/* Rename Speaker Modal */}
      {renameSpeakerModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/50 backdrop-blur-sm animate-in fade-in">
          <div className="bg-white rounded-2xl max-w-sm w-full border border-slate-200 shadow-xl p-5">
            <h3 className="text-sm font-bold text-slate-900 mb-1">
              Đổi Tên Người Nói
            </h3>
            <p className="text-sm text-slate-700 mb-4">
              <strong>{renameSpeakerModal}</strong>
            </p>

            <input
              type="text"
              required
              value={newSpeakerName}
              onChange={(e) => setNewSpeakerName(e.target.value)}
              placeholder="Ví dụ: Giám Đốc An"
              className="w-full px-3 py-2 text-xs bg-white border border-slate-300 rounded-xl text-slate-900 focus:outline-none focus:ring-2 focus:ring-emerald-600/20 focus:border-emerald-600 mb-4"
            />

            {renameError && (
              <p className="-mt-2 mb-4 text-xs font-medium text-rose-700">
                {renameError}
              </p>
            )}

            <div className="flex justify-end gap-2">
              <button
                type="button"
                onClick={() => setRenameSpeakerModal(null)}
                className="px-3 py-1.5 text-xs font-semibold rounded-xl text-slate-600 hover:bg-slate-100"
              >
                Hủy
              </button>
              <button
                type="button"
                onClick={handleConfirmRename}
                disabled={!newSpeakerName.trim()}
                className="px-4 py-1.5 text-xs font-semibold rounded-xl text-white bg-slate-900 hover:bg-slate-800 disabled:opacity-50"
              >
                Cập Nhật
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

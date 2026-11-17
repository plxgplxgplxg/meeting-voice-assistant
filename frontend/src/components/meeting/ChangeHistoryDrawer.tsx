"use client";

import React, { useState } from "react";
import { Bot, ChevronDown, ChevronRight, Loader2, Undo2, User, X } from "lucide-react";
import { useChangeSetDetail, useChangeSets } from "@/hooks/useChangeSets";
import { getErrorMessage } from "@/lib/api";
import type { ChangeSetSummary, SegmentDiff } from "@/types/api";

interface ChangeHistoryDrawerProps {
  meetingId: string;
  open: boolean;
  onClose: () => void;
  canEdit: boolean;
}

const ACTOR_LABELS: Record<ChangeSetSummary["actor_type"], string> = {
  user: "Người dùng",
  agent: "Trợ lý",
  system: "Hệ thống",
};

function DiffLines({ meetingId, changeSetId }: { meetingId: string; changeSetId: string }) {
  const { data, isLoading, error } = useChangeSetDetail(meetingId, changeSetId);

  if (isLoading) return <Loader2 className="w-4 h-4 animate-spin text-emerald-600" />;
  if (error) {
    return <p className="text-xs text-rose-700">{getErrorMessage(error, "Không thể tải chi tiết.")}</p>;
  }
  const changes: SegmentDiff[] = (data?.changes ?? []).filter(
    (change) =>
      !(
        change.op === "update" &&
        change.before &&
        change.after &&
        change.before.content === change.after.content &&
        change.before.speaker_label === change.after.speaker_label
      )
  );
  return (
    <ul className="space-y-1.5">
      {changes.map((change) => (
        <li key={change.segment_id} className="text-xs space-y-1">
          {change.before && (
            <p className="rounded px-2 py-1 bg-rose-50 text-rose-900">
              {change.before.speaker_label}: {change.before.content}
            </p>
          )}
          {change.after && (
            <p className="rounded px-2 py-1 bg-emerald-50 text-emerald-900">
              {change.after.speaker_label}: {change.after.content}
            </p>
          )}
        </li>
      ))}
    </ul>
  );
}

/**
 * Right-hand drawer listing every transcript change, by people and by the assistant.
 *
 * Each entry expands to the before and after of the segments it touched and can be undone
 * (editors only). Undoing is itself recorded as a new change.
 *
 * @param props - Meeting identifier, visibility, close callback and whether the viewer can edit.
 * @returns The drawer, or null while closed.
 */
export function ChangeHistoryDrawer({ meetingId, open, onClose, canEdit }: ChangeHistoryDrawerProps) {
  const { entries, isLoading, error, revert } = useChangeSets(meetingId, open);
  const [expanded, setExpanded] = useState<string | null>(null);
  const [revertError, setRevertError] = useState<string | null>(null);

  if (!open) return null;

  const handleRevert = (changeSetId: string): void => {
    setRevertError(null);
    revert.mutate(changeSetId, {
      onError: (err) => setRevertError(getErrorMessage(err, "Không thể hoàn tác thay đổi này.")),
    });
  };

  return (
    <div className="fixed inset-0 z-40 flex justify-end bg-slate-900/30" onClick={onClose}>
      <aside
        role="dialog"
        aria-label="Lịch sử thay đổi"
        onClick={(event) => event.stopPropagation()}
        className="w-full max-w-md h-full bg-white shadow-xl flex flex-col"
      >
        <div className="p-4 border-b border-slate-200 flex items-center justify-between">
          <h3 className="text-sm font-bold text-slate-900">Lịch Sử Thay Đổi</h3>
          <button onClick={onClose} aria-label="Đóng" className="p-1.5 rounded-lg hover:bg-slate-100">
            <X className="w-4 h-4 text-slate-600" />
          </button>
        </div>

        <div className="flex-1 overflow-y-auto p-4 space-y-2.5">
          {isLoading && <Loader2 className="w-4 h-4 animate-spin text-emerald-600" />}
          {error && (
            <p className="text-sm text-rose-700">{getErrorMessage(error, "Không thể tải lịch sử.")}</p>
          )}
          {!isLoading && entries.length === 0 && (
            <p className="text-sm text-slate-600">Chưa có thay đổi nào</p>
          )}
          {revertError && <p className="text-xs font-medium text-rose-700">{revertError}</p>}

          {entries.map((entry) => {
            const isOpen = expanded === entry.id;
            const isRevert = entry.reverts_change_set_id !== null;
            return (
              <div key={entry.id} className="rounded-xl border border-slate-200 p-3 space-y-2">
                <button
                  onClick={() => setExpanded(isOpen ? null : entry.id)}
                  className="w-full flex items-start gap-2 text-left"
                >
                  {isOpen ? (
                    <ChevronDown className="w-4 h-4 mt-0.5 text-slate-500 shrink-0" />
                  ) : (
                    <ChevronRight className="w-4 h-4 mt-0.5 text-slate-500 shrink-0" />
                  )}
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 text-xs font-semibold text-slate-700">
                      {entry.actor_type === "agent" ? (
                        <Bot className="w-3.5 h-3.5 text-emerald-700" />
                      ) : (
                        <User className="w-3.5 h-3.5 text-slate-600" />
                      )}
                      <span>{ACTOR_LABELS[entry.actor_type]}</span>
                      <span className="text-slate-500">#{entry.revision}</span>
                      {isRevert && (
                        <span className="px-1.5 py-0.5 rounded bg-slate-100 text-slate-700">Hoàn tác</span>
                      )}
                      {entry.reverted && (
                        <span className="px-1.5 py-0.5 rounded bg-amber-100 text-amber-800">Đã hoàn tác</span>
                      )}
                    </div>
                    <p className="text-sm text-slate-800 mt-0.5 break-words">{entry.summary}</p>
                    <p className="text-xs text-slate-500 mt-0.5">
                      {new Date(entry.created_at).toLocaleString("vi-VN")}
                    </p>
                  </div>
                </button>

                {isOpen && <DiffLines meetingId={meetingId} changeSetId={entry.id} />}

                {canEdit && !entry.reverted && !isRevert && (
                  <button
                    onClick={() => handleRevert(entry.id)}
                    disabled={revert.isPending}
                    className="flex items-center gap-1.5 px-2.5 py-1 text-xs font-semibold rounded-lg border border-slate-300 hover:bg-slate-50 disabled:opacity-40 transition"
                  >
                    <Undo2 className="w-3.5 h-3.5" />
                    <span>Hoàn tác</span>
                  </button>
                )}
              </div>
            );
          })}
        </div>
      </aside>
    </div>
  );
}

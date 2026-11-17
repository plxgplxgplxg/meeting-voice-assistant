"use client";

import React, { useMemo, useState } from "react";
import {
  AlertCircle,
  Check,
  FileText,
  ListTodo,
  Loader2,
  Pencil,
  RefreshCw,
  X,
} from "lucide-react";
import { buildEditedOperations } from "@/lib/proposal-edits";
import type {
  ActionItemDiff,
  AgentAction,
  ApproveActionInput,
  SegmentDiff,
} from "@/types/api";

const VISIBLE_CHANGES = 6;

const KIND_LABELS: Record<AgentAction["kind"], { label: string; icon: typeof FileText }> = {
  transcript_ops: { label: "Sửa transcript", icon: FileText },
  action_item_ops: { label: "Việc cần làm", icon: ListTodo },
  summary_regenerate: { label: "Tạo lại tóm tắt", icon: RefreshCw },
};

interface ProposalCardProps {
  proposal: AgentAction;
  busy: boolean;
  error: string | null;
  onApprove: (actionId: string, edits?: ApproveActionInput) => void;
  onReject: (actionId: string) => void;
}

function isSegmentDiff(change: SegmentDiff | ActionItemDiff): change is SegmentDiff {
  return "segment_id" in change;
}

function SegmentChange({
  change,
  editing,
  draft,
  onDraft,
  kept,
  onToggleKeep,
}: {
  change: SegmentDiff;
  editing: boolean;
  draft: string;
  onDraft: (value: string) => void;
  kept: boolean;
  onToggleKeep: () => void;
}) {
  const before = change.before;
  const after = change.after;
  const renamed =
    before && after && before.speaker_label !== after.speaker_label
      ? `${before.speaker_label} → ${after.speaker_label}`
      : (after ?? before)?.speaker_label;

  return (
    <li className="rounded-lg border border-slate-200 bg-white p-2.5 space-y-1.5 text-sm">
      <div className="text-xs font-semibold text-slate-600">{renamed}</div>
      {before && (
        <p
          className={`rounded px-2 py-1 bg-rose-50 text-rose-900 ${
            change.op === "delete" && !kept ? "opacity-50" : ""
          } ${change.op === "update" ? "line-through decoration-rose-300" : ""}`}
        >
          {before.content}
        </p>
      )}
      {after && !editing && (
        <p className="rounded px-2 py-1 bg-emerald-50 text-emerald-900">{after.content}</p>
      )}
      {after && editing && change.op === "update" && (
        <textarea
          value={draft}
          onChange={(event) => onDraft(event.target.value)}
          rows={2}
          className="w-full rounded border border-emerald-300 bg-white px-2 py-1 text-emerald-900 focus:outline-none focus:ring-1 focus:ring-emerald-600"
        />
      )}
      {editing && change.op === "delete" && (
        <label className="flex items-center gap-2 text-xs text-slate-700">
          <input type="checkbox" checked={kept} onChange={onToggleKeep} />
          <span>Xóa đoạn này</span>
        </label>
      )}
    </li>
  );
}

function ActionItemChange({ change }: { change: ActionItemDiff }) {
  const marks = { create: "+", update: "~", delete: "−" } as const;
  const text = (change.after ?? change.before)?.description ?? "";
  const assignee = (change.after ?? change.before)?.assignee;
  return (
    <li className="rounded-lg border border-slate-200 bg-white p-2.5 text-sm flex gap-2">
      <span className="font-bold text-slate-500 w-3 shrink-0">{marks[change.op]}</span>
      <span className="text-slate-800">
        {text}
        {assignee ? <span className="text-slate-500"> ({assignee})</span> : null}
      </span>
    </li>
  );
}

/**
 * One assistant proposal with a before/after view and Approve, Edit and Reject.
 *
 * Nothing is applied until the user approves. Edit lets the user change the new text of
 * each updated segment, or keep a segment that was going to be deleted, before approving.
 *
 * @param props - The proposal, its pending state and decision callbacks.
 * @returns The proposal card.
 */
export function ProposalCard({ proposal, busy, error, onApprove, onReject }: ProposalCardProps) {
  const { label, icon: Icon } = KIND_LABELS[proposal.kind];
  const [showAll, setShowAll] = useState(false);
  const [editing, setEditing] = useState(false);
  const [drafts, setDrafts] = useState<Record<string, string>>({});
  const [kept, setKept] = useState<Set<string>>(new Set());

  const changes = useMemo(() => {
    const raw = proposal.preview.changes ?? [];
    return proposal.kind === "transcript_ops"
      ? (raw as SegmentDiff[]).filter((change) => !change.order_only)
      : raw;
  }, [proposal]);

  const segmentChanges = changes.filter(isSegmentDiff);
  const canEdit =
    proposal.kind === "transcript_ops" &&
    segmentChanges.length > 0 &&
    segmentChanges.every((change) => change.op !== "insert");
  const visible = showAll ? changes : changes.slice(0, VISIBLE_CHANGES);

  const startEditing = (): void => {
    setDrafts(
      Object.fromEntries(
        segmentChanges
          .filter((change) => change.op === "update" && change.after)
          .map((change) => [change.segment_id, change.after?.content ?? ""])
      )
    );
    setKept(new Set(segmentChanges.filter((c) => c.op === "delete").map((c) => c.segment_id)));
    setEditing(true);
  };

  const editedOperations = editing ? buildEditedOperations(segmentChanges, drafts, kept) : [];

  return (
    <div className="rounded-2xl border border-emerald-200 bg-emerald-50/50 p-3.5 space-y-3">
      <div className="flex items-center justify-between gap-2">
        <div className="flex items-center gap-2 text-sm font-bold text-slate-900">
          <Icon className="w-4 h-4 text-emerald-700" />
          <span>{label}</span>
        </div>
        <span className="text-[11px] font-bold px-2 py-0.5 rounded-full bg-amber-100 text-amber-800">
          Chờ duyệt
        </span>
      </div>

      {changes.length > 0 && (
        <ul className="space-y-2">
          {visible.map((change, index) =>
            isSegmentDiff(change) ? (
              <SegmentChange
                key={`${change.segment_id}-${index}`}
                change={change}
                editing={editing}
                draft={drafts[change.segment_id] ?? ""}
                onDraft={(value) => setDrafts((d) => ({ ...d, [change.segment_id]: value }))}
                kept={kept.has(change.segment_id)}
                onToggleKeep={() =>
                  setKept((current) => {
                    const next = new Set(current);
                    if (next.has(change.segment_id)) next.delete(change.segment_id);
                    else next.add(change.segment_id);
                    return next;
                  })
                }
              />
            ) : (
              <ActionItemChange key={index} change={change} />
            )
          )}
        </ul>
      )}

      {changes.length > VISIBLE_CHANGES && (
        <button
          onClick={() => setShowAll((value) => !value)}
          className="text-xs font-semibold text-emerald-800 hover:underline"
        >
          {showAll ? "Thu gọn" : `Xem thêm (${changes.length - VISIBLE_CHANGES})`}
        </button>
      )}

      {error && (
        <div className="flex items-start gap-2 text-xs font-medium text-rose-800">
          <AlertCircle className="w-3.5 h-3.5 mt-0.5 shrink-0" />
          <span>{error}</span>
        </div>
      )}

      <div className="flex flex-wrap items-center gap-2">
        <button
          onClick={() =>
            onApprove(proposal.id, editing ? { operations: editedOperations } : undefined)
          }
          disabled={busy || (editing && editedOperations.length === 0)}
          className="px-3 py-1.5 text-xs font-semibold rounded-lg bg-emerald-700 text-white hover:bg-emerald-800 disabled:opacity-40 transition flex items-center gap-1.5"
        >
          {busy ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Check className="w-3.5 h-3.5" />}
          <span>{editing ? "Duyệt bản sửa" : "Duyệt"}</span>
        </button>
        {canEdit && !editing && (
          <button
            onClick={startEditing}
            disabled={busy}
            className="px-3 py-1.5 text-xs font-semibold rounded-lg border border-slate-300 bg-white text-slate-800 hover:bg-slate-50 disabled:opacity-40 transition flex items-center gap-1.5"
          >
            <Pencil className="w-3.5 h-3.5" />
            <span>Sửa</span>
          </button>
        )}
        {editing && (
          <button
            onClick={() => setEditing(false)}
            className="px-3 py-1.5 text-xs font-semibold rounded-lg border border-slate-300 bg-white text-slate-800 hover:bg-slate-50 transition"
          >
            Hủy sửa
          </button>
        )}
        <button
          onClick={() => onReject(proposal.id)}
          disabled={busy}
          className="px-3 py-1.5 text-xs font-semibold rounded-lg border border-rose-200 bg-white text-rose-700 hover:bg-rose-50 disabled:opacity-40 transition flex items-center gap-1.5"
        >
          <X className="w-3.5 h-3.5" />
          <span>Từ chối</span>
        </button>
      </div>
    </div>
  );
}

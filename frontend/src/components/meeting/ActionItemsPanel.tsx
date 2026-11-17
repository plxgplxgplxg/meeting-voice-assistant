"use client";

import React from "react";
import { ListTodo, Loader2 } from "lucide-react";
import { useActionItems } from "@/hooks/useSummary";
import { getErrorMessage } from "@/lib/api";

interface ActionItemsPanelProps {
  meetingId: string;
}

/**
 * Checklist of action items extracted from a meeting.
 *
 * @param props - Meeting identifier.
 * @returns The action item list with loading, empty and error states.
 */
export function ActionItemsPanel({ meetingId }: ActionItemsPanelProps) {
  const { data: items, isLoading, isError, error } = useActionItems(meetingId);

  return (
    <section>
      <div className="flex items-center gap-2 mb-3">
        <ListTodo className="w-4 h-4 text-emerald-600" />
        <h3 className="text-sm font-bold text-slate-900">Việc Cần Làm</h3>
      </div>

      {isLoading && (
        <Loader2 className="w-4 h-4 animate-spin text-emerald-600" />
      )}

      {isError && (
        <p className="text-sm font-medium text-rose-700">
          {getErrorMessage(error, "Không thể tải danh sách việc cần làm.")}
        </p>
      )}

      {items && items.length === 0 && (
        <p className="text-sm text-slate-600">Không có việc cần làm</p>
      )}

      {items && items.length > 0 && (
        <ul className="space-y-2">
          {items.map((item) => (
            <li
              key={item.id}
              className="p-3 rounded-xl border border-slate-200 bg-slate-50 flex items-start justify-between gap-3"
            >
              <div className="space-y-1">
                <span className="text-sm font-semibold text-slate-900 block">
                  {item.description}
                </span>
                <span className="text-xs text-slate-600">
                  Phụ trách: <strong className="text-slate-800">{item.assignee}</strong>
                </span>
              </div>

              <span
                className={`px-2 py-0.5 rounded-full text-xs font-bold shrink-0 ${
                  item.status === "completed"
                    ? "bg-emerald-100 text-emerald-800"
                    : "bg-amber-100 text-amber-800"
                }`}
              >
                {item.status === "completed" ? "Xong" : "Chờ Xử Lý"}
              </span>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}

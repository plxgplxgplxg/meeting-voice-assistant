"use client";

import React, { useCallback, useState } from "react";
import { Bot, Check, Clock, Loader2, Send, Sparkles, User } from "lucide-react";
import { UndoToast } from "@/components/ui/UndoToast";
import { useAgentActions } from "@/hooks/useAgentActions";
import { useAssistant } from "@/hooks/useAssistant";
import { useChangeSets } from "@/hooks/useChangeSets";
import { getErrorMessage } from "@/lib/api";
import { useAuth } from "@/lib/auth-context";
import { formatDuration } from "@/lib/utils";
import type { Citation } from "@/types/api";
import { ProposalCard } from "./ProposalCard";

interface AssistantPaneProps {
  meetingId: string;
  onSeek: (seconds: number) => void;
}

interface AppliedChange {
  changeSetId: string;
}

const SUGGESTIONS = [
  "Tóm tắt các quyết định quan trọng nhất trong cuộc họp?",
  "Đổi tên Speaker 1 thành Linh",
  "Tạo biên bản cuộc họp dạng docx",
];

function CitationChips({ citations, onSeek }: { citations: Citation[]; onSeek: (s: number) => void }) {
  if (citations.length === 0) return null;
  return (
    <div className="mt-3 pt-2.5 border-t border-slate-200 flex flex-wrap gap-1.5">
      {citations.map((citation, index) => (
        <button
          key={index}
          onClick={() => onSeek(citation.start_time)}
          title="Phát đoạn này"
          className="flex items-center gap-1 px-2 py-0.5 rounded-full bg-white border border-emerald-300 hover:border-emerald-500 hover:bg-emerald-50 text-emerald-800 font-medium text-xs shadow-sm transition"
        >
          <Clock className="w-3 h-3 text-emerald-600" />
          <span>
            {citation.speaker_label ? `${citation.speaker_label} • ` : ""}
            {formatDuration(citation.start_time)}
          </span>
        </button>
      ))}
    </div>
  );
}

/**
 * Meeting assistant: streamed answers with citations, tool activity, and proposals to approve.
 *
 * The assistant never edits on its own. Proposals appear as cards under the conversation;
 * approving one applies it and shows an undo toast.
 *
 * @param props - Meeting identifier and the callback that seeks the audio.
 * @returns The assistant pane.
 */
export function AssistantPane({ meetingId, onSeek }: AssistantPaneProps) {
  const { user } = useAuth();
  const assistant = useAssistant(meetingId);
  const actions = useAgentActions(meetingId, user !== null);
  const history = useChangeSets(meetingId, false);
  const [question, setQuestion] = useState("");
  const [applied, setApplied] = useState<AppliedChange | null>(null);
  const [cardError, setCardError] = useState<{ id: string; message: string } | null>(null);
  const [activeAction, setActiveAction] = useState<string | null>(null);

  const dismissToast = useCallback(() => setApplied(null), []);

  const send = (text: string): void => {
    const trimmed = text.trim();
    if (!trimmed || assistant.isStreaming) return;
    setQuestion("");
    void assistant.send(trimmed);
  };

  const approve = (actionId: string, edits?: Parameters<typeof actions.approve.mutate>[0]["edits"]): void => {
    setActiveAction(actionId);
    setCardError(null);
    actions.approve.mutate(
      { actionId, edits },
      {
        onSuccess: (action) => {
          if (action.change_set_id) setApplied({ changeSetId: action.change_set_id });
        },
        onError: (error) =>
          setCardError({ id: actionId, message: getErrorMessage(error, "Không thể áp dụng đề xuất.") }),
        onSettled: () => setActiveAction(null),
      }
    );
  };

  const reject = (actionId: string): void => {
    setActiveAction(actionId);
    actions.reject.mutate(actionId, {
      onError: (error) =>
        setCardError({ id: actionId, message: getErrorMessage(error, "Không thể từ chối đề xuất.") }),
      onSettled: () => setActiveAction(null),
    });
  };

  const undo = (): void => {
    if (!applied) return;
    history.revert.mutate(applied.changeSetId, { onSettled: () => setApplied(null) });
  };

  const { messages, liveTurn, isLoadingHistory, historyError } = assistant;
  const isEmpty = !isLoadingHistory && messages.length === 0 && !liveTurn;

  return (
    <div className="bg-white border border-slate-200 rounded-2xl shadow-sm flex flex-col h-full max-h-[700px] overflow-hidden">
      <div className="p-4 border-b border-slate-200 flex items-center gap-2.5 bg-slate-50">
        <div className="p-1.5 rounded-lg bg-emerald-600 text-white">
          <Bot className="w-4 h-4" />
        </div>
        <h3 className="text-sm font-bold text-slate-900">Trợ Lý Cuộc Họp</h3>
      </div>

      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {isLoadingHistory && (
          <div className="py-6 flex justify-center">
            <Loader2 className="w-5 h-5 animate-spin text-emerald-600" />
          </div>
        )}

        {historyError && (
          <p className="text-sm font-medium text-rose-700">
            {getErrorMessage(historyError, "Không thể tải lịch sử trợ lý.")}
          </p>
        )}

        {isEmpty && (
          <div className="py-6 space-y-4">
            <div className="text-center">
              <Sparkles className="w-8 h-8 text-emerald-600 mx-auto mb-2" />
              <p className="text-sm font-semibold text-slate-800">Hỏi hoặc nhờ chỉnh sửa</p>
            </div>
            <div className="space-y-1.5 pt-2">
              {SUGGESTIONS.map((suggestion) => (
                <button
                  key={suggestion}
                  onClick={() => send(suggestion)}
                  className="w-full text-left p-2.5 rounded-xl border border-slate-200 hover:border-emerald-300 hover:bg-emerald-50 text-sm text-slate-800 transition"
                >
                  {suggestion}
                </button>
              ))}
            </div>
          </div>
        )}

        {messages
          .filter((message) => message.role !== "tool")
          .map((message) => (
            <div
              key={message.id}
              className={`flex gap-2.5 ${message.role === "user" ? "justify-end" : "justify-start"}`}
            >
              {message.role === "assistant" && (
                <div className="w-6 h-6 rounded-lg bg-emerald-600 text-white flex items-center justify-center shrink-0 mt-0.5">
                  <Bot className="w-3.5 h-3.5" />
                </div>
              )}
              <div
                className={`max-w-[85%] rounded-2xl p-3 text-sm leading-relaxed ${
                  message.role === "user"
                    ? "bg-slate-900 text-white"
                    : message.status === "error"
                    ? "bg-rose-50 border border-rose-200 text-rose-900"
                    : "bg-slate-50 border border-slate-200 text-slate-800"
                }`}
              >
                <div className="whitespace-pre-wrap">{message.content}</div>
                <CitationChips citations={message.citations} onSeek={onSeek} />
              </div>
              {message.role === "user" && (
                <div className="w-6 h-6 rounded-lg bg-slate-200 text-slate-700 flex items-center justify-center shrink-0 mt-0.5">
                  <User className="w-3.5 h-3.5" />
                </div>
              )}
            </div>
          ))}

        {liveTurn && (
          <>
            <div className="flex gap-2.5 justify-end">
              <div className="max-w-[85%] rounded-2xl p-3 text-sm leading-relaxed bg-slate-900 text-white">
                {liveTurn.question}
              </div>
              <div className="w-6 h-6 rounded-lg bg-slate-200 text-slate-700 flex items-center justify-center shrink-0 mt-0.5">
                <User className="w-3.5 h-3.5" />
              </div>
            </div>
            <div className="flex gap-2.5">
              <div className="w-6 h-6 rounded-lg bg-emerald-600 text-white flex items-center justify-center shrink-0 mt-0.5">
                <Bot className="w-3.5 h-3.5" />
              </div>
              <div className="max-w-[85%] space-y-2">
                {liveTurn.tools.length > 0 && (
                  <div className="flex flex-wrap gap-1.5">
                    {liveTurn.tools.map((tool, index) => (
                      <span
                        key={`${tool.name}-${index}`}
                        className="flex items-center gap-1.5 px-2 py-0.5 rounded-full bg-slate-100 border border-slate-200 text-xs font-medium text-slate-700"
                      >
                        {tool.done ? (
                          <Check className="w-3 h-3 text-emerald-600" />
                        ) : (
                          <Loader2 className="w-3 h-3 animate-spin text-emerald-600" />
                        )}
                        <span>{tool.label}</span>
                      </span>
                    ))}
                  </div>
                )}
                {(liveTurn.text || liveTurn.error) && (
                  <div
                    className={`rounded-2xl p-3 text-sm leading-relaxed ${
                      liveTurn.error
                        ? "bg-rose-50 border border-rose-200 text-rose-900"
                        : "bg-slate-50 border border-slate-200 text-slate-800"
                    }`}
                  >
                    <div className="whitespace-pre-wrap">{liveTurn.error ?? liveTurn.text}</div>
                    {!liveTurn.error && <CitationChips citations={liveTurn.citations} onSeek={onSeek} />}
                    {liveTurn.error && (
                      <button
                        onClick={assistant.dismissError}
                        className="mt-2 text-xs font-semibold text-rose-700 hover:underline"
                      >
                        Đóng
                      </button>
                    )}
                  </div>
                )}
                {!liveTurn.text && !liveTurn.error && liveTurn.tools.length === 0 && (
                  <Loader2 className="w-4 h-4 animate-spin text-emerald-600" />
                )}
              </div>
            </div>
          </>
        )}

        {actions.proposals.length > 0 && (
          <section className="space-y-2.5 pt-1">
            <h4 className="text-xs font-bold text-slate-700">
              Đề xuất chờ duyệt ({actions.proposals.length})
            </h4>
            {actions.proposals.map((proposal) => (
              <ProposalCard
                key={proposal.id}
                proposal={proposal}
                busy={activeAction === proposal.id}
                error={cardError?.id === proposal.id ? cardError.message : null}
                onApprove={approve}
                onReject={reject}
              />
            ))}
          </section>
        )}
      </div>

      <form
        onSubmit={(event) => {
          event.preventDefault();
          send(question);
        }}
        className="p-3 border-t border-slate-200 flex items-center gap-2 bg-white"
      >
        <input
          type="text"
          value={question}
          onChange={(event) => setQuestion(event.target.value)}
          placeholder="Hỏi hoặc nhờ chỉnh sửa"
          className="flex-1 px-3.5 py-2 text-sm bg-slate-50 border border-slate-200 rounded-xl text-slate-900 focus:outline-none focus:ring-1 focus:ring-emerald-600 focus:bg-white transition"
        />
        <button
          type="submit"
          aria-label="Gửi"
          disabled={!question.trim() || assistant.isStreaming}
          className="p-2 rounded-xl bg-slate-900 text-white hover:bg-slate-800 disabled:opacity-40 transition shadow-sm"
        >
          <Send className="w-3.5 h-3.5" />
        </button>
      </form>

      {applied && (
        <UndoToast
          message="Đã áp dụng thay đổi"
          isUndoing={history.revert.isPending}
          onUndo={undo}
          onDismiss={dismissToast}
        />
      )}
    </div>
  );
}

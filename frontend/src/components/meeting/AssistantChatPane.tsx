"use client";

import React, { useState } from "react";
import { Send, Bot, User, Sparkles, Clock, Loader2 } from "lucide-react";
import { fetchApi } from "@/lib/api";
import { formatDuration } from "@/lib/utils";

interface Citation {
  segment_id?: string;
  speaker?: string;
  start_time: number;
  end_time?: number;
  snippet?: string;
}

interface ChatMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  citations?: Citation[];
  created_at?: string;
}

interface AssistantChatPaneProps {
  meetingId: string;
  onSeek: (seconds: number) => void;
}

const SUGGESTIONS = [
  "Tóm tắt các quyết định quan trọng nhất trong cuộc họp?",
  "Danh sách việc cần làm và người phụ trách là ai?",
  "Nội dung tranh luận chính xoay quanh vấn đề gì?",
];

export function AssistantChatPane({
  meetingId,
  onSeek,
}: AssistantChatPaneProps) {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [question, setQuestion] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [sessionId, setSessionId] = useState<string | null>(null);

  // Initialize or retrieve chat session
  const ensureSession = async (): Promise<string> => {
    if (sessionId) return sessionId;
    try {
      const session = await fetchApi<{ id: string }>(
        `/chat/meetings/${meetingId}/sessions`,
        { method: "POST" }
      );
      setSessionId(session.id);
      return session.id;
    } catch {
      // Mock fallback session ID
      const fallback = `sess_${meetingId.slice(0, 8)}`;
      setSessionId(fallback);
      return fallback;
    }
  };

  const handleSendMessage = async (textToSend?: string) => {
    const text = textToSend || question;
    if (!text.trim() || isLoading) return;

    const userMsg: ChatMessage = {
      id: `usr_${Date.now()}`,
      role: "user",
      content: text.trim(),
    };
    setMessages((prev) => [...prev, userMsg]);
    setQuestion("");
    setIsLoading(true);

    try {
      const activeSessionId = await ensureSession();
      const response = await fetchApi<{
        answer: string;
        citations: Citation[];
      }>(`/chat/sessions/${activeSessionId}/messages`, {
        method: "POST",
        body: JSON.stringify({ question: text.trim() }),
      });

      const assistantMsg: ChatMessage = {
        id: `ast_${Date.now()}`,
        role: "assistant",
        content: response.answer,
        citations: response.citations || [],
      };
      setMessages((prev) => [...prev, assistantMsg]);
    } catch (err: any) {
      // Graceful error assistant message
      const errorMsg: ChatMessage = {
        id: `err_${Date.now()}`,
        role: "assistant",
        content:
          err.message ||
          "Không thể tra cứu thông tin cuộc họp lúc này. Vui lòng thử lại sau.",
      };
      setMessages((prev) => [...prev, errorMsg]);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="bg-white border border-slate-200 rounded-2xl shadow-sm flex flex-col h-full max-h-[700px] overflow-hidden">
      {/* Header */}
      <div className="p-4 border-b border-slate-100 flex items-center gap-2.5 bg-slate-50/50">
        <div className="p-1.5 rounded-lg bg-emerald-600 text-white">
          <Bot className="w-4 h-4" />
        </div>
        <div>
          <h3 className="text-xs font-bold text-slate-900">
            Trợ Lý Hỏi Đáp (RAG)
          </h3>
          <p className="text-[11px] text-slate-500">
            Tra cứu nội dung kèm bằng chứng trích dẫn trực tiếp
          </p>
        </div>
      </div>

      {/* Messages Feed */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {messages.length === 0 ? (
          <div className="py-6 space-y-4">
            <div className="text-center">
              <Sparkles className="w-8 h-8 text-emerald-600/50 mx-auto mb-2" />
              <p className="text-xs font-semibold text-slate-700">
                Hỏi bất kỳ điều gì về cuộc họp này
              </p>
              <p className="text-[11px] text-slate-400 mt-0.5">
                Mô hình AI sẽ trích xuất thông tin kèm mốc thời gian phát biểu
              </p>
            </div>

            <div className="space-y-1.5 pt-2">
              <span className="text-[10px] font-bold uppercase tracking-wider text-slate-400 block px-1">
                Gợi ý câu hỏi:
              </span>
              {SUGGESTIONS.map((s) => (
                <button
                  key={s}
                  onClick={() => handleSendMessage(s)}
                  className="w-full text-left p-2.5 rounded-xl border border-slate-200 hover:border-emerald-300 hover:bg-emerald-50/40 text-xs text-slate-700 transition"
                >
                  {s}
                </button>
              ))}
            </div>
          </div>
        ) : (
          messages.map((msg) => (
            <div
              key={msg.id}
              className={`flex gap-2.5 ${
                msg.role === "user" ? "justify-end" : "justify-start"
              }`}
            >
              {msg.role === "assistant" && (
                <div className="w-6 h-6 rounded-lg bg-emerald-600 text-white flex items-center justify-center shrink-0 mt-0.5">
                  <Bot className="w-3.5 h-3.5" />
                </div>
              )}

              <div
                className={`max-w-[85%] rounded-2xl p-3 text-xs leading-relaxed ${
                  msg.role === "user"
                    ? "bg-slate-900 text-white"
                    : "bg-slate-50 border border-slate-200 text-slate-800"
                }`}
              >
                <div className="whitespace-pre-wrap">{msg.content}</div>

                {/* Citations Pill list */}
                {msg.citations && msg.citations.length > 0 && (
                  <div className="mt-3 pt-2.5 border-t border-slate-200/60 space-y-1.5">
                    <span className="text-[10px] font-bold text-slate-500 uppercase tracking-wide block">
                      Trích dẫn bằng chứng:
                    </span>
                    <div className="flex flex-wrap gap-1.5">
                      {msg.citations.map((c, i) => (
                        <button
                          key={i}
                          onClick={() => onSeek(c.start_time)}
                          className="flex items-center gap-1 px-2 py-0.5 rounded-full bg-white border border-emerald-300 hover:border-emerald-500 hover:bg-emerald-50 text-emerald-800 font-medium text-[11px] shadow-xs transition"
                          title="Bấm để phát lại đoạn này"
                        >
                          <Clock className="w-3 h-3 text-emerald-600" />
                          <span>
                            {c.speaker ? `${c.speaker} • ` : ""}
                            {formatDuration(c.start_time)}
                          </span>
                        </button>
                      ))}
                    </div>
                  </div>
                )}
              </div>

              {msg.role === "user" && (
                <div className="w-6 h-6 rounded-lg bg-slate-200 text-slate-700 flex items-center justify-center shrink-0 mt-0.5">
                  <User className="w-3.5 h-3.5" />
                </div>
              )}
            </div>
          ))
        )}

        {isLoading && (
          <div className="flex gap-2.5 items-center text-xs text-slate-500 bg-slate-50 p-3 rounded-2xl border border-slate-100 w-fit">
            <Loader2 className="w-4 h-4 animate-spin text-emerald-600" />
            <span>AI đang tìm kiếm ngữ cảnh cuộc họp...</span>
          </div>
        )}
      </div>

      {/* Input Box */}
      <form
        onSubmit={(e) => {
          e.preventDefault();
          handleSendMessage();
        }}
        className="p-3 border-t border-slate-100 flex items-center gap-2 bg-white"
      >
        <input
          type="text"
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          placeholder="Hỏi về nội dung cuộc họp..."
          className="flex-1 px-3.5 py-2 text-xs bg-slate-50 border border-slate-200 rounded-xl text-slate-900 focus:outline-none focus:ring-1 focus:ring-emerald-600 focus:bg-white transition"
        />
        <button
          type="submit"
          disabled={!question.trim() || isLoading}
          className="p-2 rounded-xl bg-slate-900 text-white hover:bg-slate-800 disabled:opacity-40 transition shadow-sm"
        >
          <Send className="w-3.5 h-3.5" />
        </button>
      </form>
    </div>
  );
}

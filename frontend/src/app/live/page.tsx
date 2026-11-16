"use client";

import React, { useState, useRef, useEffect } from "react";
import { useRouter } from "next/navigation";
import {
  Mic,
  MicOff,
  Radio,
  Square,
  Play,
  RotateCcw,
  CheckCircle2,
  AlertCircle,
  Clock,
  Loader2,
} from "lucide-react";
import { fetchApi } from "@/lib/api";
import { formatDuration } from "@/lib/utils";

export default function LiveMeetingPage() {
  const router = useRouter();
  const [meetingTitle, setMeetingTitle] = useState("");
  const [isRecording, setIsRecording] = useState(false);
  const [isPaused, setIsPaused] = useState(false);
  const [elapsedSeconds, setElapsedSeconds] = useState(0);
  const [meetingId, setMeetingId] = useState<string | null>(null);
  const [liveTranscripts, setLiveTranscripts] = useState<
    { speaker: string; text: string; time: number }[]
  >([]);
  const [audioBlob, setAudioBlob] = useState<Blob | null>(null);
  const [isFinalizing, setIsFinalizing] = useState(false);

  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const chunksRef = useRef<Blob[]>([]);
  const timerRef = useRef<NodeJS.Timeout | null>(null);

  useEffect(() => {
    if (isRecording && !isPaused) {
      timerRef.current = setInterval(() => {
        setElapsedSeconds((prev) => prev + 1);
      }, 1000);
    } else {
      if (timerRef.current) clearInterval(timerRef.current);
    }
    return () => {
      if (timerRef.current) clearInterval(timerRef.current);
    };
  }, [isRecording, isPaused]);

  const startRecording = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const mediaRecorder = new MediaRecorder(stream);
      mediaRecorderRef.current = mediaRecorder;
      chunksRef.current = [];

      mediaRecorder.ondataavailable = (e) => {
        if (e.data.size > 0) {
          chunksRef.current.push(e.data);
        }
      };

      mediaRecorder.onstop = async () => {
        const fullBlob = new Blob(chunksRef.current, { type: "audio/webm" });
        setAudioBlob(fullBlob);
      };

      // Create meeting in backend
      const title =
        meetingTitle.trim() ||
        `Ghi Âm Trực Tiếp ${new Date().toLocaleTimeString("vi-VN")}`;
      const res = await fetchApi<{ id: string }>("/meetings", {
        method: "POST",
        body: JSON.stringify({ title }),
      });
      setMeetingId(res.id);

      mediaRecorder.start(1000);
      setIsRecording(true);
      setIsPaused(false);
      setElapsedSeconds(0);
    } catch (err: any) {
      alert("Không thể truy cập microphone: " + (err.message || "Vui lòng cấp quyền"));
    }
  };

  const pauseRecording = () => {
    if (mediaRecorderRef.current && isRecording) {
      if (isPaused) {
        mediaRecorderRef.current.resume();
        setIsPaused(false);
      } else {
        mediaRecorderRef.current.pause();
        setIsPaused(true);
      }
    }
  };

  const stopAndProcess = async () => {
    if (!mediaRecorderRef.current) return;
    setIsFinalizing(true);
    mediaRecorderRef.current.stop();

    // Give 500ms for onstop blob to produce
    setTimeout(async () => {
      if (!meetingId) {
        setIsFinalizing(false);
        return;
      }
      try {
        const blob = new Blob(chunksRef.current, { type: "audio/webm" });
        const formData = new FormData();
        formData.append("file", blob, `live_recording_${meetingId}.webm`);

        await fetchApi(`/audio/meetings/${meetingId}/upload`, {
          method: "POST",
          body: formData,
        });

        router.push(`/meetings/${meetingId}`);
      } catch (err: any) {
        alert(err.message || "Lỗi tải lên đoạn ghi âm trực tiếp.");
        setIsFinalizing(false);
      }
    }, 600);
  };

  return (
    <div className="max-w-3xl mx-auto space-y-6">
      <div className="pb-4 border-b border-slate-200 flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold text-slate-900">
            Phòng Thu Âm Trực Tiếp
          </h1>
          <p className="text-xs text-slate-500 mt-0.5">
            Ghi âm thời gian thực từ microphone với AI phân tích tự động
          </p>
        </div>

        {isRecording && (
          <div className="flex items-center gap-2 px-3 py-1.5 rounded-full bg-rose-50 border border-rose-200 text-rose-700 text-xs font-bold animate-pulse">
            <Radio className="w-3.5 h-3.5 text-rose-600" />
            <span>ĐANG GHI ÂM</span>
          </div>
        )}
      </div>

      <div className="bg-white border border-slate-200 rounded-2xl p-8 shadow-sm text-center space-y-6">
        {!isRecording ? (
          <div className="max-w-md mx-auto space-y-4">
            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1.5 text-left">
                Tiêu Đề Phiên Ghi Âm
              </label>
              <input
                type="text"
                value={meetingTitle}
                onChange={(e) => setMeetingTitle(e.target.value)}
                placeholder="Ví dụ: Thảo Luận Kỹ Thuật Dự Án"
                className="w-full px-3.5 py-2.5 text-sm bg-white border border-slate-300 rounded-xl text-slate-900 focus:outline-none focus:ring-2 focus:ring-emerald-600/20 focus:border-emerald-600"
              />
            </div>

            <div className="py-8">
              <button
                onClick={startRecording}
                className="inline-flex items-center gap-3 px-8 py-3.5 text-sm font-bold text-white bg-slate-900 hover:bg-slate-800 rounded-2xl shadow-md transition transform active:scale-95"
              >
                <Mic className="w-5 h-5 text-emerald-400" />
                <span>Bắt Đầu Ghi Âm</span>
              </button>
            </div>
          </div>
        ) : (
          <div className="space-y-6">
            {/* Timer Display */}
            <div className="p-8 rounded-2xl bg-slate-50 border border-slate-100 flex flex-col items-center justify-center">
              <div className="text-5xl font-mono font-extrabold text-slate-900 tracking-wider">
                {formatDuration(elapsedSeconds)}
              </div>
              <span className="text-xs font-medium text-slate-500 mt-2">
                {isPaused ? "Đang tạm dừng thu âm" : "Đang thu âm liên tục..."}
              </span>
            </div>

            {/* Action Buttons */}
            <div className="flex justify-center items-center gap-4">
              <button
                onClick={pauseRecording}
                className="px-5 py-2.5 rounded-xl border border-slate-200 bg-white hover:bg-slate-50 text-slate-700 text-xs font-semibold transition shadow-xs"
              >
                {isPaused ? "Tiếp Tục Thu" : "Tạm Dừng"}
              </button>

              <button
                onClick={stopAndProcess}
                disabled={isFinalizing}
                className="flex items-center gap-2 px-6 py-2.5 rounded-xl bg-rose-600 hover:bg-rose-700 text-white text-xs font-bold transition shadow-sm disabled:opacity-50"
              >
                {isFinalizing ? (
                  <>
                    <Loader2 className="w-4 h-4 animate-spin" />
                    <span>Đang Hoàn Tất & Xử Lý...</span>
                  </>
                ) : (
                  <>
                    <Square className="w-3.5 h-3.5 fill-current" />
                    <span>Dừng & Phân Tích AI</span>
                  </>
                )}
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

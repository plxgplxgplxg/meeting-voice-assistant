"use client";

import React, {
  forwardRef,
  useEffect,
  useImperativeHandle,
  useRef,
  useState,
} from "react";
import {
  Play,
  Pause,
  RotateCcw,
  RotateCw,
  ZoomIn,
  ZoomOut,
  Volume2,
  VolumeX,
} from "lucide-react";
import { formatDuration } from "@/lib/utils";

export interface TimelineSegment {
  id: string;
  speaker_label: string;
  start_time: number;
  end_time: number;
  content: string;
}

export interface SpeakerTimelineHandle {
  seekTo: (seconds: number, options?: { play?: boolean }) => void;
  play: () => void;
  pause: () => void;
}

interface SpeakerTimelineProps {
  audioUrl?: string | null;
  durationSec: number;
  segments: TimelineSegment[];
  currentTime: number;
  onTimeUpdate: (seconds: number) => void;
  onSegmentClick?: (segment: TimelineSegment) => void;
  onAudioError?: () => void;
}

const SPEAKER_PALETTE: string[] = [
  "bg-emerald-600 text-white border-emerald-700",
  "bg-indigo-600 text-white border-indigo-700",
  "bg-teal-600 text-white border-teal-700",
  "bg-violet-600 text-white border-violet-700",
  "bg-amber-600 text-white border-amber-700",
  "bg-rose-600 text-white border-rose-700",
];

const SPEEDS = [0.75, 1, 1.25, 1.5, 2] as const;

export const SpeakerTimeline = forwardRef<
  SpeakerTimelineHandle,
  SpeakerTimelineProps
>(function SpeakerTimeline(
  {
    audioUrl,
    durationSec,
    segments,
    currentTime,
    onTimeUpdate,
    onSegmentClick,
    onAudioError,
  },
  ref
) {
  const audioRef = useRef<HTMLAudioElement | null>(null);
  const containerRef = useRef<HTMLDivElement | null>(null);
  const [isPlaying, setIsPlaying] = useState(false);
  const [playbackRate, setPlaybackRate] = useState<number>(1);
  const [zoom, setZoom] = useState<number>(1);
  const [isMuted, setIsMuted] = useState(false);

  // Group speakers to unique track rows
  const speakerNames = Array.from(new Set(segments.map((s) => s.speaker_label)));
  const effectiveDuration = Math.max(
    durationSec,
    segments.reduce((acc, s) => Math.max(acc, s.end_time), 0),
    1
  );

  useImperativeHandle(ref, () => ({
    seekTo: (seconds: number, options?: { play?: boolean }) => {
      const clamped = Math.max(0, Math.min(seconds, effectiveDuration));
      if (audioRef.current) {
        audioRef.current.currentTime = clamped;
        if (options?.play) {
          audioRef.current.play().catch(() => {});
          setIsPlaying(true);
        }
      }
      onTimeUpdate(clamped);
    },
    play: () => {
      audioRef.current?.play().catch(() => {});
      setIsPlaying(true);
    },
    pause: () => {
      audioRef.current?.pause();
      setIsPlaying(false);
    },
  }));

  const togglePlay = () => {
    if (!audioRef.current) return;
    if (isPlaying) {
      audioRef.current.pause();
      setIsPlaying(false);
    } else {
      audioRef.current.play().catch(() => {});
      setIsPlaying(true);
    }
  };

  const seekRelative = (delta: number) => {
    const nextTime = Math.max(0, Math.min(currentTime + delta, effectiveDuration));
    if (audioRef.current) {
      audioRef.current.currentTime = nextTime;
    }
    onTimeUpdate(nextTime);
  };

  const handleSpeedChange = (speed: number) => {
    setPlaybackRate(speed);
    if (audioRef.current) {
      audioRef.current.playbackRate = speed;
    }
  };

  const handleTrackClick = (e: React.MouseEvent<HTMLDivElement>) => {
    const rect = e.currentTarget.getBoundingClientRect();
    const clickX = e.clientX - rect.left;
    const ratio = Math.max(0, Math.min(clickX / rect.width, 1));
    const targetSec = ratio * effectiveDuration;
    if (audioRef.current) {
      audioRef.current.currentTime = targetSec;
    }
    onTimeUpdate(targetSec);
  };

  return (
    <div className="bg-white border border-slate-200 rounded-2xl shadow-sm p-4 space-y-3">
      {audioUrl && (
        <audio
          ref={audioRef}
          src={audioUrl}
          preload="metadata"
          onTimeUpdate={(e) => onTimeUpdate(e.currentTarget.currentTime)}
          onEnded={() => setIsPlaying(false)}
          onError={() => onAudioError?.()}
        />
      )}

      {/* Control Bar */}
      <div className="flex flex-wrap items-center justify-between gap-3 pb-3 border-b border-slate-100">
        <div className="flex items-center gap-2">
          <button
            onClick={togglePlay}
            className="p-2.5 rounded-xl bg-slate-900 text-white hover:bg-slate-800 transition shadow-sm"
            title={isPlaying ? "Tạm dừng" : "Phát"}
          >
            {isPlaying ? (
              <Pause className="w-4 h-4 fill-current" />
            ) : (
              <Play className="w-4 h-4 fill-current ml-0.5" />
            )}
          </button>

          <button
            onClick={() => seekRelative(-5)}
            className="p-2 rounded-xl border border-slate-200 hover:bg-slate-50 text-slate-700 transition"
            title="Lùi 5 giây"
          >
            <RotateCcw className="w-4 h-4" />
          </button>

          <button
            onClick={() => seekRelative(5)}
            className="p-2 rounded-xl border border-slate-200 hover:bg-slate-50 text-slate-700 transition"
            title="Tiến 5 giây"
          >
            <RotateCw className="w-4 h-4" />
          </button>

          <div className="text-xs font-mono font-semibold text-slate-700 ml-2">
            <span>{formatDuration(currentTime)}</span>
            <span className="text-slate-400 mx-1">/</span>
            <span>{formatDuration(effectiveDuration)}</span>
          </div>
        </div>

        <div className="flex items-center gap-4">
          {/* Speed Selector */}
          <div className="flex items-center bg-slate-100 p-0.5 rounded-xl text-xs font-semibold">
            {SPEEDS.map((s) => (
              <button
                key={s}
                onClick={() => handleSpeedChange(s)}
                className={`px-2 py-1 rounded-lg transition ${
                  playbackRate === s
                    ? "bg-white text-slate-900 shadow-xs"
                    : "text-slate-600 hover:text-slate-900"
                }`}
              >
                {s}x
              </button>
            ))}
          </div>

          {/* Zoom Slider */}
          <div className="hidden sm:flex items-center gap-2 text-slate-500">
            <ZoomOut className="w-3.5 h-3.5" />
            <input
              type="range"
              min={1}
              max={4}
              step={0.5}
              value={zoom}
              onChange={(e) => setZoom(parseFloat(e.target.value))}
              className="w-20 accent-slate-900 h-1 bg-slate-200 rounded-lg cursor-pointer"
            />
            <ZoomIn className="w-3.5 h-3.5" />
          </div>
        </div>
      </div>

      {/* Multi-Speaker Tracks Visualizer */}
      <div className="overflow-x-auto pb-1" ref={containerRef}>
        <div
          className="relative select-none min-w-full"
          style={{ width: `${zoom * 100}%` }}
        >
          {/* Main Scrubber Click Bar */}
          <div
            onClick={handleTrackClick}
            className="h-3 bg-slate-100 rounded-full mb-3 cursor-pointer relative overflow-hidden"
          >
            <div
              className="h-full bg-emerald-500/30"
              style={{
                width: `${(currentTime / effectiveDuration) * 100}%`,
              }}
            />
          </div>

          {/* Speaker Tracks */}
          <div
            onClick={handleTrackClick}
            className="space-y-2 relative cursor-pointer"
          >
            {speakerNames.map((spk, idx) => {
              const spkSegments = segments.filter((s) => s.speaker_label === spk);
              const colorClass =
                SPEAKER_PALETTE[idx % SPEAKER_PALETTE.length];

              return (
                <div
                  key={spk}
                  className="h-8 bg-slate-50 rounded-xl relative border border-slate-100 overflow-hidden"
                >
                  <span className="absolute left-2 top-1/2 -translate-y-1/2 text-[10px] font-bold text-slate-400 z-10 pointer-events-none uppercase tracking-wide">
                    {spk}
                  </span>

                  {spkSegments.map((seg) => {
                    const leftPct = (seg.start_time / effectiveDuration) * 100;
                    const widthPct = Math.max(
                      ((seg.end_time - seg.start_time) / effectiveDuration) * 100,
                      0.5
                    );

                    return (
                      <div
                        key={seg.id}
                        onClick={(e) => {
                          e.stopPropagation();
                          if (audioRef.current) {
                            audioRef.current.currentTime = seg.start_time;
                          }
                          onTimeUpdate(seg.start_time);
                          if (onSegmentClick) {
                            onSegmentClick(seg);
                          }
                        }}
                        style={{
                          left: `${leftPct}%`,
                          width: `${widthPct}%`,
                        }}
                        title={`${seg.speaker_label}: ${seg.content}`}
                        className={`absolute top-1 bottom-1 rounded-md px-1.5 flex items-center text-[10px] font-medium truncate cursor-pointer hover:brightness-110 shadow-xs border ${colorClass}`}
                      >
                        <span className="truncate">{seg.content}</span>
                      </div>
                    );
                  })}
                </div>
              );
            })}

            {/* Playhead Indicator */}
            <div
              className="absolute top-0 bottom-0 w-0.5 bg-emerald-600 pointer-events-none z-20 shadow-sm transition-all"
              style={{
                left: `${(currentTime / effectiveDuration) * 100}%`,
              }}
            >
              <div className="w-2.5 h-2.5 -ml-1 rounded-full bg-emerald-600 shadow-sm" />
            </div>
          </div>
        </div>
      </div>
    </div>
  );
});

export type MeetingStatus =
  | "draft"
  | "uploaded"
  | "transcribing"
  | "summarizing"
  | "indexing"
  | "ready"
  | "failed";

export type StatusTone = "success" | "warning" | "danger" | "neutral";

const PROCESSING_STATUSES: ReadonlySet<MeetingStatus> = new Set<MeetingStatus>([
  "uploaded",
  "transcribing",
  "summarizing",
  "indexing",
]);

const STATUS_LABELS: Record<MeetingStatus, string> = {
  draft: "Nháp",
  uploaded: "Đang Chờ Xử Lý",
  transcribing: "Đang Phiên Âm",
  summarizing: "Đang Tóm Tắt",
  indexing: "Đang Lập Chỉ Mục",
  ready: "Đã Xong",
  failed: "Thất Bại",
};

const STATUS_TONES: Record<MeetingStatus, StatusTone> = {
  draft: "neutral",
  uploaded: "warning",
  transcribing: "warning",
  summarizing: "warning",
  indexing: "warning",
  ready: "success",
  failed: "danger",
};

const TONE_CLASSES: Record<StatusTone, string> = {
  success: "bg-emerald-100 text-emerald-800",
  warning: "bg-amber-100 text-amber-800 animate-pulse",
  danger: "bg-rose-100 text-rose-800",
  neutral: "bg-slate-100 text-slate-700",
};

/**
 * Whether the backend is still working on a meeting.
 *
 * @param status - Meeting status reported by the API.
 * @returns True for every state between upload and ready/failed.
 */
export function isProcessingStatus(status: MeetingStatus): boolean {
  return PROCESSING_STATUSES.has(status);
}

/**
 * Short Vietnamese label for a meeting status.
 *
 * @param status - Meeting status reported by the API.
 * @returns Label for badges.
 */
export function statusLabel(status: MeetingStatus): string {
  return STATUS_LABELS[status] ?? status;
}

/**
 * Tailwind classes for a status badge.
 *
 * @param status - Meeting status reported by the API.
 * @returns Class list including the pulse animation for in-progress states.
 */
export function statusBadgeClasses(status: MeetingStatus): string {
  return TONE_CLASSES[STATUS_TONES[status] ?? "neutral"];
}

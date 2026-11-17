import type {
  AudioStreamUrl,
  AudioUploadResult,
  ExportFormat,
  Meeting,
  MeetingShareLink,
  SharePermission,
} from "@/types/api";
import { downloadFile, fetchApi } from "./client";

/**
 * List the meetings visible to the signed-in user.
 *
 * @returns Meetings sorted by the backend.
 */
export function listMeetings(): Promise<Meeting[]> {
  return fetchApi<Meeting[]>("/meetings");
}

/**
 * Fetch one meeting. The share token, when set, is appended by the client.
 *
 * @param meetingId - Meeting identifier.
 * @returns Meeting detail including processing status.
 */
export function getMeeting(meetingId: string): Promise<Meeting> {
  return fetchApi<Meeting>(`/meetings/${meetingId}`);
}

/**
 * Create an empty meeting owned by the signed-in user.
 *
 * @param title - Meeting title.
 * @returns The created meeting in draft status.
 */
export function createMeeting(title: string): Promise<Meeting> {
  return fetchApi<Meeting>("/meetings", {
    method: "POST",
    body: JSON.stringify({ title }),
  });
}

/**
 * Upload a recording to an existing meeting and queue processing.
 *
 * @param meetingId - Meeting identifier.
 * @param file - Audio file or recorded blob.
 * @param fileName - Optional file name, required for plain blobs.
 * @returns Upload summary with the new meeting status.
 */
export function uploadMeetingAudio(
  meetingId: string,
  file: Blob,
  fileName?: string
): Promise<AudioUploadResult> {
  const formData = new FormData();
  if (fileName) {
    formData.append("file", file, fileName);
  } else {
    formData.append("file", file);
  }
  return fetchApi<AudioUploadResult>(`/meetings/${meetingId}/audio`, {
    method: "POST",
    body: formData,
  });
}

/**
 * Restart processing of a failed meeting.
 *
 * @param meetingId - Meeting identifier.
 * @returns Upload summary with the new meeting status.
 */
export function reprocessMeeting(meetingId: string): Promise<AudioUploadResult> {
  return fetchApi<AudioUploadResult>(`/meetings/${meetingId}/reprocess`, {
    method: "POST",
  });
}

/**
 * Request a short-lived signed URL for the audio element.
 *
 * @param meetingId - Meeting identifier.
 * @returns Signed path and its expiry timestamp.
 */
export function getAudioStreamUrl(meetingId: string): Promise<AudioStreamUrl> {
  return fetchApi<AudioStreamUrl>(`/meetings/${meetingId}/audio/stream-url`);
}

/**
 * Create or refresh the share link of a meeting (creator only).
 *
 * @param meetingId - Meeting identifier.
 * @param permission - Access level granted to link holders.
 * @returns Share token and path.
 */
export function createShareLink(
  meetingId: string,
  permission: SharePermission = "viewer"
): Promise<MeetingShareLink> {
  return fetchApi<MeetingShareLink>(
    `/meetings/${meetingId}/share?permission=${permission}`,
    { method: "POST" }
  );
}

/**
 * Download a meeting export through the browser.
 *
 * @param meetingId - Meeting identifier.
 * @param format - Export format.
 * @param fallbackFilename - File name used when the response has none.
 */
export function downloadMeetingExport(
  meetingId: string,
  format: ExportFormat,
  fallbackFilename: string
): Promise<void> {
  return downloadFile(`/meetings/${meetingId}/exports/${format}`, fallbackFilename);
}

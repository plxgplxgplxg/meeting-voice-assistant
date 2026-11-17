import type { TranscriptSegment } from "@/types/api";
import { fetchApi } from "./client";

/**
 * Fetch all transcript segments of a meeting in chronological order.
 *
 * @param meetingId - Meeting identifier.
 * @returns Transcript segments.
 */
export function getTranscript(meetingId: string): Promise<TranscriptSegment[]> {
  return fetchApi<TranscriptSegment[]>(`/meetings/${meetingId}/transcript`);
}

/**
 * Replace the text of one segment.
 *
 * @param meetingId - Meeting identifier.
 * @param segmentId - Segment identifier.
 * @param content - New text.
 * @returns The updated segment.
 */
export function updateTranscriptSegment(
  meetingId: string,
  segmentId: string,
  content: string
): Promise<TranscriptSegment> {
  return fetchApi<TranscriptSegment>(
    `/meetings/${meetingId}/transcript/segments/${segmentId}`,
    { method: "PATCH", body: JSON.stringify({ content }) }
  );
}

/**
 * Rename a speaker across the whole transcript.
 *
 * @param meetingId - Meeting identifier.
 * @param oldLabel - Current speaker label.
 * @param newLabel - New speaker label.
 * @returns Number of affected segments and the stored label.
 */
export function renameSpeaker(
  meetingId: string,
  oldLabel: string,
  newLabel: string
): Promise<{ affected_segments: number; new_speaker_label: string }> {
  return fetchApi(`/meetings/${meetingId}/transcript/rename-speaker`, {
    method: "POST",
    body: JSON.stringify({
      old_speaker_label: oldLabel,
      new_speaker_label: newLabel,
    }),
  });
}

/**
 * Delete segments from the transcript.
 *
 * @param meetingId - Meeting identifier.
 * @param segmentIds - Identifiers of the segments to remove.
 * @returns Number of deleted segments.
 */
export function deleteTranscriptSegments(
  meetingId: string,
  segmentIds: string[]
): Promise<{ deleted_segments: number }> {
  return fetchApi(`/meetings/${meetingId}/transcript/delete-segments`, {
    method: "POST",
    body: JSON.stringify({ segment_ids: segmentIds }),
  });
}

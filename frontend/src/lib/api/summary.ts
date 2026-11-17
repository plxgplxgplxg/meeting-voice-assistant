import type { ActionItem, Summary } from "@/types/api";
import { fetchApi } from "./client";

/**
 * Fetch the generated summary of a meeting.
 *
 * @param meetingId - Meeting identifier.
 * @returns The summary, or null while none has been generated.
 */
export function getSummary(meetingId: string): Promise<Summary | null> {
  return fetchApi<Summary | null>(`/meetings/${meetingId}/summary`);
}

/**
 * Fetch the action items extracted from a meeting.
 *
 * @param meetingId - Meeting identifier.
 * @returns Action items.
 */
export function listActionItems(meetingId: string): Promise<ActionItem[]> {
  return fetchApi<ActionItem[]>(`/meetings/${meetingId}/action-items`);
}

/**
 * Queue a new summary and action items from the current transcript.
 *
 * @param meetingId - Meeting identifier.
 */
export async function regenerateSummary(meetingId: string): Promise<void> {
  await fetchApi(`/meetings/${meetingId}/summary:regenerate`, { method: "POST" });
}

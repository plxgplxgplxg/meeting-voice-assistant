import type {
  ChangeSetDetail,
  ChangeSetResult,
  ChangeSetSummary,
} from "@/types/api";
import { fetchApi } from "./client";

/**
 * List the transcript edit history, newest first.
 *
 * @param meetingId - Meeting identifier.
 * @returns Change sets made by users and by the assistant.
 */
export function listChangeSets(meetingId: string): Promise<ChangeSetSummary[]> {
  return fetchApi<ChangeSetSummary[]>(`/meetings/${meetingId}/transcript/change-sets`);
}

/**
 * Fetch one change set with the before and after of each segment it touched.
 *
 * @param meetingId - Meeting identifier.
 * @param changeSetId - Change set identifier.
 * @returns The change set detail.
 */
export function getChangeSet(
  meetingId: string,
  changeSetId: string
): Promise<ChangeSetDetail> {
  return fetchApi<ChangeSetDetail>(
    `/meetings/${meetingId}/transcript/change-sets/${changeSetId}`
  );
}

/**
 * Undo a change set by applying its inverse as a new change set.
 *
 * @param meetingId - Meeting identifier.
 * @param changeSetId - Change set to undo.
 * @returns The new change set that restores the previous text.
 */
export function revertChangeSet(
  meetingId: string,
  changeSetId: string
): Promise<ChangeSetResult> {
  return fetchApi<ChangeSetResult>(
    `/meetings/${meetingId}/transcript/change-sets/${changeSetId}/revert`,
    { method: "POST" }
  );
}

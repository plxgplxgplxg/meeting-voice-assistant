import type { SegmentDiff, TranscriptOperationPayload } from "../types/api";

/**
 * Build the operations that reproduce the user's edits to a transcript proposal.
 *
 * Only updates and deletes can be edited: text changes become ``update_text``,
 * speaker changes ``reassign_speaker`` (grouped by label), and deletes the user
 * kept become one ``delete_segments``.
 *
 * @param changes - Segment changes shown in the proposal.
 * @param drafts - Edited new text per segment id.
 * @param keptDeletes - Segment ids whose deletion the user still wants.
 * @returns Operations to send with the approval.
 */
export function buildEditedOperations(
  changes: SegmentDiff[],
  drafts: Record<string, string>,
  keptDeletes: Set<string>
): TranscriptOperationPayload[] {
  const operations: TranscriptOperationPayload[] = [];
  const speakerGroups = new Map<string, string[]>();
  const deletions: string[] = [];

  for (const change of changes) {
    if (change.op === "delete" && keptDeletes.has(change.segment_id)) {
      deletions.push(change.segment_id);
    }
    if (change.op !== "update" || !change.before || !change.after) continue;
    const text = (drafts[change.segment_id] ?? change.after.content).trim();
    if (text && text !== change.before.content) {
      operations.push({ op: "update_text", segment_id: change.segment_id, new_text: text });
    }
    if (change.after.speaker_label !== change.before.speaker_label) {
      const ids = speakerGroups.get(change.after.speaker_label) ?? [];
      speakerGroups.set(change.after.speaker_label, [...ids, change.segment_id]);
    }
  }
  speakerGroups.forEach((ids, label) =>
    operations.push({ op: "reassign_speaker", segment_ids: ids, new_label: label })
  );
  if (deletions.length > 0) {
    operations.push({ op: "delete_segments", segment_ids: deletions });
  }
  return operations;
}

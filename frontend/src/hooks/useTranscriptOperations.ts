"use client";

import { useMutation, useQueryClient } from "@tanstack/react-query";
import {
  deleteTranscriptSegments,
  renameSpeaker,
  updateTranscriptSegment,
} from "@/lib/api/transcript";
import { queryKeys } from "@/lib/query-keys";
import { useShareToken } from "@/lib/share-token";
import type { TranscriptSegment } from "@/types/api";

interface TranscriptSnapshot {
  previous: TranscriptSegment[] | undefined;
}

interface UpdateSegmentInput {
  segmentId: string;
  content: string;
}

interface RenameSpeakerInput {
  oldLabel: string;
  newLabel: string;
}

/**
 * Transcript edits applied optimistically to the cached transcript.
 *
 * Each mutation patches the cache immediately, restores the previous snapshot
 * when the request fails, and refetches the transcript and meeting afterwards
 * (editing can mark the summary outdated).
 *
 * @param meetingId - Meeting identifier.
 * @returns Mutations to update a segment, rename a speaker and delete segments.
 */
export function useTranscriptOperations(meetingId: string) {
  const queryClient = useQueryClient();
  const shareToken = useShareToken();
  const transcriptKey = queryKeys.transcript(meetingId, shareToken);

  const applyOptimistic = async (
    update: (segments: TranscriptSegment[]) => TranscriptSegment[]
  ): Promise<TranscriptSnapshot> => {
    await queryClient.cancelQueries({ queryKey: transcriptKey });
    const previous = queryClient.getQueryData<TranscriptSegment[]>(transcriptKey);
    queryClient.setQueryData<TranscriptSegment[]>(transcriptKey, (current) =>
      current ? update(current) : current
    );
    return { previous };
  };

  const rollback = (snapshot: TranscriptSnapshot | undefined): void => {
    if (snapshot?.previous) {
      queryClient.setQueryData(transcriptKey, snapshot.previous);
    }
  };

  const refresh = async (): Promise<void> => {
    await Promise.all([
      queryClient.invalidateQueries({ queryKey: transcriptKey }),
      queryClient.invalidateQueries({
        queryKey: queryKeys.meeting(meetingId, shareToken),
      }),
    ]);
  };

  const updateSegment = useMutation({
    mutationFn: ({ segmentId, content }: UpdateSegmentInput) =>
      updateTranscriptSegment(meetingId, segmentId, content),
    onMutate: ({ segmentId, content }) =>
      applyOptimistic((segments) =>
        segments.map((segment) =>
          segment.id === segmentId ? { ...segment, content } : segment
        )
      ),
    onError: (_error, _input, snapshot) => rollback(snapshot),
    onSettled: refresh,
  });

  const renameSpeakerLabel = useMutation({
    mutationFn: ({ oldLabel, newLabel }: RenameSpeakerInput) =>
      renameSpeaker(meetingId, oldLabel, newLabel),
    onMutate: ({ oldLabel, newLabel }) =>
      applyOptimistic((segments) =>
        segments.map((segment) =>
          segment.speaker_label === oldLabel
            ? { ...segment, speaker_label: newLabel }
            : segment
        )
      ),
    onError: (_error, _input, snapshot) => rollback(snapshot),
    onSettled: refresh,
  });

  const deleteSegments = useMutation({
    mutationFn: (segmentIds: string[]) =>
      deleteTranscriptSegments(meetingId, segmentIds),
    onMutate: (segmentIds) =>
      applyOptimistic((segments) =>
        segments.filter((segment) => !segmentIds.includes(segment.id))
      ),
    onError: (_error, _ids, snapshot) => rollback(snapshot),
    onSettled: refresh,
  });

  return { updateSegment, renameSpeakerLabel, deleteSegments };
}

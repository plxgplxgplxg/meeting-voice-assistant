"use client";

import { useQuery } from "@tanstack/react-query";
import { getTranscript } from "@/lib/api/transcript";
import { queryKeys } from "@/lib/query-keys";
import { useShareToken } from "@/lib/share-token";
import type { TranscriptSegment } from "@/types/api";

export const EMPTY_SEGMENTS: TranscriptSegment[] = [];

/**
 * Load the transcript of a meeting.
 *
 * @param meetingId - Meeting identifier.
 * @returns Query resolving to the segments in chronological order.
 */
export function useTranscript(meetingId: string) {
  const shareToken = useShareToken();

  return useQuery({
    queryKey: queryKeys.transcript(meetingId, shareToken),
    queryFn: () => getTranscript(meetingId),
  });
}

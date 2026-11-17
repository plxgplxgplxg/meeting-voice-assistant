"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { getSummary, listActionItems, regenerateSummary } from "@/lib/api/summary";
import { queryKeys } from "@/lib/query-keys";
import { useShareToken } from "@/lib/share-token";

/**
 * Load the generated summary of a meeting.
 *
 * @param meetingId - Meeting identifier.
 * @returns Query resolving to the summary, or null when none exists yet.
 */
export function useSummary(meetingId: string) {
  const shareToken = useShareToken();

  return useQuery({
    queryKey: queryKeys.summary(meetingId, shareToken),
    queryFn: () => getSummary(meetingId),
  });
}

/**
 * Load the action items extracted from a meeting.
 *
 * @param meetingId - Meeting identifier.
 * @returns Query resolving to the action items.
 */
export function useActionItems(meetingId: string) {
  const shareToken = useShareToken();

  return useQuery({
    queryKey: queryKeys.actionItems(meetingId, shareToken),
    queryFn: () => listActionItems(meetingId),
  });
}

/**
 * Queue a new summary from the current transcript.
 *
 * The meeting is refetched so its ``summary_status`` turns ``pending``, which makes
 * the meeting query poll until the new summary is ready.
 *
 * @param meetingId - Meeting identifier.
 * @returns Mutation that requests regeneration.
 */
export function useRegenerateSummary(meetingId: string) {
  const queryClient = useQueryClient();
  const shareToken = useShareToken();

  return useMutation({
    mutationFn: () => regenerateSummary(meetingId),
    onSettled: () =>
      queryClient.invalidateQueries({ queryKey: queryKeys.meeting(meetingId, shareToken) }),
  });
}

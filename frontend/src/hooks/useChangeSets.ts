"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { getChangeSet, listChangeSets, revertChangeSet } from "@/lib/api/history";
import { queryKeys } from "@/lib/query-keys";
import { useShareToken } from "@/lib/share-token";
import type { ChangeSetSummary } from "@/types/api";

const EMPTY_HISTORY: ChangeSetSummary[] = [];

/**
 * Transcript edit history of a meeting, with undo.
 *
 * @param meetingId - Meeting identifier.
 * @param enabled - Load the history only while a view needs it.
 * @returns The history and a mutation that reverts one change set.
 */
export function useChangeSets(meetingId: string, enabled: boolean) {
  const queryClient = useQueryClient();
  const shareToken = useShareToken();
  const historyKey = queryKeys.changeSets(meetingId, shareToken);

  const history = useQuery({
    queryKey: historyKey,
    queryFn: () => listChangeSets(meetingId),
    enabled,
  });

  const revert = useMutation({
    mutationFn: (changeSetId: string) => revertChangeSet(meetingId, changeSetId),
    onSettled: () =>
      Promise.all([
        queryClient.invalidateQueries({ queryKey: historyKey }),
        queryClient.invalidateQueries({ queryKey: queryKeys.transcript(meetingId, shareToken) }),
        queryClient.invalidateQueries({ queryKey: queryKeys.meeting(meetingId, shareToken) }),
      ]),
  });

  return {
    entries: history.data ?? EMPTY_HISTORY,
    isLoading: history.isLoading,
    error: history.error,
    revert,
  };
}

/**
 * Load the before and after of every segment in one change set.
 *
 * @param meetingId - Meeting identifier.
 * @param changeSetId - Change set to expand, or null while collapsed.
 * @returns The change set detail query.
 */
export function useChangeSetDetail(meetingId: string, changeSetId: string | null) {
  const shareToken = useShareToken();
  return useQuery({
    queryKey: [...queryKeys.changeSets(meetingId, shareToken), changeSetId],
    queryFn: () => getChangeSet(meetingId, changeSetId as string),
    enabled: changeSetId !== null,
  });
}

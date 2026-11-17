"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  approveAgentAction,
  listAgentActions,
  rejectAgentAction,
} from "@/lib/api/assistant";
import { queryKeys } from "@/lib/query-keys";
import { useShareToken } from "@/lib/share-token";
import type { AgentAction, ApproveActionInput } from "@/types/api";

const EMPTY_ACTIONS: AgentAction[] = [];

interface ApproveInput {
  actionId: string;
  edits?: ApproveActionInput;
}

/**
 * The caller's pending assistant proposals and the decisions on them.
 *
 * Approving applies the change through the same command layer as manual edits, so
 * the transcript, summary state, action items, history and meeting are refetched
 * afterwards. A stale or expired proposal fails with a 409 the card can show.
 *
 * @param meetingId - Meeting identifier.
 * @param enabled - Load proposals only for signed-in users (guests have none).
 * @returns Pending proposals plus approve and reject mutations.
 */
export function useAgentActions(meetingId: string, enabled = true) {
  const queryClient = useQueryClient();
  const shareToken = useShareToken();
  const actionsKey = queryKeys.agentActions(meetingId, shareToken);

  const pending = useQuery({
    queryKey: actionsKey,
    queryFn: () => listAgentActions(meetingId, "proposed"),
    enabled,
  });

  const refreshMeetingData = (): Promise<unknown[]> =>
    Promise.all([
      queryClient.invalidateQueries({ queryKey: actionsKey }),
      queryClient.invalidateQueries({ queryKey: queryKeys.transcript(meetingId, shareToken) }),
      queryClient.invalidateQueries({ queryKey: queryKeys.summary(meetingId, shareToken) }),
      queryClient.invalidateQueries({ queryKey: queryKeys.actionItems(meetingId, shareToken) }),
      queryClient.invalidateQueries({ queryKey: queryKeys.meeting(meetingId, shareToken) }),
      queryClient.invalidateQueries({ queryKey: queryKeys.changeSets(meetingId, shareToken) }),
    ]);

  const approve = useMutation({
    mutationFn: ({ actionId, edits }: ApproveInput) =>
      approveAgentAction(meetingId, actionId, edits),
    onSettled: refreshMeetingData,
  });

  const reject = useMutation({
    mutationFn: (actionId: string) => rejectAgentAction(meetingId, actionId),
    onSettled: () => queryClient.invalidateQueries({ queryKey: actionsKey }),
  });

  return {
    proposals: pending.data ?? EMPTY_ACTIONS,
    isLoading: pending.isLoading,
    approve,
    reject,
  };
}

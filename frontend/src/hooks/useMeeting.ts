"use client";

import { useEffect, useRef } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { createShareLink, getMeeting, reprocessMeeting } from "@/lib/api/meetings";
import { MeetingStatus, isProcessingStatus } from "@/lib/meeting-status";
import { queryKeys } from "@/lib/query-keys";
import { useShareToken } from "@/lib/share-token";

export const MEETING_POLL_INTERVAL_MS = 4000;

/**
 * Load a meeting and keep it fresh while the backend is processing it.
 *
 * Polls every 4 seconds while the status is a processing state or the summary or
 * index is still being rebuilt, and stops on `ready` or `failed`. When the status or
 * the summary state changes, the transcript, summary, action items and audio URL are
 * refetched.
 *
 * @param meetingId - Meeting identifier.
 * @returns The meeting query.
 */
export function useMeeting(meetingId: string) {
  const shareToken = useShareToken();
  const queryClient = useQueryClient();

  const query = useQuery({
    queryKey: queryKeys.meeting(meetingId, shareToken),
    queryFn: () => getMeeting(meetingId),
    refetchInterval: (current) => {
      const meeting = current.state.data;
      if (!meeting) return false;
      const working =
        isProcessingStatus(meeting.status) ||
        meeting.summary_status === "pending" ||
        meeting.index_status === "pending";
      return working ? MEETING_POLL_INTERVAL_MS : false;
    },
  });

  const status = query.data?.status;
  const summaryStatus = query.data?.summary_status;
  const lastSeen = useRef<{
    id: string;
    status: MeetingStatus;
    summaryStatus: string | undefined;
  } | null>(null);

  useEffect(() => {
    if (!status) return;
    const previous = lastSeen.current;
    const changed =
      previous &&
      previous.id === meetingId &&
      (previous.status !== status || previous.summaryStatus !== summaryStatus);
    if (changed) {
      const dependentKeys = [
        queryKeys.transcript(meetingId, shareToken),
        queryKeys.summary(meetingId, shareToken),
        queryKeys.actionItems(meetingId, shareToken),
        queryKeys.audioUrl(meetingId, shareToken),
      ];
      dependentKeys.forEach((queryKey) =>
        void queryClient.invalidateQueries({ queryKey })
      );
    }
    lastSeen.current = { id: meetingId, status, summaryStatus };
  }, [meetingId, shareToken, status, summaryStatus, queryClient]);

  return query;
}

/**
 * Restart processing of a failed meeting.
 *
 * @param meetingId - Meeting identifier.
 * @returns Mutation that refetches the meeting once the retry is queued.
 */
export function useReprocessMeeting(meetingId: string) {
  const shareToken = useShareToken();
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: () => reprocessMeeting(meetingId),
    onSuccess: () =>
      queryClient.invalidateQueries({
        queryKey: queryKeys.meeting(meetingId, shareToken),
      }),
  });
}

/**
 * Create or refresh the share link of a meeting.
 *
 * @param meetingId - Meeting identifier.
 * @returns Mutation resolving to the share token details.
 */
export function useCreateShareLink(meetingId: string) {
  return useMutation({
    mutationFn: () => createShareLink(meetingId, "viewer"),
  });
}

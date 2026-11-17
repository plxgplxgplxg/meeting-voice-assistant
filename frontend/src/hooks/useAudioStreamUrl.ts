"use client";

import { useQuery } from "@tanstack/react-query";
import { buildBackendUrl } from "@/lib/api";
import { getAudioStreamUrl } from "@/lib/api/meetings";
import { queryKeys } from "@/lib/query-keys";
import { useShareToken } from "@/lib/share-token";

/**
 * Fetch the signed audio URL of a meeting.
 *
 * The URL is never refetched in the background because a new URL restarts the
 * audio element; callers refetch explicitly when playback fails.
 *
 * @param meetingId - Meeting identifier.
 * @param enabled - Whether a recording is ready to stream.
 * @returns Query resolving to an absolute audio URL.
 */
export function useAudioStreamUrl(meetingId: string, enabled: boolean) {
  const shareToken = useShareToken();

  return useQuery({
    queryKey: queryKeys.audioUrl(meetingId, shareToken),
    queryFn: async () => buildBackendUrl((await getAudioStreamUrl(meetingId)).url),
    enabled,
    staleTime: Infinity,
    gcTime: 0,
  });
}

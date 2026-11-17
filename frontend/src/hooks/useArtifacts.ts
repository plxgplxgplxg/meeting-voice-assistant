"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { deleteArtifact, downloadArtifact, listArtifacts } from "@/lib/api/artifacts";
import { queryKeys } from "@/lib/query-keys";
import { useShareToken } from "@/lib/share-token";
import type { MeetingArtifact } from "@/types/api";

const EMPTY_ARTIFACTS: MeetingArtifact[] = [];

/**
 * Generated documents of a meeting: list, download and delete.
 *
 * @param meetingId - Meeting identifier.
 * @returns The artifacts and mutations to download or delete one.
 */
export function useArtifacts(meetingId: string) {
  const queryClient = useQueryClient();
  const shareToken = useShareToken();
  const artifactsKey = queryKeys.artifacts(meetingId, shareToken);

  const artifacts = useQuery({
    queryKey: artifactsKey,
    queryFn: () => listArtifacts(meetingId),
  });

  const download = useMutation({
    mutationFn: (artifact: MeetingArtifact) => downloadArtifact(meetingId, artifact),
  });

  const remove = useMutation({
    mutationFn: (artifactId: string) => deleteArtifact(meetingId, artifactId),
    onSettled: () => queryClient.invalidateQueries({ queryKey: artifactsKey }),
  });

  return {
    artifacts: artifacts.data ?? EMPTY_ARTIFACTS,
    isLoading: artifacts.isLoading,
    error: artifacts.error,
    download,
    remove,
  };
}

"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  createMeeting,
  listMeetings,
  uploadMeetingAudio,
} from "@/lib/api/meetings";
import { getProject, linkMeetingToProject } from "@/lib/api/projects";
import { useAuth } from "@/lib/auth-context";
import { queryKeys } from "@/lib/query-keys";
import type { Meeting } from "@/types/api";

interface UploadMeetingInput {
  title: string;
  file: File;
  projectId: string | null;
}

interface UploadRecordingInput {
  meetingId: string;
  recording: Blob;
  fileName: string;
}

/**
 * Load the meetings of the signed-in user, optionally scoped to a project.
 *
 * @param projectId - Project to scope to, or null for all meetings.
 * @returns Meetings query, disabled while signed out.
 */
export function useMeetings(projectId: string | null) {
  const { user } = useAuth();
  const userId = user?.id ?? null;

  return useQuery({
    queryKey: queryKeys.meetingList(userId, projectId),
    queryFn: async (): Promise<Meeting[]> =>
      projectId ? (await getProject(projectId)).meetings : listMeetings(),
    enabled: userId !== null,
    staleTime: 0,
  });
}

/**
 * Create a meeting, attach it to a project and upload its recording.
 *
 * @returns Mutation resolving to the created meeting.
 */
export function useUploadMeeting() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async ({ title, file, projectId }: UploadMeetingInput) => {
      const meeting = await createMeeting(title);
      if (projectId) await linkMeetingToProject(projectId, meeting.id);
      await uploadMeetingAudio(meeting.id, file);
      return meeting;
    },
    onSettled: () => queryClient.invalidateQueries({ queryKey: queryKeys.meetings }),
  });
}

/**
 * Create an empty meeting, used when a live recording starts.
 *
 * @returns Mutation resolving to the created meeting.
 */
export function useCreateMeeting() {
  return useMutation({ mutationFn: createMeeting });
}

/**
 * Upload a finished live recording to its meeting.
 *
 * @returns Mutation resolving to the upload summary.
 */
export function useUploadRecording() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ meetingId, recording, fileName }: UploadRecordingInput) =>
      uploadMeetingAudio(meetingId, recording, fileName),
    onSettled: () => queryClient.invalidateQueries({ queryKey: queryKeys.meetings }),
  });
}

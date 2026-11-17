import type { MeetingArtifact } from "@/types/api";
import { downloadFile, fetchApi } from "./client";

/**
 * List the generated documents of a meeting.
 *
 * @param meetingId - Meeting identifier.
 * @returns Artifacts, newest first.
 */
export function listArtifacts(meetingId: string): Promise<MeetingArtifact[]> {
  return fetchApi<MeetingArtifact[]>(`/meetings/${meetingId}/artifacts`);
}

/**
 * Delete a generated document (creator only).
 *
 * @param meetingId - Meeting identifier.
 * @param artifactId - Artifact identifier.
 */
export async function deleteArtifact(
  meetingId: string,
  artifactId: string
): Promise<void> {
  await fetchApi(`/meetings/${meetingId}/artifacts/${artifactId}`, { method: "DELETE" });
}

/**
 * Download a generated document.
 *
 * @param meetingId - Meeting identifier.
 * @param artifact - Artifact to download.
 */
export function downloadArtifact(
  meetingId: string,
  artifact: MeetingArtifact
): Promise<void> {
  return downloadFile(
    `/meetings/${meetingId}/artifacts/${artifact.id}/download`,
    artifact.title
  );
}

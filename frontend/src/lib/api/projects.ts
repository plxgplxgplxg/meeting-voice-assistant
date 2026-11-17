import type { CreateProjectPayload, Project, ProjectDetail } from "@/types/api";
import { fetchApi } from "./client";

/**
 * List the projects the signed-in user belongs to.
 *
 * @returns Projects.
 */
export function listProjects(): Promise<Project[]> {
  return fetchApi<Project[]>("/projects");
}

/**
 * Fetch a project with its members and meetings.
 *
 * @param projectId - Project identifier.
 * @returns Project detail.
 */
export function getProject(projectId: string): Promise<ProjectDetail> {
  return fetchApi<ProjectDetail>(`/projects/${projectId}`);
}

/**
 * Create a project owned by the signed-in user.
 *
 * @param payload - Project name and optional description.
 * @returns The created project.
 */
export function createProject(payload: CreateProjectPayload): Promise<Project> {
  return fetchApi<Project>("/projects", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

/**
 * Attach an existing meeting to a project.
 *
 * @param projectId - Project identifier.
 * @param meetingId - Meeting identifier.
 */
export async function linkMeetingToProject(
  projectId: string,
  meetingId: string
): Promise<void> {
  await fetchApi(`/projects/${projectId}/meetings/${meetingId}`, {
    method: "POST",
  });
}

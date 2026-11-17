"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { createProject, listProjects } from "@/lib/api/projects";
import { useAuth } from "@/lib/auth-context";
import { queryKeys } from "@/lib/query-keys";
import type { Project } from "@/types/api";

/**
 * Load the projects of the signed-in user.
 *
 * @returns Projects query, disabled while signed out.
 */
export function useProjects() {
  const { user } = useAuth();
  const userId = user?.id ?? null;

  return useQuery({
    queryKey: queryKeys.projects(userId),
    queryFn: listProjects,
    enabled: userId !== null,
  });
}

/**
 * Create a project and add it to the cached list.
 *
 * @returns Mutation resolving to the created project.
 */
export function useCreateProject() {
  const { user } = useAuth();
  const queryClient = useQueryClient();
  const userId = user?.id ?? null;

  return useMutation({
    mutationFn: createProject,
    onSuccess: (created: Project) => {
      queryClient.setQueryData<Project[]>(queryKeys.projects(userId), (current) => [
        created,
        ...(current ?? []),
      ]);
    },
  });
}

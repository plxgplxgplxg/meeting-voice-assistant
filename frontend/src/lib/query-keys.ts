type ShareScope = string | null;

const meetingScope = (meetingId: string, shareToken: ShareScope) =>
  ["meeting", meetingId, shareToken] as const;

/**
 * Central factory for React Query keys.
 *
 * Meeting keys carry the share token so data fetched as a guest is never reused
 * for the signed-in view of the same meeting.
 */
export const queryKeys = {
  meetingList: (userId: string | null, projectId: string | null) =>
    ["meetings", userId, projectId] as const,
  meetings: ["meetings"] as const,
  meeting: (meetingId: string, shareToken: ShareScope) =>
    [...meetingScope(meetingId, shareToken), "detail"] as const,
  transcript: (meetingId: string, shareToken: ShareScope) =>
    [...meetingScope(meetingId, shareToken), "transcript"] as const,
  summary: (meetingId: string, shareToken: ShareScope) =>
    [...meetingScope(meetingId, shareToken), "summary"] as const,
  actionItems: (meetingId: string, shareToken: ShareScope) =>
    [...meetingScope(meetingId, shareToken), "action-items"] as const,
  chat: (meetingId: string, shareToken: ShareScope) =>
    [...meetingScope(meetingId, shareToken), "chat"] as const,
  agentActions: (meetingId: string, shareToken: ShareScope) =>
    [...meetingScope(meetingId, shareToken), "agent-actions"] as const,
  changeSets: (meetingId: string, shareToken: ShareScope) =>
    [...meetingScope(meetingId, shareToken), "change-sets"] as const,
  artifacts: (meetingId: string, shareToken: ShareScope) =>
    [...meetingScope(meetingId, shareToken), "artifacts"] as const,
  audioUrl: (meetingId: string, shareToken: ShareScope) =>
    [...meetingScope(meetingId, shareToken), "audio-url"] as const,
  projects: (userId: string | null) => ["projects", userId] as const,
  plans: ["plans"] as const,
  subscription: (userId: string | null) => ["subscription", userId] as const,
  order: (orderCode: string) => ["order", orderCode] as const,
};

import type { ChatMessage } from "@/types/api";
import { fetchApi } from "./client";

/**
 * Fetch the caller's chat history for a meeting.
 *
 * @param meetingId - Meeting identifier.
 * @returns Messages in chronological order.
 */
export function listChatMessages(meetingId: string): Promise<ChatMessage[]> {
  return fetchApi<ChatMessage[]>(`/meetings/${meetingId}/chat/messages`);
}

/**
 * Ask the meeting assistant a question.
 *
 * @param meetingId - Meeting identifier.
 * @param query - Question text.
 * @returns The assistant answer with citations.
 */
export function askMeetingQuestion(
  meetingId: string,
  query: string
): Promise<ChatMessage> {
  return fetchApi<ChatMessage>(`/meetings/${meetingId}/chat`, {
    method: "POST",
    body: JSON.stringify({ query }),
  });
}

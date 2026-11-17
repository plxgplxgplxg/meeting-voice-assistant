import type { AgentAction, ApproveActionInput, AssistantEvent } from "@/types/api";
import { flushSseBuffer, parseSseBuffer } from "../assistant-events";
import { fetchApi, fetchStream } from "./client";

/**
 * Send a message to the meeting assistant and stream its events.
 *
 * @param meetingId - Meeting identifier.
 * @param message - The user's message.
 * @param onEvent - Called for every event as it arrives.
 * @param signal - Aborts the stream, e.g. when the pane unmounts.
 * @throws ApiError when the request is refused before streaming (quota, index not ready, ...).
 */
export async function streamAssistantTurn(
  meetingId: string,
  message: string,
  onEvent: (event: AssistantEvent) => void,
  signal?: AbortSignal
): Promise<void> {
  const response = await fetchStream(`/meetings/${meetingId}/assistant/turns`, {
    method: "POST",
    body: JSON.stringify({ message }),
    headers: { Accept: "text/event-stream" },
    signal,
  });
  if (!response.body) return;

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  for (;;) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    const parsed = parseSseBuffer(buffer);
    buffer = parsed.rest;
    parsed.events.forEach(onEvent);
  }
  flushSseBuffer(buffer).forEach(onEvent);
}

/**
 * List the caller's own assistant proposals for a meeting.
 *
 * @param meetingId - Meeting identifier.
 * @param status - Optional status filter, e.g. ``proposed``.
 * @returns Proposals, newest first.
 */
export function listAgentActions(
  meetingId: string,
  status?: string
): Promise<AgentAction[]> {
  const query = status ? `?status=${encodeURIComponent(status)}` : "";
  return fetchApi<AgentAction[]>(`/meetings/${meetingId}/agent-actions${query}`);
}

/**
 * Apply a proposal, optionally with edited operations.
 *
 * @param meetingId - Meeting identifier.
 * @param actionId - Proposal identifier.
 * @param edits - Edited operations replacing the proposed ones.
 * @returns The applied proposal including the change set that can be reverted.
 */
export function approveAgentAction(
  meetingId: string,
  actionId: string,
  edits?: ApproveActionInput
): Promise<AgentAction> {
  return fetchApi<AgentAction>(
    `/meetings/${meetingId}/agent-actions/${actionId}:approve`,
    { method: "POST", body: JSON.stringify(edits ?? {}) }
  );
}

/**
 * Discard a proposal.
 *
 * @param meetingId - Meeting identifier.
 * @param actionId - Proposal identifier.
 * @returns The rejected proposal.
 */
export function rejectAgentAction(
  meetingId: string,
  actionId: string
): Promise<AgentAction> {
  return fetchApi<AgentAction>(
    `/meetings/${meetingId}/agent-actions/${actionId}:reject`,
    { method: "POST" }
  );
}

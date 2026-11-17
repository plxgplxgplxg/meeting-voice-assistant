"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { emptyTurn, reduceTurn, type LiveTurn } from "@/lib/assistant-events";
import { getErrorMessage } from "@/lib/api";
import { streamAssistantTurn } from "@/lib/api/assistant";
import { listChatMessages } from "@/lib/api/chat";
import { queryKeys } from "@/lib/query-keys";
import { useShareToken } from "@/lib/share-token";
import type { AssistantEvent, ChatMessage } from "@/types/api";

const EMPTY_MESSAGES: ChatMessage[] = [];
const ASK_FAILED_MESSAGE = "Không thể liên hệ trợ lý lúc này. Vui lòng thử lại sau.";

/**
 * Conversation with the meeting assistant, streamed over Server-Sent Events.
 *
 * Shows the persisted history plus the turn in progress (tokens, tool activity,
 * citations). Proposals are not kept here: they are persisted by the backend and
 * read through ``useAgentActions``, which is refreshed whenever a proposal event arrives.
 *
 * @param meetingId - Meeting identifier.
 * @returns History, the live turn, and a function to send a message.
 */
export function useAssistant(meetingId: string) {
  const queryClient = useQueryClient();
  const shareToken = useShareToken();
  const chatKey = queryKeys.chat(meetingId, shareToken);
  const [liveTurn, setLiveTurn] = useState<LiveTurn | null>(null);
  const controller = useRef<AbortController | null>(null);

  const history = useQuery({
    queryKey: chatKey,
    queryFn: () => listChatMessages(meetingId),
  });

  useEffect(() => () => controller.current?.abort(), []);

  const send = useCallback(
    async (message: string): Promise<void> => {
      const abort = new AbortController();
      controller.current = abort;
      setLiveTurn(emptyTurn(message));

      const onEvent = (event: AssistantEvent): void => {
        setLiveTurn((turn) => (turn ? reduceTurn(turn, event) : turn));
        if (event.type === "proposal") {
          void queryClient.invalidateQueries({
            queryKey: queryKeys.agentActions(meetingId, shareToken),
          });
        }
        if (event.type === "tool_end" && event.data.name === "create_artifact") {
          void queryClient.invalidateQueries({
            queryKey: queryKeys.artifacts(meetingId, shareToken),
          });
        }
      };

      try {
        await streamAssistantTurn(meetingId, message, onEvent, abort.signal);
      } catch (error) {
        if (abort.signal.aborted) return;
        const text = getErrorMessage(error, ASK_FAILED_MESSAGE);
        setLiveTurn((turn) => (turn ? { ...turn, error: text } : turn));
      }

      if (abort.signal.aborted) return;
      await queryClient.invalidateQueries({ queryKey: chatKey });
      await queryClient.invalidateQueries({
        queryKey: queryKeys.agentActions(meetingId, shareToken),
      });
      setLiveTurn((turn) => (turn?.error ? turn : null));
    },
    [chatKey, meetingId, queryClient, shareToken]
  );

  return {
    messages: history.data ?? EMPTY_MESSAGES,
    isLoadingHistory: history.isLoading,
    historyError: history.error,
    liveTurn,
    isStreaming: liveTurn !== null && liveTurn.error === null,
    send,
    dismissError: () => setLiveTurn(null),
  };
}

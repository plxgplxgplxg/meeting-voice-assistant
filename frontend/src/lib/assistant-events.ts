import type { AssistantEvent, Citation } from "../types/api";

const FRAME_SEPARATOR = "\n\n";

export const TOOL_LABELS: Record<string, string> = {
  get_meeting_overview: "Đang xem tổng quan cuộc họp",
  search_transcript: "Đang tìm trong transcript",
  read_segments: "Đang đọc transcript",
  find_text: "Đang tìm đoạn cần sửa",
  get_summary: "Đang đọc bản tóm tắt",
  propose_transcript_edits: "Đang soạn đề xuất sửa transcript",
  propose_action_item_changes: "Đang soạn đề xuất việc cần làm",
  request_summary_regeneration: "Đang đề xuất tạo lại tóm tắt",
  create_artifact: "Đang tạo tài liệu",
};

export interface ToolActivity {
  name: string;
  label: string;
  done: boolean;
}

export interface LiveTurn {
  question: string;
  text: string;
  tools: ToolActivity[];
  citations: Citation[];
  error: string | null;
}

/**
 * Split buffered Server-Sent Events text into complete events.
 *
 * @param buffer - Text received so far, possibly ending in a partial frame.
 * @returns The decoded events and the unfinished remainder to keep buffering.
 */
export function parseSseBuffer(buffer: string): {
  events: AssistantEvent[];
  rest: string;
} {
  const frames = buffer.split(FRAME_SEPARATOR);
  const rest = frames.pop() ?? "";
  const events: AssistantEvent[] = [];
  for (const frame of frames) {
    const lines = frame.split("\n");
    const type = lines.find((line) => line.startsWith("event:"))?.slice(6).trim();
    const data = lines.find((line) => line.startsWith("data:"))?.slice(5).trim();
    if (!type || !data) continue;
    try {
      events.push({ type, data: JSON.parse(data) } as AssistantEvent);
    } catch {
      // Ignore a malformed frame rather than breaking the whole stream
    }
  }
  return { events, rest };
}

/**
 * Flush whatever is left in the buffer when the stream ends.
 *
 * @param buffer - Remaining text without a trailing frame separator.
 * @returns Events contained in the last frame.
 */
export function flushSseBuffer(buffer: string): AssistantEvent[] {
  return parseSseBuffer(`${buffer}${FRAME_SEPARATOR}`).events;
}

/**
 * Start an empty in-progress turn for a question.
 *
 * @param question - The user's message.
 * @returns A turn with no text, tools or citations yet.
 */
export function emptyTurn(question: string): LiveTurn {
  return { question, text: "", tools: [], citations: [], error: null };
}

/**
 * Apply one streamed event to the in-progress turn.
 *
 * @param turn - Turn state before the event.
 * @param event - Event received from the assistant.
 * @returns The updated turn.
 */
export function reduceTurn(turn: LiveTurn, event: AssistantEvent): LiveTurn {
  switch (event.type) {
    case "token":
      return { ...turn, text: turn.text + event.data.text };
    case "tool_start":
      return {
        ...turn,
        tools: [
          ...turn.tools,
          {
            name: event.data.name,
            label: TOOL_LABELS[event.data.name] ?? "Đang xử lý",
            done: false,
          },
        ],
      };
    case "tool_end": {
      const index = turn.tools.findIndex((t) => t.name === event.data.name && !t.done);
      if (index < 0) return turn;
      return {
        ...turn,
        tools: turn.tools.map((tool, i) => (i === index ? { ...tool, done: true } : tool)),
      };
    }
    case "citation":
      return { ...turn, citations: [...turn.citations, event.data] };
    case "error":
      return { ...turn, error: event.data.message };
    default:
      return turn;
  }
}

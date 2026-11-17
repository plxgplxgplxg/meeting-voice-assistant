import assert from "node:assert/strict";
import { test } from "node:test";
import {
  emptyTurn,
  flushSseBuffer,
  parseSseBuffer,
  reduceTurn,
} from "../src/lib/assistant-events.ts";
import type { AssistantEvent } from "../src/types/api.ts";

const frame = (type: string, data: object): string =>
  `event: ${type}\ndata: ${JSON.stringify(data)}\n\n`;

test("parseSseBuffer returns complete events and keeps the partial frame", () => {
  const input = frame("token", { text: "Xin " }) + frame("token", { text: "chào" }) + "event: tok";
  const { events, rest } = parseSseBuffer(input);

  assert.deepEqual(
    events.map((e) => e.type),
    ["token", "token"]
  );
  assert.equal(rest, "event: tok");
});

test("a frame split across network chunks is decoded once it is complete", () => {
  const whole = frame("done", { message_id: "m1" });
  const first = parseSseBuffer(whole.slice(0, 20));
  assert.deepEqual(first.events, []);

  const second = parseSseBuffer(first.rest + whole.slice(20));
  assert.deepEqual(second.events, [{ type: "done", data: { message_id: "m1" } }]);
  assert.equal(second.rest, "");
});

test("Vietnamese text and malformed frames are handled", () => {
  const { events } = parseSseBuffer(
    "event: token\ndata: not-json\n\n" + frame("token", { text: "Đã đề xuất đổi tên." })
  );
  assert.equal(events.length, 1);
  assert.equal((events[0] as { data: { text: string } }).data.text, "Đã đề xuất đổi tên.");
});

test("flushSseBuffer decodes a final frame without a trailing separator", () => {
  const events = flushSseBuffer('event: done\ndata: {"message_id":"m2"}');
  assert.deepEqual(events, [{ type: "done", data: { message_id: "m2" } }]);
});

test("reduceTurn builds the live turn from tokens, tool activity and citations", () => {
  const events: AssistantEvent[] = [
    { type: "tool_start", data: { name: "search_transcript" } },
    { type: "tool_end", data: { name: "search_transcript" } },
    { type: "token", data: { text: "Họ chọn " } },
    { type: "token", data: { text: "API-first [S1]." } },
    { type: "citation", data: { segment_id: "s1", start_time: 5 } },
  ];
  const turn = events.reduce(reduceTurn, emptyTurn("Chọn kiến trúc nào?"));

  assert.equal(turn.text, "Họ chọn API-first [S1].");
  assert.deepEqual(turn.tools, [
    { name: "search_transcript", label: "Đang tìm trong transcript", done: true },
  ]);
  assert.equal(turn.citations.length, 1);
  assert.equal(turn.error, null);
});

test("each tool_end completes the oldest unfinished call of that tool", () => {
  const events: AssistantEvent[] = [
    { type: "tool_start", data: { name: "find_text" } },
    { type: "tool_start", data: { name: "find_text" } },
    { type: "tool_end", data: { name: "find_text" } },
  ];
  const turn = events.reduce(reduceTurn, emptyTurn("q"));
  assert.deepEqual(turn.tools.map((t) => t.done), [true, false]);
});

test("errors and unknown events never lose the text already streamed", () => {
  let turn = reduceTurn(emptyTurn("q"), { type: "token", data: { text: "dở dang" } });
  turn = reduceTurn(turn, { type: "error", data: { code: "AGENT_ERROR", message: "Lỗi" } });
  assert.equal(turn.text, "dở dang");
  assert.equal(turn.error, "Lỗi");

  const unchanged = reduceTurn(turn, { type: "done", data: { message_id: "m" } });
  assert.equal(unchanged, turn);
});

test("an unknown tool gets a neutral label", () => {
  const turn = reduceTurn(emptyTurn("q"), { type: "tool_start", data: { name: "brand_new_tool" } });
  assert.equal(turn.tools[0].label, "Đang xử lý");
});

import assert from "node:assert/strict";
import { test } from "node:test";
import { buildEditedOperations } from "../src/lib/proposal-edits.ts";
import type { SegmentDiff, SegmentSnapshot } from "../src/types/api.ts";

const snapshot = (id: string, speaker: string, content: string): SegmentSnapshot => ({
  id,
  speaker_label: speaker,
  start_time: 0,
  end_time: 1,
  content,
  sequence_order: 1,
});

const update = (id: string, before: [string, string], after: [string, string]): SegmentDiff => ({
  op: "update",
  segment_id: id,
  before: snapshot(id, before[0], before[1]),
  after: snapshot(id, after[0], after[1]),
  order_only: false,
});

const removal = (id: string): SegmentDiff => ({
  op: "delete",
  segment_id: id,
  before: snapshot(id, "Speaker 1", "Xin chào"),
  after: null,
  order_only: false,
});

test("unedited updates reproduce the proposal as update_text and reassign_speaker", () => {
  const changes = [
    update("a", ["Speaker 1", "Gemany"], ["Linh", "Gemini"]),
    update("b", ["Speaker 1", "Gemany hai"], ["Linh", "Gemini hai"]),
  ];
  const operations = buildEditedOperations(changes, {}, new Set());

  assert.deepEqual(operations, [
    { op: "update_text", segment_id: "a", new_text: "Gemini" },
    { op: "update_text", segment_id: "b", new_text: "Gemini hai" },
    { op: "reassign_speaker", segment_ids: ["a", "b"], new_label: "Linh" },
  ]);
});

test("the user's edited text replaces the proposed text", () => {
  const changes = [update("a", ["S", "Gemany"], ["S", "Gemini"])];
  const operations = buildEditedOperations(changes, { a: "  Gemini Pro  " }, new Set());
  assert.deepEqual(operations, [{ op: "update_text", segment_id: "a", new_text: "Gemini Pro" }]);
});

test("restoring the original text drops the operation", () => {
  const changes = [update("a", ["S", "Gemany"], ["S", "Gemini"])];
  assert.deepEqual(buildEditedOperations(changes, { a: "Gemany" }, new Set()), []);
  assert.deepEqual(buildEditedOperations(changes, { a: "   " }, new Set()), []);
});

test("only deletions the user kept become a delete_segments operation", () => {
  const changes = [removal("x"), removal("y"), removal("z")];
  const operations = buildEditedOperations(changes, {}, new Set(["x", "z"]));
  assert.deepEqual(operations, [{ op: "delete_segments", segment_ids: ["x", "z"] }]);
  assert.deepEqual(buildEditedOperations(changes, {}, new Set()), []);
});

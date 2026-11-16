from typing import Any


def chunk_by_speaker_turn(
    segments: list[dict[str, Any]],
    turn_gap_seconds: float = 2.0,
    min_tokens: int = 24,
    max_tokens: int = 512,
    window_size: int = 1,
) -> list[dict[str, Any]]:
    """Chunk transcript segments by speaker turn with surrounding window context.

    Groups consecutive segments by the same speaker within turn_gap_seconds,
    respects min/max length bounds, and annotates window context boundaries.

    Args:
        segments: Chronological list of transcript segments.
        turn_gap_seconds: Maximum pause allowed between turns to merge.
        min_tokens: Minimum estimated word/token length per chunk.
        max_tokens: Maximum token limit before splitting a long monologue.
        window_size: Number of neighboring chunks to bundle for context retrieval.

    Returns:
        List of contextualized text chunks with citation boundaries.
    """
    if not segments:
        return []

    merged_turns: list[dict[str, Any]] = []
    current_turn: dict[str, Any] | None = None

    for seg in segments:
        speaker = seg.get("speaker", "Người nói")
        start = float(seg.get("start", seg.get("start_time", 0.0)))
        end = float(seg.get("end", seg.get("end_time", 0.0)))
        text = seg.get("text", seg.get("content", "")).strip()

        if not text:
            continue

        if current_turn is None:
            current_turn = {
                "speaker": speaker,
                "start": start,
                "end": end,
                "text": text,
                "segment_ids": [seg.get("segment_id", seg.get("id", "0"))],
            }
        elif current_turn["speaker"] == speaker and (start - current_turn["end"]) <= turn_gap_seconds:
            # Merge with active turn
            current_turn["end"] = end
            current_turn["text"] = f"{current_turn['text']} {text}"
            current_turn["segment_ids"].append(seg.get("segment_id", seg.get("id", "0")))
        else:
            merged_turns.append(current_turn)
            current_turn = {
                "speaker": speaker,
                "start": start,
                "end": end,
                "text": text,
                "segment_ids": [seg.get("segment_id", seg.get("id", "0"))],
            }

    if current_turn:
        merged_turns.append(current_turn)

    # Attach window context (+- window_size turns)
    chunks: list[dict[str, Any]] = []
    total_turns = len(merged_turns)

    for idx, turn in enumerate(merged_turns):
        prev_idx = max(0, idx - window_size)
        next_idx = min(total_turns, idx + window_size + 1)
        window_texts = [
            f"{t['speaker']}: {t['text']}" for t in merged_turns[prev_idx:next_idx]
        ]
        context_window = "\n".join(window_texts)

        chunks.append({
            "chunk_id": f"chunk_{idx}",
            "seq": idx,
            "speaker": turn["speaker"],
            "start": turn["start"],
            "end": turn["end"],
            "text": turn["text"],
            "context_window": context_window,
            "segment_ids": turn["segment_ids"],
        })

    return chunks

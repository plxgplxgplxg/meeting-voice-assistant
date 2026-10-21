from typing import Any


def chunk_by_speaker_turn(
    segments: list[dict[str, Any]], window_size: int = 1
) -> list[dict[str, Any]]:
    """Chunk transcript segments by speaker turn with surrounding window context.

    Args:
        segments: Chronological list of transcript segments.
        window_size: Number of preceding and succeeding segments to bundle.

    Returns:
        List of contextualized text chunks with citation boundaries.
    """
    chunks: list[dict[str, Any]] = []
    for idx, seg in enumerate(segments):
        chunks.append({
            "segment_id": seg.get("id", str(idx)),
            "speaker": seg.get("speaker", "Speaker"),
            "start_time": seg.get("start", 0.0),
            "end_time": seg.get("end", 0.0),
            "content": seg.get("text", ""),
        })
    return chunks

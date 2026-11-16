from app.rag.chunking import chunk_by_speaker_turn


def test_chunk_by_speaker_turn_merging() -> None:
    """Verify that consecutive segments by the same speaker within 2s are merged."""
    segments = [
        {"segment_id": "1", "speaker": "A", "start": 0.0, "end": 2.0, "text": "Chào các bạn."},
        {"segment_id": "2", "speaker": "A", "start": 2.5, "end": 4.5, "text": "Chúng ta bắt đầu nhé."},
        {"segment_id": "3", "speaker": "B", "start": 5.0, "end": 8.0, "text": "Vâng tôi đồng ý."},
    ]

    chunks = chunk_by_speaker_turn(segments, turn_gap_seconds=2.0)
    assert len(chunks) == 2
    assert chunks[0]["speaker"] == "A"
    assert chunks[0]["start"] == 0.0
    assert chunks[0]["end"] == 4.5
    assert "Chào các bạn. Chúng ta bắt đầu nhé." in chunks[0]["text"]
    assert chunks[1]["speaker"] == "B"
    assert "context_window" in chunks[0]

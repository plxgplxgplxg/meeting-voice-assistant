import uuid

import pytest

from app.core.errors import ValidationFailedError
from app.schemas.transcript_ops import (
    DeleteSegments,
    MergeSegments,
    ReassignSpeaker,
    RenameSpeaker,
    ReplaceText,
    SplitSegment,
    UpdateText,
)
from app.services.transcript_ops import SegmentState, TranscriptPlanner

IDS = [uuid.UUID(int=i) for i in range(1, 6)]


def make_segments() -> list[SegmentState]:
    rows = [
        ("Speaker 1", 0, 10, "Xin chào các bạn, hôm nay họp về Gemany."),
        ("Speaker 1", 10, 20, "Gemany là nhà cung cấp mô hình."),
        ("Speaker 2", 20, 30, "Đồng ý, ta dùng gemany cho bản demo."),
        ("Speaker 2", 30, 40, "Hẹn gặp lại."),
        ("Speaker 1", 40, 50, "Tạm biệt."),
    ]
    return [
        SegmentState(IDS[i], speaker, start, end, text, i + 1)
        for i, (speaker, start, end, text) in enumerate(rows)
    ]


def plan(*operations):
    return TranscriptPlanner(make_segments(), new_id=lambda: uuid.UUID(int=99)).plan(operations)


def test_update_text_changes_one_segment() -> None:
    (change,) = plan(UpdateText(segment_id=IDS[3], new_text="  Hẹn gặp lại sau.  "))
    assert change.kind == "update" and change.segment_id == IDS[3]
    assert change.before["content"] == "Hẹn gặp lại." and change.after["content"] == "Hẹn gặp lại sau."


def test_replace_text_is_case_insensitive_by_default_across_all_segments() -> None:
    changes = plan(ReplaceText(find="Gemany", replace="Gemini"))
    assert [c.segment_id for c in changes] == [IDS[0], IDS[1], IDS[2]]
    assert "gemini" not in changes[2].after["content"].lower().replace("gemini", "") or True
    assert changes[2].after["content"] == "Đồng ý, ta dùng Gemini cho bản demo."


def test_replace_text_respects_case_sensitivity_and_whole_word() -> None:
    sensitive = plan(ReplaceText(find="Gemany", replace="Gemini", case_sensitive=True))
    assert [c.segment_id for c in sensitive] == [IDS[0], IDS[1]]

    segments = [SegmentState(IDS[0], "A", 0, 1, "cat concatenate cat.", 1)]
    changes = TranscriptPlanner(segments).plan(
        [ReplaceText(find="cat", replace="dog", whole_word=True)]
    )
    assert changes[0].after["content"] == "dog concatenate dog."


def test_replace_text_can_be_limited_to_chosen_segments() -> None:
    changes = plan(ReplaceText(find="Gemany", replace="Gemini", scope="segments", segment_ids=[IDS[2]]))
    assert [c.segment_id for c in changes] == [IDS[2]]


def test_replace_text_treats_the_search_text_literally() -> None:
    segments = [SegmentState(IDS[0], "A", 0, 1, "giá 5.000 (đồng) *", 1)]
    changes = TranscriptPlanner(segments).plan([ReplaceText(find="(đồng) *", replace="VND")])
    assert changes[0].after["content"] == "giá 5.000 VND"


def test_rename_speaker_updates_every_matching_segment() -> None:
    changes = plan(RenameSpeaker(old_label="Speaker 1", new_label="Linh"))
    assert [c.segment_id for c in changes] == [IDS[0], IDS[1], IDS[4]]
    assert {c.after["speaker_label"] for c in changes} == {"Linh"}


def test_rename_unknown_speaker_is_rejected() -> None:
    with pytest.raises(ValidationFailedError) as exc:
        plan(RenameSpeaker(old_label="Nobody", new_label="X"))
    assert exc.value.code == "SPEAKER_NOT_FOUND"


def test_reassign_speaker_only_touches_the_given_segments() -> None:
    changes = plan(ReassignSpeaker(segment_ids=[IDS[3]], new_label="Dũng"))
    assert [(c.segment_id, c.after["speaker_label"]) for c in changes] == [(IDS[3], "Dũng")]


def test_delete_segments_leaves_other_orders_untouched() -> None:
    changes = plan(DeleteSegments(segment_ids=[IDS[1], IDS[2]]))
    assert {c.kind for c in changes} == {"delete"} and len(changes) == 2


def test_split_creates_a_new_segment_and_shifts_later_orders() -> None:
    changes = plan(SplitSegment(segment_id=IDS[1], at_char=10, split_time=15.0))
    kinds = {c.segment_id: c for c in changes}

    head = kinds[IDS[1]]
    assert head.after["content"] == "Gemany là" and head.after["end_time"] == 15.0
    new = kinds[uuid.UUID(int=99)]
    assert new.kind == "insert"
    assert (new.after["start_time"], new.after["end_time"], new.after["sequence_order"]) == (15.0, 20, 3)
    assert new.after["content"] == "nhà cung cấp mô hình."
    shifted = [c for c in changes if c.kind == "update" and c.order_only]
    assert sorted(c.after["sequence_order"] for c in shifted) == [4, 5, 6]


@pytest.mark.parametrize(
    "operation",
    [
        SplitSegment(segment_id=IDS[1], at_char=1000, split_time=15.0),
        SplitSegment(segment_id=IDS[1], at_char=5, split_time=10.0),
        SplitSegment(segment_id=IDS[1], at_char=5, split_time=25.0),
    ],
)
def test_invalid_splits_are_rejected(operation: SplitSegment) -> None:
    with pytest.raises(ValidationFailedError) as exc:
        plan(operation)
    assert exc.value.code == "INVALID_SPLIT"


def test_merge_joins_adjacent_segments_of_one_speaker_into_the_first() -> None:
    changes = plan(MergeSegments(segment_ids=[IDS[1], IDS[0]]))
    by_kind = {c.kind: c for c in changes}
    merged = by_kind["update"]
    assert merged.segment_id == IDS[0]
    assert merged.after["content"].endswith("Gemany là nhà cung cấp mô hình.")
    assert (merged.after["start_time"], merged.after["end_time"]) == (0, 20)
    assert by_kind["delete"].segment_id == IDS[1]


@pytest.mark.parametrize(
    "segment_ids",
    [[IDS[0], IDS[2]], [IDS[1], IDS[2]], [IDS[0], IDS[4]]],
    ids=["not adjacent", "different speakers", "far apart"],
)
def test_invalid_merges_are_rejected(segment_ids: list[uuid.UUID]) -> None:
    with pytest.raises(ValidationFailedError) as exc:
        plan(MergeSegments(segment_ids=segment_ids))
    assert exc.value.code == "INVALID_MERGE"


def test_unknown_segment_ids_are_rejected_with_a_clear_code() -> None:
    with pytest.raises(ValidationFailedError) as exc:
        plan(UpdateText(segment_id=uuid.uuid4(), new_text="x"))
    assert exc.value.code == "SEGMENT_NOT_FOUND"


def test_operations_compose_in_order() -> None:
    changes = plan(
        RenameSpeaker(old_label="Speaker 2", new_label="Dũng"),
        UpdateText(segment_id=IDS[3], new_text="Hẹn gặp lại."),
        ReplaceText(find="Hẹn", replace="Hẹn nhé", scope="segments", segment_ids=[IDS[3]]),
    )
    final = {c.segment_id: c.after for c in changes}
    assert final[IDS[3]]["content"] == "Hẹn nhé gặp lại." and final[IDS[3]]["speaker_label"] == "Dũng"


def test_noop_operations_produce_no_changes() -> None:
    assert plan(UpdateText(segment_id=IDS[4], new_text="Tạm biệt.")) == []
    assert plan(ReplaceText(find="khong-co-trong-van-ban", replace="x")) == []

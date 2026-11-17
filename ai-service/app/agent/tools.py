from typing import Any

import httpx
from langchain_core.runnables import RunnableConfig
from langchain_core.tools import BaseTool, tool

from app.agent.backend_client import BackendToolError
from app.agent.prompts import TRANSCRIPT_NOTICE
from app.agent.schemas import MAX_PROPOSAL_OPERATIONS, ActionItemOperation, TranscriptOperation
from app.agent.state import TurnContext

MAX_TOOL_OUTPUT_CHARS = 12_000


def turn_context(config: RunnableConfig) -> TurnContext:
    """Return the per-turn context carried in the run configuration."""
    return config["configurable"]["turn"]


def mmss(seconds: float) -> str:
    """Format seconds as MM:SS."""
    whole = int(seconds)
    return f"{whole // 60:02d}:{whole % 60:02d}"


def wrap_transcript(revision: int | None, lines: list[str]) -> str:
    """Wrap meeting text in ``<transcript>`` tags so the model treats it as untrusted data.

    Args:
        revision: Transcript revision the text reflects, when known.
        lines: Already formatted lines of meeting content.

    Returns:
        Text with a notice and the lines inside ``<transcript>`` tags, truncated to a safe length.
    """
    attr = f' revision="{revision}"' if revision is not None else ""
    body = "\n".join(lines)
    if len(body) > MAX_TOOL_OUTPUT_CHARS:
        body = body[:MAX_TOOL_OUTPUT_CHARS] + "\n[...truncated]"
    return f"{TRANSCRIPT_NOTICE}\n<transcript{attr}>\n{body}\n</transcript>"


def segment_line(segment: dict[str, Any]) -> str:
    """One segment as a line with its id, so edits can target exact ids."""
    return (
        f"id={segment['segment_id']} {segment['speaker_label']} "
        f"({mmss(segment['start_time'])}-{mmss(segment['end_time'])}): {segment['text']}"
    )


def tool_error(exc: BackendToolError) -> str:
    """Render a backend refusal for the model."""
    return f"Error [{exc.code}] (HTTP {exc.status}): {exc.message}"


@tool
async def get_meeting_overview(config: RunnableConfig) -> str:
    """Get the meeting title, processing state, transcript revision and per-speaker talk time."""
    ctx = turn_context(config)
    try:
        data = await ctx.backend.overview(ctx.meeting_id)
    except BackendToolError as exc:
        return tool_error(exc)
    speakers = ", ".join(
        f"{s['speaker_label']} ({s['segments']} đoạn, {round(s['talk_time_seconds'])}s)"
        for s in data["speakers"]
    )
    return (
        f"Tiêu đề: {data['title']}\nTrạng thái: {data['status']}\n"
        f"Thời lượng: {round(data['duration_seconds'])}s, {data['segments_count']} đoạn\n"
        f"Revision transcript: {data['transcript_revision']}\n"
        f"Tóm tắt: {data['summary_status']}, chỉ mục: {data['index_status']}\n"
        f"Người nói: {speakers}"
    )


@tool
async def search_transcript(query: str, config: RunnableConfig, k: int = 5) -> str:
    """Search the meeting transcript for passages relevant to a question.

    Results are labelled [S1], [S2], ... Cite them with the same labels in the answer.

    Args:
        query: What to look for, in natural language.
        k: Number of passages to return (1-10).
    """
    ctx = turn_context(config)
    try:
        hits = await ctx.backend.search(ctx.meeting_id, query, max(1, min(k, 10)))
    except BackendToolError as exc:
        return tool_error(exc)
    if not hits:
        return "Không tìm thấy đoạn nào phù hợp."
    lines = []
    for hit in hits:
        label = f"S{len(ctx.sources) + 1}"
        first_segment = hit["segment_ids"][0] if hit["segment_ids"] else hit["chunk_id"]
        ctx.sources[label] = {
            "segment_id": first_segment,
            "speaker_label": hit["speaker_label"],
            "start_time": hit["start_time"],
            "end_time": hit["end_time"],
            "quote": hit["text"][:120],
        }
        lines.append(
            f"[{label}] {hit['speaker_label']} ({mmss(hit['start_time'])}-{mmss(hit['end_time'])}): {hit['text']}"
        )
    return wrap_transcript(None, lines)


@tool
async def read_segments(
    config: RunnableConfig,
    from_time: float | None = None,
    to_time: float | None = None,
    speaker: str | None = None,
    limit: int = 50,
) -> str:
    """Read transcript segments, optionally limited to a time window (seconds) or one speaker.

    Each line starts with the segment id needed for edit proposals.

    Args:
        from_time: Start of the window in seconds.
        to_time: End of the window in seconds.
        speaker: Exact speaker label to filter by.
        limit: Maximum segments (1-200).
    """
    ctx = turn_context(config)
    try:
        segments = await ctx.backend.read_segments(
            ctx.meeting_id, from_time, to_time, speaker, max(1, min(limit, 200))
        )
    except BackendToolError as exc:
        return tool_error(exc)
    if not segments:
        return "Không có đoạn nào trong phạm vi này."
    return wrap_transcript(ctx.base_revision, [segment_line(s) for s in segments])


@tool
async def find_text(pattern: str, config: RunnableConfig, case_sensitive: bool = False) -> str:
    """Find segments that contain an exact piece of text and return their ids.

    Use this before proposing a replace or delete so the ids are real.

    Args:
        pattern: Literal text to look for.
        case_sensitive: Whether letter case must match.
    """
    ctx = turn_context(config)
    try:
        matches = await ctx.backend.find_text(ctx.meeting_id, pattern, case_sensitive)
    except BackendToolError as exc:
        return tool_error(exc)
    if not matches:
        return f"Không đoạn nào chứa '{pattern}'."
    return wrap_transcript(ctx.base_revision, [segment_line(s) for s in matches])


@tool
async def get_summary(config: RunnableConfig) -> str:
    """Get the generated summary, key points and action items (with their ids)."""
    ctx = turn_context(config)
    try:
        data = await ctx.backend.get_summary(ctx.meeting_id)
    except BackendToolError as exc:
        return tool_error(exc)
    items = "\n".join(
        f"id={i['id']} [{i['status']}] {i['description']} (phụ trách: {i['assignee']})"
        for i in data["action_items"]
    )
    points = "\n".join(f"- {p}" for p in data["key_points"])
    return wrap_transcript(
        None,
        [
            f"Trạng thái tóm tắt: {data['summary_status']}",
            f"Tóm tắt: {data['executive_summary'] or '(chưa có)'}",
            f"Ý chính:\n{points}",
            f"Action items:\n{items}",
        ],
    )


async def _propose(config: RunnableConfig, body: dict[str, Any], explanation: str) -> str:
    ctx = turn_context(config)
    try:
        action = await ctx.backend.propose(ctx.meeting_id, {**body, "base_revision": ctx.base_revision})
    except BackendToolError as exc:
        return tool_error(exc)
    ctx.proposals.append({"action_id": action["id"], "kind": action["kind"], "explanation": explanation})
    return (
        f"Đã tạo đề xuất {action['id']} ({action['kind']}). Đề xuất đang CHỜ người dùng duyệt, "
        "chưa có thay đổi nào được áp dụng."
    )


@tool
async def propose_transcript_edits(
    operations: list[TranscriptOperation], explanation: str, config: RunnableConfig
) -> str:
    """Propose edits to the transcript. Nothing is applied until the user approves.

    Operations: update_text, replace_text, rename_speaker, reassign_speaker,
    delete_segments, split_segment, merge_segments. Use real segment ids from find_text
    or read_segments.

    Args:
        operations: Up to 200 operations applied together as one change.
        explanation: One sentence telling the user what this change does.
    """
    if len(operations) > MAX_PROPOSAL_OPERATIONS:
        return f"Error: at most {MAX_PROPOSAL_OPERATIONS} operations per proposal."
    return await _propose(
        config,
        {
            "kind": "transcript_ops",
            "operations": [op.model_dump(mode="json", exclude_none=True) for op in operations],
        },
        explanation,
    )


@tool
async def propose_action_item_changes(
    operations: list[ActionItemOperation], explanation: str, config: RunnableConfig
) -> str:
    """Propose creating, updating or deleting action items. Nothing is applied until the user approves.

    Args:
        operations: Up to 200 action item operations.
        explanation: One sentence telling the user what this change does.
    """
    if len(operations) > MAX_PROPOSAL_OPERATIONS:
        return f"Error: at most {MAX_PROPOSAL_OPERATIONS} operations per proposal."
    return await _propose(
        config,
        {
            "kind": "action_item_ops",
            "action_item_operations": [
                op.model_dump(mode="json", exclude_none=True) for op in operations
            ],
        },
        explanation,
    )


@tool
async def request_summary_regeneration(explanation: str, config: RunnableConfig) -> str:
    """Propose regenerating the summary and action items from the current transcript.

    Args:
        explanation: One sentence telling the user why.
    """
    return await _propose(config, {"kind": "summary_regenerate"}, explanation)


@tool
async def create_artifact(
    kind: str, title: str, config: RunnableConfig, content_markdown: str | None = None
) -> str:
    """Generate a document stored with the meeting (no approval needed, nothing is overwritten).

    Args:
        kind: minutes_docx (Word minutes), email_draft, srt (subtitles) or custom_md.
        title: Document title.
        content_markdown: Markdown body. Required for email_draft and custom_md; optional for
            minutes_docx, which otherwise uses the standard minutes layout.
    """
    ctx = turn_context(config)
    body: dict[str, Any] = {"kind": kind, "title": title}
    if content_markdown:
        body["content_markdown"] = content_markdown
    try:
        artifact = await ctx.backend.create_artifact(ctx.meeting_id, body)
    except BackendToolError as exc:
        return tool_error(exc)
    return f"Đã tạo tài liệu '{artifact['title']}' (id {artifact['id']}). Người dùng có thể tải xuống ở tab Tài liệu."


READ_TOOLS: list[BaseTool] = [
    get_meeting_overview,
    search_transcript,
    read_segments,
    find_text,
    get_summary,
]
WRITE_TOOLS: list[BaseTool] = [
    propose_transcript_edits,
    propose_action_item_changes,
    request_summary_regeneration,
    create_artifact,
]
ALL_TOOLS: list[BaseTool] = [*READ_TOOLS, *WRITE_TOOLS]
CONNECTION_ERRORS = (httpx.ConnectError, httpx.ConnectTimeout)

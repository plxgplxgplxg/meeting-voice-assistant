import uuid
from dataclasses import dataclass
from typing import Protocol

from sqlalchemy import delete, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.clients.ai_service_client import AIServiceClient
from app.models.transcript import TranscriptSegmentModel
from app.models.transcript_chunk import TranscriptChunkModel
from app.services.chunking import chunk_by_speaker_turn

EMBED_BATCH_SIZE = 64
CANDIDATES_PER_STREAM = 30
RRF_K = 60

HYBRID_SEARCH_SQL = text(
    """
    WITH dense AS (
        SELECT id, ROW_NUMBER() OVER (ORDER BY embedding <=> CAST(:qvec AS vector)) AS r
        FROM transcript_chunks
        WHERE meeting_id = :meeting_id
        ORDER BY embedding <=> CAST(:qvec AS vector)
        LIMIT :candidates
    ),
    lexical AS (
        SELECT c.id, ROW_NUMBER() OVER (ORDER BY ts_rank(c.tsv, q.query) DESC) AS r
        FROM transcript_chunks c, websearch_to_tsquery('simple', :qtext) AS q(query)
        WHERE c.meeting_id = :meeting_id AND c.tsv @@ q.query
        ORDER BY ts_rank(c.tsv, q.query) DESC
        LIMIT :candidates
    ),
    fused AS (
        SELECT COALESCE(d.id, l.id) AS id,
               COALESCE(1.0 / (:rrf_k + d.r), 0) + COALESCE(1.0 / (:rrf_k + l.r), 0) AS score
        FROM dense d FULL OUTER JOIN lexical l ON d.id = l.id
    )
    SELECT c.id, f.score
    FROM fused f JOIN transcript_chunks c ON c.id = f.id
    ORDER BY f.score DESC, c.chunk_index ASC
    LIMIT :k
    """
)


@dataclass(frozen=True, slots=True)
class RetrievedChunk:
    """A transcript chunk returned by retrieval, with its fused relevance score."""

    id: uuid.UUID
    chunk_index: int
    speaker_label: str
    start_time: float
    end_time: float
    text: str
    segment_ids: list[uuid.UUID]
    score: float


class TranscriptIndexer(Protocol):
    """Seam for rebuilding a meeting's retrieval index."""

    async def rebuild_index(self, meeting_id: uuid.UUID, revision: int) -> int:
        """Rebuild all chunks of a meeting from its current transcript.

        Args:
            meeting_id: Meeting to index.
            revision: Transcript revision the index reflects.

        Returns:
            Number of chunks written.
        """
        ...


class TranscriptRetriever(Protocol):
    """Seam for searching a meeting's transcript."""

    async def search(self, meeting_id: uuid.UUID, query: str, k: int = 5) -> list[RetrievedChunk]:
        """Return the top-k chunks for a query.

        Args:
            meeting_id: Meeting to search.
            query: Natural-language question.
            k: Maximum number of chunks.

        Returns:
            Chunks ordered by relevance.
        """
        ...


def vector_literal(vector: list[float]) -> str:
    """Format a vector in pgvector's text input form, e.g. ``[0.1,0.2]``."""
    return "[" + ",".join(repr(float(value)) for value in vector) + "]"


class RetrievalService:
    """Backend-owned hybrid retrieval over ``transcript_chunks`` (pgvector plus full text, fused with RRF).

    The AI service only computes embeddings, so filtering by meeting (and later
    by project) stays in SQL and the AI service never needs the transcript.
    """

    def __init__(self, session: AsyncSession, ai_client: AIServiceClient) -> None:
        """Initialize the service.

        Args:
            session: Active SQLAlchemy session.
            ai_client: Client used to embed passages and queries.
        """
        self.session = session
        self.ai_client = ai_client

    async def rebuild_index(self, meeting_id: uuid.UUID, revision: int) -> int:
        segments = (
            await self.session.scalars(
                select(TranscriptSegmentModel)
                .where(TranscriptSegmentModel.meeting_id == meeting_id)
                .order_by(TranscriptSegmentModel.sequence_order)
            )
        ).all()
        chunks = chunk_by_speaker_turn(
            [
                {
                    "segment_id": segment.id,
                    "speaker": segment.speaker_label,
                    "start": segment.start_time,
                    "end": segment.end_time,
                    "text": segment.content,
                }
                for segment in segments
            ]
        )

        embeddings: list[list[float]] = []
        texts = [f"{chunk['speaker']}: {chunk['text']}" for chunk in chunks]
        for offset in range(0, len(texts), EMBED_BATCH_SIZE):
            batch = texts[offset : offset + EMBED_BATCH_SIZE]
            embeddings.extend(await self.ai_client.embed(batch, "passage"))

        await self.session.execute(
            delete(TranscriptChunkModel).where(TranscriptChunkModel.meeting_id == meeting_id)
        )
        for chunk, embedding in zip(chunks, embeddings, strict=True):
            self.session.add(
                TranscriptChunkModel(
                    meeting_id=meeting_id,
                    chunk_index=chunk["seq"],
                    speaker_label=chunk["speaker"],
                    start_time=chunk["start"],
                    end_time=chunk["end"],
                    text=chunk["text"],
                    segment_ids=chunk["segment_ids"],
                    embedding=embedding,
                    transcript_revision=revision,
                )
            )
        await self.session.flush()
        return len(chunks)

    async def search(self, meeting_id: uuid.UUID, query: str, k: int = 5) -> list[RetrievedChunk]:
        query_vector = (await self.ai_client.embed([query], "query"))[0]
        rows = (
            await self.session.execute(
                HYBRID_SEARCH_SQL,
                {
                    "qvec": vector_literal(query_vector),
                    "qtext": query,
                    "meeting_id": meeting_id,
                    "candidates": CANDIDATES_PER_STREAM,
                    "rrf_k": RRF_K,
                    "k": k,
                },
            )
        ).all()
        if not rows:
            return []

        scores = {row.id: float(row.score) for row in rows}
        chunks = (
            await self.session.scalars(
                select(TranscriptChunkModel).where(TranscriptChunkModel.id.in_(scores))
            )
        ).all()
        ordered = sorted(chunks, key=lambda c: (-scores[c.id], c.chunk_index))
        return [
            RetrievedChunk(
                id=c.id,
                chunk_index=c.chunk_index,
                speaker_label=c.speaker_label,
                start_time=c.start_time,
                end_time=c.end_time,
                text=c.text,
                segment_ids=list(c.segment_ids),
                score=scores[c.id],
            )
            for c in ordered
        ]

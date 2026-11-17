from typing import Any

import anyio.to_thread
import numpy as np
import structlog

from app.rag.embeddings import EmbeddingModelWrapper
from app.rag.protocols import EmbeddingProviderProtocol

logger = structlog.get_logger(__name__)


def cosine_similarity(v1: list[float] | np.ndarray, v2: list[float] | np.ndarray) -> float:
    """Calculate cosine similarity between two vector embeddings.

    Args:
        v1: First embedding vector.
        v2: Second embedding vector.

    Returns:
        Cosine similarity score in range [-1.0, 1.0].
    """
    a = np.array(v1, dtype=np.float32)
    b = np.array(v2, dtype=np.float32)
    norm_a = np.linalg.norm(a)
    norm_b = np.linalg.norm(b)
    if norm_a == 0.0 or norm_b == 0.0:
        return 0.0
    return float(np.dot(a, b) / (norm_a * norm_b))


class MeetingRetriever:
    """Hybrid search retriever combining Dense E5 embeddings and Lexical term matching with RRF."""

    def __init__(
        self,
        embedding_provider: EmbeddingProviderProtocol | None = None,
        embedding_wrapper: EmbeddingProviderProtocol | None = None,
    ) -> None:
        """Initialize MeetingRetriever.

        Args:
            embedding_provider: Implementation of EmbeddingProviderProtocol. Defaults to EmbeddingModelWrapper.
            embedding_wrapper: Alias for embedding_provider for backwards compatibility.
        """
        self.embedding_provider = embedding_provider or embedding_wrapper or EmbeddingModelWrapper()
        self.embedding_wrapper = self.embedding_provider

    def lexical_score(self, query: str, text: str) -> float:
        """Compute term overlap score between query keywords and candidate text.

        Args:
            query: User query string.
            text: Candidate segment text.

        Returns:
            Lexical similarity score.
        """
        query_terms = [t.lower() for t in query.split() if len(t) > 2]
        if not query_terms:
            return 0.0

        content_lower = text.lower()
        matched = sum(1 for t in query_terms if t in content_lower)
        return matched / len(query_terms)

    async def retrieve(
        self,
        query: str,
        segments: list[dict[str, Any]],
        top_k: int = 5,
        rrf_k: int = 60,
    ) -> list[dict[str, Any]]:
        """Retrieve top-k relevant segments using Hybrid Search (Dense + Lexical + RRF).

        Args:
            query: The question or query string.
            segments: List of candidate transcript segments.
            top_k: Number of highest-ranked segments to return.
            rrf_k: Reciprocal Rank Fusion constant (default 60).

        Returns:
            Ranked list of segment dictionaries with composite relevance score.
        """
        if not segments:
            return []

        if len(segments) <= top_k:
            return segments

        # 1. Dense Scoring
        # Prepend 'query: ' for E5 query embeddings
        query_embedding = (
            await anyio.to_thread.run_sync(self.embedding_provider.encode, [f"query: {query}"])
        )[0]

        segment_texts = [
            f"passage: {s.get('speaker', '')}: {s.get('text', s.get('content', ''))}"
            for s in segments
        ]
        segment_embeddings = await anyio.to_thread.run_sync(
            self.embedding_provider.encode, segment_texts
        )

        dense_scores = [
            cosine_similarity(query_embedding, emb)
            for emb in segment_embeddings
        ]

        # 2. Lexical Scoring
        lexical_scores = [
            self.lexical_score(query, s.get("text", s.get("content", "")))
            for s in segments
        ]

        # 3. Rank calculation for RRF
        dense_order = np.argsort(-np.array(dense_scores))
        dense_ranks = {int(idx): rank for rank, idx in enumerate(dense_order)}

        lexical_order = np.argsort(-np.array(lexical_scores))
        lexical_ranks = {int(idx): rank for rank, idx in enumerate(lexical_order)}

        # 4. RRF Score Fusion
        scored_candidates: list[tuple[float, dict[str, Any]]] = []
        for idx, seg in enumerate(segments):
            r_dense = dense_ranks[idx]
            r_lex = lexical_ranks[idx]
            rrf_score = (1.0 / (rrf_k + r_dense)) + (1.0 / (rrf_k + r_lex))
            seg_copy = dict(seg)
            seg_copy["rrf_score"] = rrf_score
            seg_copy["dense_score"] = dense_scores[idx]
            seg_copy["lexical_score"] = lexical_scores[idx]
            scored_candidates.append((rrf_score, seg_copy))

        scored_candidates.sort(key=lambda x: x[0], reverse=True)
        return [cand[1] for cand in scored_candidates[:top_k]]

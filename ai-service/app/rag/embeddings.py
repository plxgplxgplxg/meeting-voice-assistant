import structlog

from app.core.config import ai_settings
from app.rag.protocols import EmbeddingProviderProtocol

logger = structlog.get_logger(__name__)


class EmbeddingModelWrapper(EmbeddingProviderProtocol):
    """Embedding generator wrapper for vector search.

    Optimized for lightweight local execution on CPU using multilingual-e5-small (384 dimensions).
    """

    def __init__(self, model_name: str | None = None) -> None:
        self.model_name = model_name or ai_settings.embedding_model_name
        self._model = None

    def _load_model(self) -> None:
        """Lazily load SentenceTransformer model on CPU."""
        if self._model is None:
            try:
                from sentence_transformers import SentenceTransformer
                self._model = SentenceTransformer(self.model_name, device=ai_settings.device)
                logger.info("embedding_model_loaded", model=self.model_name, device=ai_settings.device)
            except Exception as exc:
                logger.warning("embedding_model_load_failed", error=str(exc))
                self._model = None

    def encode(self, texts: list[str]) -> list[list[float]]:
        """Convert input text list into embedding vectors.

        Args:
            texts: List of strings to encode.

        Returns:
            List of float vector embeddings (384 dimensions).
        """
        if not texts:
            return []

        self._load_model()
        if self._model is not None:
            try:
                embeddings = self._model.encode(texts, normalize_embeddings=True)
                return [emb.tolist() for emb in embeddings]
            except Exception as exc:
                logger.error("embedding_encode_failed", error=str(exc))

        # Deterministic 384-dimensional fallback vector if model not present
        return [[0.0] * 384 for _ in texts]

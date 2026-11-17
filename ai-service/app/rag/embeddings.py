import structlog

from app.core.config import ai_settings
from app.core.errors import ProviderError, ProviderNotConfiguredError
from app.rag.protocols import EmbeddingProviderProtocol

logger = structlog.get_logger(__name__)


class EmbeddingModelWrapper(EmbeddingProviderProtocol):
    """Embedding generator wrapper for vector search.

    Optimized for lightweight local execution on CPU using multilingual-e5-small (384 dimensions).
    Failures are raised: zero vectors would silently make dense retrieval meaningless.
    """

    def __init__(self, model_name: str | None = None) -> None:
        self.model_name = model_name or ai_settings.embedding_model_name
        self._model = None

    @property
    def is_loaded(self) -> bool:
        """Whether the model is in memory."""
        return self._model is not None

    def load(self) -> None:
        """Load the SentenceTransformer model, blocking until it is ready.

        Intended to run once at startup in a worker thread.

        Raises:
            ProviderNotConfiguredError: If the model cannot be imported or loaded.
        """
        if self._model is not None:
            return
        try:
            from sentence_transformers import SentenceTransformer

            self._model = SentenceTransformer(self.model_name, device=ai_settings.device)
        except Exception as exc:
            logger.error("embedding_model_load_failed", model=self.model_name, error=str(exc))
            raise ProviderNotConfiguredError(
                f"Embedding model '{self.model_name}' is unavailable: {exc}"
            ) from exc
        logger.info("embedding_model_loaded", model=self.model_name, device=ai_settings.device)

    def encode(self, texts: list[str]) -> list[list[float]]:
        """Convert input texts into normalized embedding vectors.

        This call is CPU bound and synchronous; async callers must run it in a
        worker thread.

        Args:
            texts: List of strings to encode.

        Returns:
            List of float vector embeddings (384 dimensions).

        Raises:
            ProviderNotConfiguredError: If the model is not available.
            ProviderError: If encoding fails.
        """
        if not texts:
            return []

        self.load()
        try:
            embeddings = self._model.encode(texts, normalize_embeddings=True)
        except Exception as exc:
            logger.error("embedding_encode_failed", error=str(exc))
            raise ProviderError(f"Embedding encode failed: {exc}") from exc
        return [embedding.tolist() for embedding in embeddings]

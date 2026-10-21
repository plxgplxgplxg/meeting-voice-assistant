class EmbeddingModelWrapper:
    """Embedding generator wrapper for vector search."""

    def __init__(self, model_name: str) -> None:
        self.model_name = model_name

    def encode(self, texts: list[str]) -> list[list[float]]:
        """Convert input text list into embedding vectors.

        Args:
            texts: List of strings to encode.

        Returns:
            List of float vector embeddings.
        """
        return [[0.0] * 384 for _ in texts]

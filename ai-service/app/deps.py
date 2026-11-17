from pathlib import Path
from typing import Annotated

from fastapi import Depends, Request

from app.core.config import ai_settings
from app.core.errors import AudioNotFoundError, InvalidStorageKeyError, ProviderNotConfiguredError
from app.pipelines.fake import FakeAudioProcessor
from app.pipelines.gladia import GladiaAudioPipeline
from app.pipelines.protocols import AudioProcessorProtocol
from app.rag.fake import FakeLLMClient
from app.rag.generator import MeetingSummaryGenerator, RAGAnswerGenerator
from app.rag.llm_client import OpenAICompatibleLLMClient
from app.rag.protocols import EmbeddingProviderProtocol, LLMClientProtocol
from app.rag.retriever import MeetingRetriever


def build_audio_processor() -> AudioProcessorProtocol:
    """Select the ASR adapter from configuration.

    Returns:
        ``FakeAudioProcessor`` for the development mock engine, otherwise Gladia.

    Raises:
        ProviderNotConfiguredError: If the mock engine is requested in production.
    """
    if ai_settings.use_mock_engine:
        if ai_settings.is_production:
            raise ProviderNotConfiguredError("Mock engine is disabled in production.")
        return FakeAudioProcessor()
    return GladiaAudioPipeline()


def build_llm_client(request: Request) -> LLMClientProtocol:
    """Select the LLM adapter, reusing the lifespan HTTP client when available.

    Args:
        request: Current request, used to reach ``app.state``.

    Returns:
        ``FakeLLMClient`` for the development mock engine, otherwise the OpenAI-compatible client.
    """
    if ai_settings.use_mock_engine and not ai_settings.is_production:
        return FakeLLMClient()
    return OpenAICompatibleLLMClient(client=getattr(request.app.state, "http", None))


def get_audio_processor() -> AudioProcessorProtocol:
    """Provide the ASR adapter."""
    return build_audio_processor()


def get_llm_client(request: Request) -> LLMClientProtocol:
    """Provide the LLM adapter."""
    return build_llm_client(request)


def get_embedder(request: Request) -> EmbeddingProviderProtocol:
    """Provide the process-wide embedding model created at startup."""
    return request.app.state.embedder


LLMClient = Annotated[LLMClientProtocol, Depends(get_llm_client)]
Embedder = Annotated[EmbeddingProviderProtocol, Depends(get_embedder)]
AudioProcessor = Annotated[AudioProcessorProtocol, Depends(get_audio_processor)]


def get_summary_generator(llm: LLMClient) -> MeetingSummaryGenerator:
    """Provide the summary generator bound to the LLM adapter."""
    return MeetingSummaryGenerator(llm_client=llm)


def get_answer_generator(llm: LLMClient) -> RAGAnswerGenerator:
    """Provide the RAG answer generator bound to the LLM adapter."""
    return RAGAnswerGenerator(llm_client=llm)


def get_retriever(embedder: Embedder) -> MeetingRetriever:
    """Provide the hybrid retriever bound to the shared embedder."""
    return MeetingRetriever(embedding_provider=embedder)


SummaryGeneratorDep = Annotated[MeetingSummaryGenerator, Depends(get_summary_generator)]
AnswerGeneratorDep = Annotated[RAGAnswerGenerator, Depends(get_answer_generator)]
RetrieverDep = Annotated[MeetingRetriever, Depends(get_retriever)]


def resolve_storage_key(storage_key: str) -> Path:
    """Translate a storage key into a file path confined to the storage root.

    Args:
        storage_key: Key relative to ``STORAGE_ROOT``.

    Returns:
        Absolute path of an existing file inside the storage root.

    Raises:
        InvalidStorageKeyError: If the key is empty, absolute, or escapes the root.
        AudioNotFoundError: If no file exists for the key.
    """
    root = Path(ai_settings.storage_root).resolve()
    candidate = (root / storage_key).resolve()
    if not storage_key or candidate == root or root not in candidate.parents:
        raise InvalidStorageKeyError("Invalid storage key.")
    if not candidate.is_file():
        raise AudioNotFoundError("Audio file not found in storage.")
    return candidate

"""
Enterprise RAG Knowledge Assistant — Embedding Service

Generates vector embeddings for document chunks and queries.
Default provider: OpenAI (text-embedding-3-small).
Supports deterministic mock embeddings for offline testing without API keys.

Phase 3 of the implementation plan.
"""

import hashlib
import logging
import math
from typing import Any

from langchain_core.embeddings import Embeddings

from backend.app.core.config import settings

logger = logging.getLogger(__name__)

# Standard dimension for text-embedding-3-small
DEFAULT_EMBEDDING_DIM = 1536


class MockEmbeddings(Embeddings):
    """
    Deterministic pseudo-embeddings for testing without external API calls.
    Generates a normalized 1536-dimensional vector based on the SHA-256 hash of the text.
    """

    def __init__(self, dimension: int = DEFAULT_EMBEDDING_DIM) -> None:
        self.dimension = dimension

    def _text_to_vector(self, text: str) -> list[float]:
        """Produce a normalized float vector using word-level feature hashing."""
        import re
        vector = [0.0] * self.dimension
        words = re.findall(r"\w+", text.lower())
        if not words:
            # Avoid divide by zero
            vector[0] = 1.0
            return vector

        for word in words:
            # Hash word into bucket index
            idx = int(hashlib.md5(word.encode("utf-8")).hexdigest(), 16) % self.dimension
            vector[idx] += 1.0

        # Normalize vector to unit length for cosine distance
        norm = math.sqrt(sum(x * x for x in vector)) or 1.0
        return [x / norm for x in vector]

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return [self._text_to_vector(t) for t in texts]

    def embed_query(self, text: str) -> list[float]:
        return self._text_to_vector(text)



class EmbeddingService:
    """
    Service wrapper around embedding generation.
    Enables swapping providers and using mock embeddings for automated tests.
    """

    def __init__(
        self,
        api_key: str | None = None,
        model_name: str | None = None,
        use_mock: bool = False,
    ) -> None:
        self.api_key = api_key if api_key is not None else settings.openai_api_key
        self.model_name = model_name if model_name is not None else settings.embedding_model
        self.use_mock = use_mock

        self._embeddings: Embeddings | None = None

    def get_embeddings(self) -> Embeddings:
        """
        Return the configured LangChain Embeddings instance.
        Falls back to MockEmbeddings if use_mock is True or if no API key is provided.
        """
        if self._embeddings is not None:
            return self._embeddings

        # Check for Google Gemini API key first
        if settings.google_api_key and "replace-" not in settings.google_api_key:
            try:
                from langchain_google_genai import GoogleGenerativeAIEmbeddings

                logger.info("Initializing GoogleGenerativeAIEmbeddings with model '%s'", settings.gemini_embedding_model)
                self._embeddings = GoogleGenerativeAIEmbeddings(
                    model=settings.gemini_embedding_model,
                    google_api_key=settings.google_api_key,
                )
                return self._embeddings
            except Exception as e:
                logger.warning("Failed to initialize GoogleGenerativeAIEmbeddings: %s", e)

        # Check for OpenAI API key
        if self.api_key and "replace-" not in self.api_key and not self.use_mock:
            try:
                from langchain_openai import OpenAIEmbeddings

                logger.info("Initializing OpenAIEmbeddings with model '%s'", self.model_name)
                self._embeddings = OpenAIEmbeddings(
                    api_key=self.api_key,
                    model=self.model_name,
                )
                return self._embeddings
            except Exception as e:
                logger.warning("Failed to initialize OpenAIEmbeddings: %s", e)

        # Fallback to offline mock embeddings
        logger.info("Using deterministic MockEmbeddings (offline mode, no API key required)")
        self._embeddings = MockEmbeddings(dimension=DEFAULT_EMBEDDING_DIM)
        return self._embeddings


    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        """Generate embeddings for a list of document chunk texts with automatic fallback."""
        if not texts:
            return []
        try:
            embeddings = self.get_embeddings()
            return embeddings.embed_documents(texts)
        except Exception as e:
            logger.warning(
                "Embedding API call failed (%s). Falling back to local deterministic embeddings.",
                e,
            )
            fallback = MockEmbeddings(dimension=DEFAULT_EMBEDDING_DIM)
            return fallback.embed_documents(texts)

    def embed_query(self, text: str) -> list[float]:
        """Generate embedding for a single user query with automatic fallback."""
        try:
            embeddings = self.get_embeddings()
            return embeddings.embed_query(text)
        except Exception as e:
            logger.warning(
                "Query embedding API call failed (%s). Falling back to local deterministic embeddings.",
                e,
            )
            fallback = MockEmbeddings(dimension=DEFAULT_EMBEDDING_DIM)
            return fallback.embed_query(text)


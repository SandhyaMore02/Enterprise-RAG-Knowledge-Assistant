"""
Enterprise RAG Knowledge Assistant — Retrieval Service

Orchestrates semantic search over indexed documents.
Extracts relevant context chunks and attaches provenance metadata.
Evaluates retrieval confidence to avoid hallucinating when evidence is weak.

Phase 4 of the implementation plan.
"""

import logging
from dataclasses import dataclass
from typing import Any

from backend.app.core.config import settings
from backend.app.services.vector_store import VectorStoreService

logger = logging.getLogger(__name__)

# Minimum similarity threshold to consider evidence confident
MIN_CONFIDENCE_THRESHOLD = 0.35


@dataclass
class RetrievedChunk:
    """A retrieved chunk enriched with source provenance and relevance score."""

    text: str
    document_id: str
    filename: str
    page: int | None = None
    relevance_score: float = 0.0
    distance: float = 0.0
    metadata: dict[str, Any] | None = None

    def to_citation(self) -> dict[str, Any]:
        """Convert to a citation dictionary for client responses."""
        return {
            "document_id": self.document_id,
            "filename": self.filename,
            "page": self.page,
        }


@dataclass
class RetrievalResult:
    """Output of the retrieval pipeline."""

    query: str
    chunks: list[RetrievedChunk]
    has_sufficient_evidence: bool = True
    context_text: str = ""

    @property
    def citations(self) -> list[dict[str, Any]]:
        """Deduplicated citations from retrieved chunks."""
        seen = set()
        citations = []
        for c in self.chunks:
            key = (c.document_id, c.filename, c.page)
            if key not in seen:
                seen.add(key)
                citations.append(c.to_citation())
        return citations


class RetrievalService:
    """
    Retrieves and filters relevant document chunks for answering queries.
    """

    def __init__(self, vector_store: VectorStoreService | None = None) -> None:
        self.vector_store = vector_store or VectorStoreService()

    def retrieve(
        self,
        query: str,
        top_k: int | None = None,
        filter_document_id: str | None = None,
        min_threshold: float = MIN_CONFIDENCE_THRESHOLD,
    ) -> RetrievalResult:
        """
        Retrieve chunks matching the query and evaluate evidence strength.

        Args:
            query: User's question.
            top_k: Number of chunks to retrieve.
            filter_document_id: Optional filter for a specific document.
            min_threshold: Minimum similarity score to be considered sufficient.

        Returns:
            RetrievalResult containing chunks, formatted context, and evidence flag.
        """
        k = top_k if top_k is not None else settings.top_k
        raw_matches = self.vector_store.search(
            query=query,
            top_k=k,
            filter_document_id=filter_document_id,
        )

        retrieved_chunks: list[RetrievedChunk] = []
        for m in raw_matches:
            retrieved_chunks.append(
                RetrievedChunk(
                    text=m.get("text", ""),
                    document_id=m.get("document_id", ""),
                    filename=m.get("source", "Unknown"),
                    page=m.get("page"),
                    relevance_score=m.get("relevance_score", 0.0),
                    distance=m.get("distance", 0.0),
                    metadata=m.get("metadata"),
                )
            )

        # Check if evidence is sufficient
        has_evidence = False
        if retrieved_chunks:
            # If the best match exceeds the minimum confidence threshold
            top_score = max(c.relevance_score for c in retrieved_chunks)
            has_evidence = top_score >= min_threshold

        # Build formatted context string for LLM injection
        context_parts = []
        for i, c in enumerate(retrieved_chunks, 1):
            page_info = f", Page {c.page}" if c.page else ""
            context_parts.append(
                f"[Source {i}: {c.filename}{page_info}]\n{c.text}"
            )
        context_text = "\n\n---\n\n".join(context_parts)

        logger.info(
            "Query '%s' retrieved %d chunks (sufficient_evidence=%s)",
            query,
            len(retrieved_chunks),
            has_evidence,
        )

        return RetrievalResult(
            query=query,
            chunks=retrieved_chunks,
            has_sufficient_evidence=has_evidence,
            context_text=context_text,
        )

"""
Enterprise RAG Knowledge Assistant — Vector Store Service

Manages document chunk persistence and similarity search using ChromaDB.
Handles persistent storage, duplicate prevention, document deletion, and document listing.

Phase 3 and Phase 4 of the implementation plan.
"""

import logging
from pathlib import Path
from typing import Any

import chromadb
from chromadb.config import Settings as ChromaSettings

from backend.app.core.config import settings
from backend.app.services.chunking_service import DocumentChunk
from backend.app.services.embedding_service import EmbeddingService

logger = logging.getLogger(__name__)

COLLECTION_NAME = "enterprise_rag_knowledge"


class VectorStoreService:
    """
    ChromaDB-backed vector database service for document chunks.
    """

    def __init__(
        self,
        persist_directory: Path | str | None = None,
        embedding_service: EmbeddingService | None = None,
        in_memory: bool = False,
    ) -> None:
        self.embedding_service = embedding_service or EmbeddingService()

        if in_memory:
            self.client = chromadb.Client()
        else:
            persist_path = Path(persist_directory or settings.chroma_dir)
            persist_path.mkdir(parents=True, exist_ok=True)
            self.client = chromadb.PersistentClient(
                path=str(persist_path),
                settings=ChromaSettings(anonymized_telemetry=False),
            )

        # Use cosine distance for normalized embeddings
        self.collection = self.client.get_or_create_collection(
            name=COLLECTION_NAME,
            metadata={"hnsw:space": "cosine"},
        )
        logger.info(
            "Vector store initialized (collection: '%s', total chunks: %d)",
            COLLECTION_NAME,
            self.collection.count(),
        )

    def add_chunks(self, chunks: list[DocumentChunk], overwrite: bool = True) -> int:
        """
        Store document chunks in ChromaDB.

        Args:
            chunks: List of DocumentChunk instances.
            overwrite: If True, delete existing chunks for the same document_id first.

        Returns:
            Number of chunks added.
        """
        if not chunks:
            return 0

        document_id = chunks[0].document_id

        # Check for existing chunks of this document to prevent duplicates
        if overwrite:
            existing = self.get_chunks_for_document(document_id)
            if existing:
                logger.info(
                    "Document '%s' already exists with %d chunks. Overwriting...",
                    document_id,
                    len(existing),
                )
                self.delete_document(document_id)

        ids = [c.chunk_id for c in chunks]
        texts = [c.text for c in chunks]
        metadatas = [c.metadata for c in chunks]

        # Generate embeddings
        embeddings = self.embedding_service.embed_documents(texts)

        self.collection.add(
            ids=ids,
            documents=texts,
            metadatas=metadatas,
            embeddings=embeddings,
        )

        logger.info("Indexed %d chunks for document '%s'", len(chunks), document_id)
        return len(chunks)

    def delete_document(self, document_id: str) -> int:
        """
        Remove all chunks associated with a document_id.

        Returns:
            Number of deleted chunks.
        """
        existing = self.collection.get(
            where={"document_id": document_id},
            include=["metadatas"],
        )
        chunk_ids = existing.get("ids", [])
        if chunk_ids:
            self.collection.delete(ids=chunk_ids)
            logger.info("Deleted %d chunks for document '%s'", len(chunk_ids), document_id)
        return len(chunk_ids)

    def get_chunks_for_document(self, document_id: str) -> list[dict[str, Any]]:
        """Retrieve all chunks belonging to a document."""
        result = self.collection.get(
            where={"document_id": document_id},
            include=["documents", "metadatas"],
        )
        items = []
        ids = result.get("ids", [])
        docs = result.get("documents", [])
        metas = result.get("metadatas", [])
        for i, chunk_id in enumerate(ids):
            items.append({
                "chunk_id": chunk_id,
                "text": docs[i] if docs else "",
                "metadata": metas[i] if metas else {},
            })
        return items

    def list_documents(self) -> list[dict[str, Any]]:
        """
        List all indexed documents with summary statistics.

        Returns:
            List of dictionaries with document_id, filename, file_type, chunk_count.
        """
        all_records = self.collection.get(include=["metadatas", "documents"])
        metadatas = all_records.get("metadatas") or []
        documents = all_records.get("documents") or []

        doc_map: dict[str, dict[str, Any]] = {}
        for idx, meta in enumerate(metadatas):
            doc_id = meta.get("document_id")
            if not doc_id:
                continue

            doc_text = documents[idx] if idx < len(documents) else ""

            if doc_id not in doc_map:
                doc_map[doc_id] = {
                    "document_id": doc_id,
                    "filename": meta.get("source", doc_id),
                    "file_type": meta.get("file_type", "unknown"),
                    "chunk_count": 0,
                    "total_characters": 0,
                }

            doc_map[doc_id]["chunk_count"] += 1
            doc_map[doc_id]["total_characters"] += len(doc_text)

        return list(doc_map.values())

    def search(
        self,
        query: str,
        top_k: int | None = None,
        filter_document_id: str | None = None,
    ) -> list[dict[str, Any]]:
        """
        Perform vector similarity search for relevant chunks.

        Args:
            query: User's question or search query.
            top_k: Number of chunks to retrieve.
            filter_document_id: Optional filter for a specific document.

        Returns:
            List of dicts with text, metadata, distance, relevance_score.
        """
        k = top_k if top_k is not None else settings.top_k
        query = query.strip()
        if not query or self.collection.count() == 0:
            return []

        # Ensure we don't request more than available
        k = min(k, self.collection.count())

        query_vector = self.embedding_service.embed_query(query)

        where_clause = None
        if filter_document_id:
            where_clause = {"document_id": filter_document_id}

        results = self.collection.query(
            query_embeddings=[query_vector],
            n_results=k,
            where=where_clause,
            include=["documents", "metadatas", "distances"],
        )

        matched_chunks = []
        doc_list = results.get("documents", [[]])[0]
        meta_list = results.get("metadatas", [[]])[0]
        dist_list = results.get("distances", [[]])[0]

        for i, text in enumerate(doc_list):
            distance = dist_list[i] if i < len(dist_list) else 1.0
            meta = meta_list[i] if i < len(meta_list) else {}

            # In cosine space, cosine distance in [0, 2]; similarity = 1 - (distance / 2)
            similarity = max(0.0, min(1.0, 1.0 - (distance / 2.0)))

            matched_chunks.append({
                "text": text,
                "metadata": meta,
                "distance": distance,
                "relevance_score": round(similarity, 4),
                "source": meta.get("source", "Unknown"),
                "page": meta.get("page") or None,
                "document_id": meta.get("document_id", ""),
            })

        return matched_chunks

    def clear(self) -> None:
        """Clear all records from the collection (useful for test resets)."""
        all_ids = self.collection.get().get("ids", [])
        if all_ids:
            self.collection.delete(ids=all_ids)
            logger.info("Cleared all records from vector store collection")

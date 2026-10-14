"""
Enterprise RAG Knowledge Assistant — Chunking Service

Splits extracted document text into manageable chunks using LangChain text splitters.
Preserves document ID, filename, page numbers, and chunk sequence metadata.

Phase 2 of the implementation plan.
"""

import logging
from dataclasses import dataclass, field
from typing import Any

from langchain_text_splitters import RecursiveCharacterTextSplitter

from backend.app.core.config import settings
from backend.app.services.document_processor import PageContent, ProcessedDocument

logger = logging.getLogger(__name__)


@dataclass
class DocumentChunk:
    """A chunk of text derived from a processed document."""

    chunk_id: str
    text: str
    document_id: str
    filename: str
    page_number: int | None = None
    chunk_index: int = 0
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert chunk into a dictionary representation."""
        return {
            "chunk_id": self.chunk_id,
            "text": self.text,
            "document_id": self.document_id,
            "filename": self.filename,
            "page_number": self.page_number,
            "chunk_index": self.chunk_index,
            **self.metadata,
        }


class ChunkingService:
    """
    Splits processed documents into chunks while preserving source provenance.

    Splits page-by-page so page metadata is never ambiguous or mixed across boundaries.
    """

    def __init__(
        self,
        chunk_size: int | None = None,
        chunk_overlap: int | None = None,
    ) -> None:
        self.chunk_size = chunk_size if chunk_size is not None else settings.chunk_size
        self.chunk_overlap = chunk_overlap if chunk_overlap is not None else settings.chunk_overlap

        self.splitter = RecursiveCharacterTextSplitter(
            chunk_size=self.chunk_size,
            chunk_overlap=self.chunk_overlap,
            separators=["\n\n", "\n", ". ", " ", ""],
            keep_separator=True,
        )

    def chunk_document(self, document: ProcessedDocument) -> list[DocumentChunk]:
        """
        Chunk a ProcessedDocument into a list of DocumentChunks.

        Args:
            document: Processed document containing pages and metadata.

        Returns:
            List of DocumentChunk instances.
        """
        if not document.is_valid:
            logger.warning(
                "Skipping chunking for invalid document '%s': %s",
                document.filename,
                document.error or "No text content",
            )
            return []

        chunks: list[DocumentChunk] = []
        global_chunk_idx = 0

        for page in document.pages:
            page_text = page.text.strip()
            if not page_text:
                continue

            # Split this page's text
            page_chunks = self.splitter.split_text(page_text)

            for page_sub_idx, chunk_text in enumerate(page_chunks):
                chunk_text = chunk_text.strip()
                if not chunk_text:
                    continue

                page_label = f"p{page.page_number}" if page.page_number is not None else "p0"
                chunk_id = f"{document.document_id}_{page_label}_c{page_sub_idx}"

                chunk_meta = {
                    "source": document.filename,
                    "document_id": document.document_id,
                    "file_type": document.file_type,
                    "page": page.page_number if page.page_number is not None else 0,
                    "chunk_index": global_chunk_idx,
                }
                # Include any existing page metadata
                if page.metadata:
                    for k, v in page.metadata.items():
                        if k not in chunk_meta and isinstance(v, (str, int, float, bool)):
                            chunk_meta[k] = v

                chunks.append(
                    DocumentChunk(
                        chunk_id=chunk_id,
                        text=chunk_text,
                        document_id=document.document_id,
                        filename=document.filename,
                        page_number=page.page_number,
                        chunk_index=global_chunk_idx,
                        metadata=chunk_meta,
                    )
                )
                global_chunk_idx += 1

        logger.info(
            "Document '%s' chunked into %d chunks (chunk_size=%d, overlap=%d)",
            document.filename,
            len(chunks),
            self.chunk_size,
            self.chunk_overlap,
        )
        return chunks

    def chunk_text(
        self,
        text: str,
        document_id: str,
        filename: str,
        page_number: int | None = None,
        extra_metadata: dict[str, Any] | None = None,
    ) -> list[DocumentChunk]:
        """
        Chunk arbitrary raw text with associated metadata.
        """
        text = text.strip()
        if not text:
            return []

        split_texts = self.splitter.split_text(text)
        chunks: list[DocumentChunk] = []

        for idx, piece in enumerate(split_texts):
            piece = piece.strip()
            if not piece:
                continue

            page_label = f"p{page_number}" if page_number is not None else "p0"
            chunk_id = f"{document_id}_{page_label}_c{idx}"

            meta: dict[str, Any] = {
                "source": filename,
                "document_id": document_id,
                "page": page_number if page_number is not None else 0,
                "chunk_index": idx,
            }
            if extra_metadata:
                meta.update(extra_metadata)

            chunks.append(
                DocumentChunk(
                    chunk_id=chunk_id,
                    text=piece,
                    document_id=document_id,
                    filename=filename,
                    page_number=page_number,
                    chunk_index=idx,
                    metadata=meta,
                )
            )

        return chunks

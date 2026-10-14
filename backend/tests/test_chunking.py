"""
Tests for the ChunkingService (Phase 2).

Covers:
- Basic text and document chunking
- Chunk size and overlap configurability
- Page number and document metadata preservation
- Empty documents and whitespace handling
- Stable chunk ID generation
"""

import pytest

from backend.app.services.chunking_service import ChunkingService, DocumentChunk
from backend.app.services.document_processor import PageContent, ProcessedDocument


@pytest.fixture
def chunking_service():
    """Default chunking service with standard settings."""
    return ChunkingService(chunk_size=300, chunk_overlap=50)


class TestChunkingService:
    """Tests for document chunking behavior."""

    def test_chunk_document_basic(self, chunking_service):
        """Splits multi-page document into chunks while preserving metadata."""
        doc = ProcessedDocument(
            document_id="doc-123",
            filename="handbook.pdf",
            file_type="pdf",
            pages=[
                PageContent(
                    text="Page one content about company history and foundation in 2010. " * 10,
                    page_number=1,
                ),
                PageContent(
                    text="Page two content about benefits, healthcare, and vacation policies. " * 10,
                    page_number=2,
                ),
            ],
            total_characters=1300,
        )

        chunks = chunking_service.chunk_document(doc)

        assert len(chunks) > 0
        assert all(isinstance(c, DocumentChunk) for c in chunks)

        # Check page 1 chunks
        page_1_chunks = [c for c in chunks if c.page_number == 1]
        assert len(page_1_chunks) > 0
        for c in page_1_chunks:
            assert c.document_id == "doc-123"
            assert c.filename == "handbook.pdf"
            assert c.metadata["page"] == 1
            assert "p1" in c.chunk_id

        # Check page 2 chunks
        page_2_chunks = [c for c in chunks if c.page_number == 2]
        assert len(page_2_chunks) > 0
        for c in page_2_chunks:
            assert c.metadata["page"] == 2
            assert "p2" in c.chunk_id

    def test_chunk_size_configuration(self):
        """Small chunk size produces more chunks than large chunk size."""
        sample_text = (
            "The annual leave policy allows twenty working days of paid leave per year. "
            "Employees accrue leave on a monthly schedule. Unused leave can be rolled over up to five days. "
        ) * 15

        doc = ProcessedDocument(
            document_id="policy-001",
            filename="leave.txt",
            file_type="txt",
            pages=[PageContent(text=sample_text, page_number=None)],
            total_characters=len(sample_text),
        )

        small_chunker = ChunkingService(chunk_size=150, chunk_overlap=20)
        large_chunker = ChunkingService(chunk_size=600, chunk_overlap=50)

        small_chunks = small_chunker.chunk_document(doc)
        large_chunks = large_chunker.chunk_document(doc)

        assert len(small_chunks) > len(large_chunks)
        # Verify chunk sizes do not exceed configured limit unreasonably
        for c in small_chunks:
            # RecursiveCharacterTextSplitter stays within bounds (except when a single token is longer)
            assert len(c.text) <= 250

    def test_empty_document_handling(self, chunking_service):
        """Empty documents or documents marked invalid produce empty chunk lists."""
        invalid_doc = ProcessedDocument(
            document_id="empty-1",
            filename="empty.txt",
            file_type="txt",
            pages=[],
            total_characters=0,
            error="Empty document",
        )
        assert chunking_service.chunk_document(invalid_doc) == []

        empty_page_doc = ProcessedDocument(
            document_id="empty-2",
            filename="spaces.txt",
            file_type="txt",
            pages=[PageContent(text="   \n\n  ", page_number=1)],
            total_characters=6,
        )
        assert chunking_service.chunk_document(empty_page_doc) == []

    def test_chunk_id_stability(self, chunking_service):
        """Re-chunking identical document produces consistent chunk IDs."""
        doc = ProcessedDocument(
            document_id="doc-stable",
            filename="guide.txt",
            file_type="txt",
            pages=[PageContent(text="Section A. Section B. Section C.", page_number=1)],
            total_characters=30,
        )

        chunks1 = chunking_service.chunk_document(doc)
        chunks2 = chunking_service.chunk_document(doc)

        assert [c.chunk_id for c in chunks1] == [c.chunk_id for c in chunks2]

    def test_chunk_to_dict(self, chunking_service):
        """DocumentChunk.to_dict contains all required fields."""
        doc = ProcessedDocument(
            document_id="doc-dict",
            filename="test.txt",
            file_type="txt",
            pages=[PageContent(text="Some text for dictionary test.", page_number=1)],
            total_characters=30,
        )

        chunks = chunking_service.chunk_document(doc)
        assert len(chunks) == 1
        d = chunks[0].to_dict()

        assert d["chunk_id"] == chunks[0].chunk_id
        assert d["text"] == chunks[0].text
        assert d["document_id"] == "doc-dict"
        assert d["filename"] == "test.txt"
        assert d["page_number"] == 1
        assert "chunk_index" in d

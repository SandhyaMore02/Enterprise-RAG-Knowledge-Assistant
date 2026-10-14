"""
Tests for the document processor service.

Covers:
- TXT extraction
- PDF extraction (if sample PDF exists)
- DOCX extraction (if sample DOCX exists)
- Error handling: empty files, unsupported types, missing files
- Metadata preservation
- Document ID generation consistency
"""

import tempfile
from pathlib import Path

import pytest

from backend.app.services.document_processor import (
    DocumentProcessor,
    DocumentProcessingError,
    SUPPORTED_EXTENSIONS,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

SAMPLE_DOCS_DIR = Path(__file__).resolve().parent.parent.parent / "data" / "sample_docs"


@pytest.fixture
def processor():
    """Fresh DocumentProcessor instance."""
    return DocumentProcessor()


@pytest.fixture
def sample_hr_txt():
    """Path to the sample HR policy TXT file."""
    path = SAMPLE_DOCS_DIR / "sample_hr_policy.txt"
    if not path.exists():
        pytest.skip(f"Sample file not found: {path}")
    return path


@pytest.fixture
def sample_it_txt():
    """Path to the sample IT guidelines TXT file."""
    path = SAMPLE_DOCS_DIR / "sample_it_guidelines.txt"
    if not path.exists():
        pytest.skip(f"Sample file not found: {path}")
    return path


@pytest.fixture
def sample_pdf():
    """Path to the sample HR policy PDF (generated separately)."""
    path = SAMPLE_DOCS_DIR / "sample_hr_policy.pdf"
    if not path.exists():
        pytest.skip("Sample PDF not generated yet. Run: python data/sample_docs/generate_samples.py")
    return path


@pytest.fixture
def sample_docx():
    """Path to the sample IT guidelines DOCX (generated separately)."""
    path = SAMPLE_DOCS_DIR / "sample_it_guidelines.docx"
    if not path.exists():
        pytest.skip("Sample DOCX not generated yet. Run: python data/sample_docs/generate_samples.py")
    return path


# ---------------------------------------------------------------------------
# TXT Extraction Tests
# ---------------------------------------------------------------------------

class TestTxtExtraction:
    """Tests for plain text file processing."""

    def test_extract_txt_success(self, processor, sample_hr_txt):
        """TXT extraction returns valid content with metadata."""
        result = processor.process_file(sample_hr_txt)

        assert result.is_valid
        assert result.filename == "sample_hr_policy.txt"
        assert result.file_type == "txt"
        assert result.total_characters > 0
        assert len(result.pages) == 1  # TXT has a single "page"
        assert result.pages[0].page_number is None  # TXT doesn't have page numbers

    def test_txt_contains_expected_content(self, processor, sample_hr_txt):
        """Extracted text includes known content from the sample document."""
        result = processor.process_file(sample_hr_txt)
        full_text = result.full_text

        assert "ANNUAL LEAVE POLICY" in full_text
        assert "20 days" in full_text
        assert "REMOTE WORK POLICY" in full_text
        assert "PERFORMANCE REVIEW" in full_text

    def test_txt_metadata_preserved(self, processor, sample_hr_txt):
        """Source metadata is attached to the extracted page."""
        result = processor.process_file(sample_hr_txt)
        page = result.pages[0]

        assert page.metadata["source"] == "sample_hr_policy.txt"
        assert page.metadata["format"] == "txt"
        assert "encoding" in page.metadata

    def test_second_txt_file(self, processor, sample_it_txt):
        """A second TXT file also processes correctly."""
        result = processor.process_file(sample_it_txt)

        assert result.is_valid
        assert "PASSWORD POLICY" in result.full_text
        assert "DATA CLASSIFICATION" in result.full_text


# ---------------------------------------------------------------------------
# PDF Extraction Tests
# ---------------------------------------------------------------------------

class TestPdfExtraction:
    """Tests for PDF file processing."""

    def test_extract_pdf_success(self, processor, sample_pdf):
        """PDF extraction returns content with page numbers."""
        result = processor.process_file(sample_pdf)

        assert result.is_valid
        assert result.file_type == "pdf"
        assert len(result.pages) > 0
        assert all(p.page_number is not None for p in result.pages)

    def test_pdf_page_metadata(self, processor, sample_pdf):
        """Each PDF page carries source and page metadata."""
        result = processor.process_file(sample_pdf)

        for page in result.pages:
            assert "source" in page.metadata
            assert "page" in page.metadata
            assert "total_pages" in page.metadata
            assert page.metadata["page"] >= 1


# ---------------------------------------------------------------------------
# DOCX Extraction Tests
# ---------------------------------------------------------------------------

class TestDocxExtraction:
    """Tests for DOCX file processing."""

    def test_extract_docx_success(self, processor, sample_docx):
        """DOCX extraction returns valid content."""
        result = processor.process_file(sample_docx)

        assert result.is_valid
        assert result.file_type == "docx"
        assert result.total_characters > 0

    def test_docx_no_page_numbers(self, processor, sample_docx):
        """DOCX pages don't have page numbers (format limitation)."""
        result = processor.process_file(sample_docx)

        for page in result.pages:
            assert page.page_number is None


# ---------------------------------------------------------------------------
# Upload Processing Tests
# ---------------------------------------------------------------------------

class TestUploadProcessing:
    """Tests for process_upload (bytes-based ingestion)."""

    def test_upload_from_bytes(self, processor, sample_hr_txt):
        """process_upload handles raw bytes correctly."""
        content = sample_hr_txt.read_bytes()
        result = processor.process_upload("uploaded_policy.txt", content)

        assert result.is_valid
        assert result.filename == "uploaded_policy.txt"
        assert result.total_characters > 0

    def test_upload_preserves_original_filename(self, processor, sample_hr_txt):
        """The original upload filename overrides the temp file name."""
        content = sample_hr_txt.read_bytes()
        result = processor.process_upload("my_custom_name.txt", content)

        assert result.filename == "my_custom_name.txt"


# ---------------------------------------------------------------------------
# Error Handling Tests
# ---------------------------------------------------------------------------

class TestErrorHandling:
    """Tests for validation and error cases."""

    def test_reject_unsupported_extension(self, processor):
        """Unsupported file types produce a clear error."""
        with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as f:
            f.write(b"fake content")
            tmp = Path(f.name)
        try:
            with pytest.raises(DocumentProcessingError, match="Unsupported file type"):
                processor.process_file(tmp)
        finally:
            tmp.unlink()

    def test_reject_empty_file(self, processor):
        """Empty files produce a clear error."""
        with tempfile.NamedTemporaryFile(suffix=".txt", delete=False) as f:
            tmp = Path(f.name)
        try:
            with pytest.raises(DocumentProcessingError, match="empty"):
                processor.process_file(tmp)
        finally:
            tmp.unlink()

    def test_reject_missing_file(self, processor):
        """Non-existent files produce a clear error."""
        with pytest.raises(DocumentProcessingError, match="File not found"):
            processor.process_file("/does/not/exist/report.pdf")

    def test_reject_empty_bytes_upload(self, processor):
        """Uploading empty bytes raises an error."""
        with pytest.raises(DocumentProcessingError, match="empty"):
            processor.process_upload("empty.txt", b"")

    def test_reject_unsupported_upload_extension(self, processor):
        """Uploading an unsupported file type raises an error."""
        with pytest.raises(DocumentProcessingError, match="Unsupported file type"):
            processor.process_upload("report.xlsx", b"some data")


# ---------------------------------------------------------------------------
# Document ID Tests
# ---------------------------------------------------------------------------

class TestDocumentId:
    """Tests for stable document ID generation."""

    def test_same_file_same_id(self, processor, sample_hr_txt):
        """Processing the same file twice produces the same document_id."""
        result1 = processor.process_file(sample_hr_txt)
        result2 = processor.process_file(sample_hr_txt)

        assert result1.document_id == result2.document_id

    def test_different_files_different_ids(self, processor, sample_hr_txt, sample_it_txt):
        """Different files produce different document_ids."""
        result1 = processor.process_file(sample_hr_txt)
        result2 = processor.process_file(sample_it_txt)

        assert result1.document_id != result2.document_id

    def test_id_contains_filename(self, processor, sample_hr_txt):
        """The document_id includes the original filename for traceability."""
        result = processor.process_file(sample_hr_txt)
        assert "sample_hr_policy.txt" in result.document_id


# ---------------------------------------------------------------------------
# Supported Extensions Tests
# ---------------------------------------------------------------------------

class TestSupportedExtensions:
    """Tests for the SUPPORTED_EXTENSIONS constant."""

    def test_pdf_supported(self):
        assert ".pdf" in SUPPORTED_EXTENSIONS

    def test_docx_supported(self):
        assert ".docx" in SUPPORTED_EXTENSIONS

    def test_txt_supported(self):
        assert ".txt" in SUPPORTED_EXTENSIONS

    def test_xlsx_not_supported(self):
        assert ".xlsx" not in SUPPORTED_EXTENSIONS

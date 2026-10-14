"""
Enterprise RAG Knowledge Assistant — Document Processor

Extracts text from PDF, DOCX, and TXT files.
Preserves metadata: filename, file type, page numbers (where available),
and a generated document identifier.

This module is the entry point for Phase 1 of the implementation plan.
"""

import hashlib
import logging
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import BinaryIO

logger = logging.getLogger(__name__)

# Supported file extensions (lowercase, with dot)
SUPPORTED_EXTENSIONS = {".pdf", ".docx", ".txt"}

# Maximum file size guard (applied before processing, not just at upload)
MAX_FILE_BYTES = 50 * 1024 * 1024  # 50 MB hard ceiling


@dataclass
class PageContent:
    """A single page or section of extracted text."""

    text: str
    page_number: int | None = None  # 1-indexed page number, None for formats without pages
    metadata: dict = field(default_factory=dict)


@dataclass
class ProcessedDocument:
    """Result of processing a single file."""

    document_id: str
    filename: str
    file_type: str  # e.g. "pdf", "docx", "txt"
    pages: list[PageContent] = field(default_factory=list)
    total_characters: int = 0
    error: str | None = None

    @property
    def full_text(self) -> str:
        """Concatenate all page texts."""
        return "\n\n".join(page.text for page in self.pages if page.text)

    @property
    def is_valid(self) -> bool:
        """Whether extraction succeeded with usable content."""
        return self.error is None and self.total_characters > 0


class DocumentProcessingError(Exception):
    """Raised when document processing fails in an expected way."""

    pass


class DocumentProcessor:
    """
    Extracts text and metadata from supported document formats.

    Usage:
        processor = DocumentProcessor()
        result = processor.process_file(path_to_file)
        # or
        result = processor.process_upload(filename, file_bytes)
    """

    def process_file(self, file_path: str | Path) -> ProcessedDocument:
        """
        Process a document from a file path.

        Args:
            file_path: Path to the document file.

        Returns:
            ProcessedDocument with extracted text and metadata.

        Raises:
            DocumentProcessingError: If the file cannot be processed.
        """
        path = Path(file_path)

        # --- Validate the file ---
        self._validate_file_path(path)

        extension = path.suffix.lower()
        document_id = self._generate_document_id(path.name, path.read_bytes())

        try:
            if extension == ".pdf":
                pages = self._extract_pdf(path)
            elif extension == ".docx":
                pages = self._extract_docx(path)
            elif extension == ".txt":
                pages = self._extract_txt(path)
            else:
                raise DocumentProcessingError(
                    f"Unsupported file type: '{extension}'. "
                    f"Supported types: {', '.join(sorted(SUPPORTED_EXTENSIONS))}"
                )
        except DocumentProcessingError:
            raise
        except Exception as e:
            logger.error("Failed to process '%s': %s", path.name, e, exc_info=True)
            raise DocumentProcessingError(
                f"Failed to extract text from '{path.name}': {e}"
            ) from e

        total_chars = sum(len(p.text) for p in pages)

        if total_chars == 0:
            raise DocumentProcessingError(
                f"No text could be extracted from '{path.name}'. "
                "The file may be empty, image-only, or corrupted."
            )

        result = ProcessedDocument(
            document_id=document_id,
            filename=path.name,
            file_type=extension.lstrip("."),
            pages=pages,
            total_characters=total_chars,
        )

        logger.info(
            "Processed '%s': %d pages, %d characters",
            path.name,
            len(pages),
            total_chars,
        )
        return result

    def process_upload(
        self, filename: str, file_content: bytes | BinaryIO
    ) -> ProcessedDocument:
        """
        Process an uploaded file from bytes or a file-like object.

        Args:
            filename: Original filename from the upload.
            file_content: Raw file bytes or a readable binary stream.

        Returns:
            ProcessedDocument with extracted text and metadata.
        """
        if hasattr(file_content, "read"):
            file_content = file_content.read()

        if not isinstance(file_content, bytes):
            raise DocumentProcessingError("File content must be bytes or a readable stream.")

        # Validate extension
        extension = Path(filename).suffix.lower()
        if extension not in SUPPORTED_EXTENSIONS:
            raise DocumentProcessingError(
                f"Unsupported file type: '{extension}'. "
                f"Supported types: {', '.join(sorted(SUPPORTED_EXTENSIONS))}"
            )

        # Validate size
        if len(file_content) > MAX_FILE_BYTES:
            raise DocumentProcessingError(
                f"File '{filename}' is too large ({len(file_content) / 1024 / 1024:.1f} MB). "
                f"Maximum allowed: {MAX_FILE_BYTES / 1024 / 1024:.0f} MB."
            )

        if len(file_content) == 0:
            raise DocumentProcessingError(f"File '{filename}' is empty.")

        # Write to a temporary location and process
        import tempfile

        with tempfile.NamedTemporaryFile(
            suffix=extension, delete=False
        ) as tmp:
            tmp.write(file_content)
            tmp_path = Path(tmp.name)

        try:
            result = self.process_file(tmp_path)
            # Override filename with the original upload name
            result.filename = filename
            return result
        finally:
            try:
                tmp_path.unlink()
            except OSError:
                pass

    # -------------------------------------------------------------------------
    # Format-specific extractors
    # -------------------------------------------------------------------------

    def _extract_pdf(self, path: Path) -> list[PageContent]:
        """Extract text from a PDF, preserving page numbers."""
        try:
            from pypdf import PdfReader
        except ImportError as e:
            raise DocumentProcessingError(
                "pypdf is required for PDF processing. Install it with: pip install pypdf"
            ) from e

        reader = PdfReader(str(path))

        if len(reader.pages) == 0:
            raise DocumentProcessingError(f"PDF '{path.name}' has no pages.")

        pages = []
        for i, page in enumerate(reader.pages, start=1):
            text = page.extract_text() or ""
            text = text.strip()

            pages.append(
                PageContent(
                    text=text,
                    page_number=i,
                    metadata={
                        "source": path.name,
                        "page": i,
                        "total_pages": len(reader.pages),
                    },
                )
            )

        return pages

    def _extract_docx(self, path: Path) -> list[PageContent]:
        """
        Extract text from a DOCX file.

        DOCX does not have reliable page-number information in the raw XML,
        so we return the full text as a single logical page.
        """
        try:
            import docx2txt
        except ImportError as e:
            raise DocumentProcessingError(
                "docx2txt is required for DOCX processing. Install it with: pip install docx2txt"
            ) from e

        text = docx2txt.process(str(path))

        if text is None:
            text = ""

        text = text.strip()

        return [
            PageContent(
                text=text,
                page_number=None,  # DOCX doesn't expose page numbers reliably
                metadata={"source": path.name, "format": "docx"},
            )
        ]

    def _extract_txt(self, path: Path) -> list[PageContent]:
        """Extract text from a plain text file."""
        encodings = ["utf-8", "utf-8-sig", "latin-1", "cp1252"]

        for encoding in encodings:
            try:
                text = path.read_text(encoding=encoding)
                text = text.strip()
                return [
                    PageContent(
                        text=text,
                        page_number=None,
                        metadata={"source": path.name, "format": "txt", "encoding": encoding},
                    )
                ]
            except (UnicodeDecodeError, ValueError):
                continue

        raise DocumentProcessingError(
            f"Could not decode '{path.name}' with any supported encoding: {encodings}"
        )

    # -------------------------------------------------------------------------
    # Helpers
    # -------------------------------------------------------------------------

    def _validate_file_path(self, path: Path) -> None:
        """Validate that the file exists, is readable, and is a supported type."""
        if not path.exists():
            raise DocumentProcessingError(f"File not found: '{path}'")

        if not path.is_file():
            raise DocumentProcessingError(f"Path is not a file: '{path}'")

        extension = path.suffix.lower()
        if extension not in SUPPORTED_EXTENSIONS:
            raise DocumentProcessingError(
                f"Unsupported file type: '{extension}'. "
                f"Supported types: {', '.join(sorted(SUPPORTED_EXTENSIONS))}"
            )

        file_size = path.stat().st_size
        if file_size == 0:
            raise DocumentProcessingError(f"File '{path.name}' is empty (0 bytes).")

        if file_size > MAX_FILE_BYTES:
            raise DocumentProcessingError(
                f"File '{path.name}' is too large ({file_size / 1024 / 1024:.1f} MB). "
                f"Maximum allowed: {MAX_FILE_BYTES / 1024 / 1024:.0f} MB."
            )

    @staticmethod
    def _generate_document_id(filename: str, content: bytes) -> str:
        """
        Generate a stable document ID from filename + content hash.

        This ensures the same file uploaded twice gets the same ID,
        enabling duplicate detection.
        """
        content_hash = hashlib.sha256(content).hexdigest()[:12]
        return f"{filename}-{content_hash}"

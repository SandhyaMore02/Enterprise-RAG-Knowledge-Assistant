"""
Enterprise RAG Knowledge Assistant — Request/Response Schemas

Pydantic models for API input validation and output serialization.
"""

from typing import Any
from pydantic import BaseModel, Field



class HealthResponse(BaseModel):
    """Health check response."""

    status: str = "ok"
    version: str = "0.1.0"


class DocumentUploadResponse(BaseModel):
    """Response after successfully uploading and processing a document."""

    document_id: str
    filename: str
    status: str = "indexed"
    chunks_created: int = 0
    total_characters: int = 0


class SourceReference(BaseModel):
    """A citation pointing to a specific source passage."""

    document_id: str
    filename: str
    page: int | None = None


class ChatRequest(BaseModel):
    """Input for the chat/question endpoint."""

    question: str = Field(..., min_length=1, max_length=2000, description="The user's question")
    conversation_id: str | None = Field(default=None, description="Optional conversation ID for follow-ups")


class ChatResponse(BaseModel):
    """Response containing the answer and supporting sources."""

    answer: str
    sources: list[SourceReference] = []
    conversation_id: str | None = None


class DocumentInfo(BaseModel):
    """Summary of an indexed document."""

    document_id: str
    filename: str
    file_type: str
    total_characters: int
    chunk_count: int = 0


class DocumentListResponse(BaseModel):
    """Response listing all indexed documents."""

    documents: list[DocumentInfo] = []
    total: int = 0


class ErrorResponse(BaseModel):
    """Standard error response."""

    detail: str
    error_code: str | None = None


class CompareRequest(BaseModel):
    """Request payload to compare two documents."""

    document_id_a: str = Field(..., description="First document ID")
    document_id_b: str = Field(..., description="Second document ID")


class CompareResponse(BaseModel):
    """Structured response comparing two documents."""

    document_a: dict[str, Any]
    document_b: dict[str, Any]
    summary: str


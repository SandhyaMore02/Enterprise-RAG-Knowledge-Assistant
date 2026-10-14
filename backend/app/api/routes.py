"""
Enterprise RAG Knowledge Assistant — API Routes

Route definitions for document management and RAG question answering.
Phase 6 of the implementation plan.
"""

import logging
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, File, HTTPException, UploadFile, status

from backend.app.core.config import settings
from backend.app.schemas.requests import (
    ChatRequest,
    ChatResponse,
    CompareRequest,
    CompareResponse,
    DocumentInfo,
    DocumentListResponse,
    DocumentUploadResponse,
    SourceReference,
)
from backend.app.services.chunking_service import ChunkingService
from backend.app.services.comparison_service import ComparisonService
from backend.app.services.conversation_service import ConversationService
from backend.app.services.document_processor import (
    DocumentProcessingError,
    DocumentProcessor,
    SUPPORTED_EXTENSIONS,
)
from backend.app.services.rag_service import RAGService
from backend.app.services.vector_store import VectorStoreService

logger = logging.getLogger(__name__)

router = APIRouter()

# Service singletons for the API layer
doc_processor = DocumentProcessor()
chunker = ChunkingService()
vector_store = VectorStoreService()
rag_service = RAGService(retrieval_service=None)
conversation_service = ConversationService()
comparison_service = ComparisonService(vector_store=vector_store)



@router.post(
    "/documents/upload",
    response_model=DocumentUploadResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload and index a document",
)
async def upload_document(
    file: Annotated[UploadFile, File(description="PDF, DOCX, or TXT file")],
):
    """
    Upload and index a document file (PDF, DOCX, TXT):
    1. Validates extension and file size.
    2. Extracts text and page metadata.
    3. Splits text into manageable chunks.
    4. Computes embeddings and stores in ChromaDB.
    """
    if not file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded file must have a filename.",
        )

    ext = Path(file.filename).suffix.lower()
    if ext not in SUPPORTED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported file type '{ext}'. Allowed: {', '.join(sorted(SUPPORTED_EXTENSIONS))}",
        )

    # Read bytes with file size guard
    contents = await file.read()
    if len(contents) > settings.max_upload_bytes:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File exceeds maximum allowed size of {settings.max_upload_mb} MB.",
        )

    if len(contents) == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot process an empty file.",
        )

    try:
        # Step 1: Process document
        processed = doc_processor.process_upload(file.filename, contents)

        # Step 2: Split into chunks
        chunks = chunker.chunk_document(processed)

        # Step 3: Index in ChromaDB
        chunks_count = vector_store.add_chunks(chunks, overwrite=True)

        return DocumentUploadResponse(
            document_id=processed.document_id,
            filename=processed.filename,
            status="indexed",
            chunks_created=chunks_count,
            total_characters=processed.total_characters,
        )
    except DocumentProcessingError as e:
        logger.warning("Upload processing failed: %s", e)
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(e),
        )
    except Exception as e:
        logger.error("Unexpected error during upload: %s", e, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while indexing the document.",
        )


@router.get(
    "/documents",
    response_model=DocumentListResponse,
    summary="List all indexed documents",
)
async def list_documents():
    """Returns a list of all currently indexed documents in the vector store."""
    docs_data = vector_store.list_documents()
    docs = [
        DocumentInfo(
            document_id=d["document_id"],
            filename=d["filename"],
            file_type=d["file_type"],
            total_characters=d["total_characters"],
            chunk_count=d["chunk_count"],
        )
        for d in docs_data
    ]
    return DocumentListResponse(documents=docs, total=len(docs))


@router.delete(
    "/documents/{document_id}",
    summary="Delete an indexed document",
)
async def delete_document(document_id: str):
    """Removes a document and all its chunks from the vector database."""
    deleted_count = vector_store.delete_document(document_id)
    if deleted_count == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document '{document_id}' not found.",
        )
    return {"message": f"Successfully deleted document '{document_id}' ({deleted_count} chunks removed)."}


@router.post(
    "/chat",
    response_model=ChatResponse,
    summary="Ask a question grounded in indexed documents",
)
async def chat(request: ChatRequest):
    """
    Ask a question over the indexed document knowledge base.
    Contextualizes follow-up questions using session history.
    """
    session_id = request.conversation_id or conversation_service.create_session()

    # Step 1: Contextualize question using session history
    contextualized_q = conversation_service.contextualize_query(
        question=request.question,
        conversation_id=session_id,
    )

    # Step 2: Answer question with RAG pipeline
    result = rag_service.answer_question(
        question=contextualized_q,
        conversation_id=session_id,
    )

    answer_text = result.get("answer", "")

    # Step 3: Record turn in conversation memory
    conversation_service.add_turn(
        conversation_id=session_id,
        user_message=request.question,
        assistant_message=answer_text,
    )

    sources = [
        SourceReference(
            document_id=s.get("document_id", ""),
            filename=s.get("filename", ""),
            page=s.get("page"),
        )
        for s in result.get("sources", [])
    ]

    return ChatResponse(
        answer=answer_text,
        sources=sources,
        conversation_id=session_id,
    )


@router.post(
    "/documents/compare",
    response_model=CompareResponse,
    summary="Compare two indexed documents or policy versions",
)
async def compare_documents(request: CompareRequest):
    """
    Compares two indexed documents to summarize differences, additions, and updates.
    """
    res = comparison_service.compare_documents(
        document_id_a=request.document_id_a,
        document_id_b=request.document_id_b,
    )

    if "error" in res:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=res["error"],
        )

    return CompareResponse(
        document_a=res["document_a"],
        document_b=res["document_b"],
        summary=res["summary"],
    )


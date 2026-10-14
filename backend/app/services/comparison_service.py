"""
Enterprise RAG Knowledge Assistant — Document Comparison Service

Compares two indexed documents or policy versions and generates a structured
summary of differences, additions, and removals with strict source grounding.

Phase 9 of the implementation plan.
"""

import logging
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage

from backend.app.services.vector_store import VectorStoreService

logger = logging.getLogger(__name__)

COMPARISON_PROMPT = """You are a Document Comparison Specialist. Compare the two provided document texts and produce a structured breakdown of differences.

Strict Rules:
1. Compare ONLY the provided texts. Do not assume or extrapolate.
2. Structure your findings into clear bullet points:
   - **Topic/Clause**: What is being discussed
   - **Document A ({doc_a_name})**: What Document A states
   - **Document B ({doc_b_name})**: What Document B states
   - **Change Type**: Modified, Added, or Removed
3. If an item exists in one document but is absent from the other, explicitly note it as "Not specified in [Doc Name]".
4. Do not invent differences where the texts agree.

---
Document A: {doc_a_name}
{doc_a_text}

---
Document B: {doc_b_name}
{doc_b_text}

---
Structured Difference Summary:"""


class ComparisonService:
    """
    Compares two indexed documents and returns structured comparative analysis.
    """

    def __init__(self, vector_store: VectorStoreService | None = None, llm=None) -> None:
        self.vector_store = vector_store or VectorStoreService()
        self._llm = llm

    @property
    def llm(self):
        if callable(self._llm):
            return self._llm()
        return self._llm


    def compare_documents(
        self,
        document_id_a: str,
        document_id_b: str,
    ) -> dict[str, Any]:
        """
        Extract content from both documents and generate a comparative summary.
        """
        chunks_a = self.vector_store.get_chunks_for_document(document_id_a)
        chunks_b = self.vector_store.get_chunks_for_document(document_id_b)

        if not chunks_a:
            return {"error": f"Document '{document_id_a}' not found in vector store."}
        if not chunks_b:
            return {"error": f"Document '{document_id_b}' not found in vector store."}

        doc_a_name = chunks_a[0]["metadata"].get("source", document_id_a)
        doc_b_name = chunks_b[0]["metadata"].get("source", document_id_b)

        # Concatenate text content
        doc_a_text = "\n\n".join(c["text"] for c in chunks_a)[:8000]
        doc_b_text = "\n\n".join(c["text"] for c in chunks_b)[:8000]

        if self.llm is None:
            # Offline structured comparison fallback
            return {
                "document_a": {"id": document_id_a, "name": doc_a_name, "chunk_count": len(chunks_a)},
                "document_b": {"id": document_id_b, "name": doc_b_name, "chunk_count": len(chunks_b)},
                "summary": (
                    f"Comparison between **{doc_a_name}** ({len(chunks_a)} chunks) and "
                    f"**{doc_b_name}** ({len(chunks_b)} chunks).\n\n"
                    f"- **{doc_a_name}** covers topics starting with: {chunks_a[0]['text'][:120]}...\n"
                    f"- **{doc_b_name}** covers topics starting with: {chunks_b[0]['text'][:120]}..."
                ),
            }

        prompt = COMPARISON_PROMPT.format(
            doc_a_name=doc_a_name,
            doc_a_text=doc_a_text,
            doc_b_name=doc_b_name,
            doc_b_text=doc_b_text,
        )

        try:
            response = self.llm.invoke([HumanMessage(content=prompt)])
            summary = response.content if hasattr(response, "content") else str(response)
        except Exception as e:
            logger.error("Comparison LLM generation error: %s", e)
            summary = f"Error generating comparison: {str(e)}"

        return {
            "document_a": {"id": document_id_a, "name": doc_a_name, "chunk_count": len(chunks_a)},
            "document_b": {"id": document_id_b, "name": doc_b_name, "chunk_count": len(chunks_b)},
            "summary": summary,
        }

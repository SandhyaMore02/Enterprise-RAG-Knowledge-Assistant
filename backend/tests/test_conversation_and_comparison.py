"""
Tests for Conversation Context (Phase 8) and Document Comparison (Phase 9).
"""

from pathlib import Path
import pytest
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.services.conversation_service import ConversationService
from backend.app.services.comparison_service import ComparisonService
from backend.app.services.document_processor import DocumentProcessor
from backend.app.services.chunking_service import ChunkingService
from backend.app.services.vector_store import VectorStoreService

SAMPLE_DOCS_DIR = Path(__file__).resolve().parent.parent.parent / "data" / "sample_docs"


@pytest.fixture
def client():
    return TestClient(app)


class TestConversationService:
    """Unit tests for conversation context and sliding window memory."""

    def test_session_lifecycle(self):
        service = ConversationService()
        session_id = service.create_session()
        assert session_id is not None
        assert service.get_history(session_id) == []

        service.add_turn(session_id, "Hello", "Hi there!")
        history = service.get_history(session_id)
        assert len(history) == 1
        assert history[0]["user"] == "Hello"
        assert history[0]["assistant"] == "Hi there!"

    def test_sliding_window_limit(self):
        service = ConversationService()
        session_id = service.create_session()
        for i in range(10):
            service.add_turn(session_id, f"Question {i}", f"Answer {i}")

        history = service.get_history(session_id)
        # Should be bounded to MAX_HISTORY_TURNS (6)
        assert len(history) == 6
        assert history[-1]["user"] == "Question 9"

    def test_contextualize_followup_query(self):
        service = ConversationService()
        session_id = service.create_session()
        service.add_turn(
            session_id,
            "What is the annual leave policy for full-time employees?",
            "Full-time employees receive 20 days.",
        )

        # Follow-up with pronoun / ellipsis
        rephrased = service.contextualize_query("What about interns?", session_id)
        assert "annual leave policy" in rephrased.lower() or "interns" in rephrased.lower()


class TestDocumentComparison:
    """Integration test for document comparison (Phase 9)."""

    def test_compare_endpoint(self, client):
        # Index HR policy
        hr_path = SAMPLE_DOCS_DIR / "sample_hr_policy.txt"
        with open(hr_path, "rb") as f:
            res_a = client.post(
                "/documents/upload",
                files={"file": ("sample_hr_policy.txt", f, "text/plain")},
            )
        doc_a_id = res_a.json()["document_id"]

        # Index IT guidelines
        it_path = SAMPLE_DOCS_DIR / "sample_it_guidelines.txt"
        with open(it_path, "rb") as f:
            res_b = client.post(
                "/documents/upload",
                files={"file": ("sample_it_guidelines.txt", f, "text/plain")},
            )
        doc_b_id = res_b.json()["document_id"]

        compare_res = client.post(
            "/documents/compare",
            json={"document_id_a": doc_a_id, "document_id_b": doc_b_id},
        )

        assert compare_res.status_code == 200
        data = compare_res.json()
        assert "document_a" in data
        assert "document_b" in data
        assert "summary" in data
        assert len(data["summary"]) > 0

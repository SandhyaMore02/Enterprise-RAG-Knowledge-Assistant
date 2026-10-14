"""
Integration tests for FastAPI endpoints (Phase 6).

Covers:
- GET /health
- POST /documents/upload (valid, invalid extension, empty)
- GET /documents
- DELETE /documents/{document_id}
- POST /chat
"""

import io
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.api.routes import vector_store

SAMPLE_DOCS_DIR = Path(__file__).resolve().parent.parent.parent / "data" / "sample_docs"


@pytest.fixture(autouse=True)
def clean_vector_store():
    """Ensure clean vector store state for tests."""
    vector_store.clear()
    yield
    vector_store.clear()


@pytest.fixture
def client():
    """FastAPI test client."""
    return TestClient(app)


class TestApiEndpoints:
    """Integration test suite for the REST API."""

    def test_health_check(self, client):
        """GET /health returns status ok."""
        res = client.get("/health")
        assert res.status_code == 200
        assert res.json()["status"] == "ok"

    def test_upload_valid_txt(self, client):
        """POST /documents/upload successfully indexes a valid text document."""
        sample_path = SAMPLE_DOCS_DIR / "sample_hr_policy.txt"
        with open(sample_path, "rb") as f:
            res = client.post(
                "/documents/upload",
                files={"file": ("sample_hr_policy.txt", f, "text/plain")},
            )

        assert res.status_code == 201
        data = res.json()
        assert data["filename"] == "sample_hr_policy.txt"
        assert data["status"] == "indexed"
        assert data["chunks_created"] > 0
        assert data["total_characters"] > 0

    def test_upload_empty_file_rejected(self, client):
        """POST /documents/upload rejects 0-byte file."""
        res = client.post(
            "/documents/upload",
            files={"file": ("empty.txt", io.BytesIO(b""), "text/plain")},
        )
        assert res.status_code == 400
        assert "empty" in res.json()["detail"].lower()

    def test_upload_unsupported_file_rejected(self, client):
        """POST /documents/upload rejects unsupported extension."""
        res = client.post(
            "/documents/upload",
            files={"file": ("spreadsheet.xlsx", io.BytesIO(b"fake excel"), "application/vnd.ms-excel")},
        )
        assert res.status_code == 400
        assert "Unsupported" in res.json()["detail"]

    def test_list_documents(self, client):
        """GET /documents returns the list of indexed documents."""
        # First upload
        sample_path = SAMPLE_DOCS_DIR / "sample_hr_policy.txt"
        with open(sample_path, "rb") as f:
            client.post(
                "/documents/upload",
                files={"file": ("sample_hr_policy.txt", f, "text/plain")},
            )

        res = client.get("/documents")
        assert res.status_code == 200
        data = res.json()
        assert data["total"] == 1
        assert data["documents"][0]["filename"] == "sample_hr_policy.txt"

    def test_delete_document(self, client):
        """DELETE /documents/{id} removes an indexed document."""
        sample_path = SAMPLE_DOCS_DIR / "sample_hr_policy.txt"
        with open(sample_path, "rb") as f:
            upload_res = client.post(
                "/documents/upload",
                files={"file": ("sample_hr_policy.txt", f, "text/plain")},
            )
        doc_id = upload_res.json()["document_id"]

        del_res = client.delete(f"/documents/{doc_id}")
        assert del_res.status_code == 200

        # Verify it's no longer in the list
        list_res = client.get("/documents")
        assert list_res.json()["total"] == 0

    def test_delete_nonexistent_document(self, client):
        """DELETE /documents/{id} returns 404 for unknown document."""
        res = client.delete("/documents/non-existent-id")
        assert res.status_code == 404

    def test_chat_endpoint(self, client):
        """POST /chat returns a grounded answer and source citations."""
        # Ingest sample policy
        sample_path = SAMPLE_DOCS_DIR / "sample_hr_policy.txt"
        with open(sample_path, "rb") as f:
            client.post(
                "/documents/upload",
                files={"file": ("sample_hr_policy.txt", f, "text/plain")},
            )

        chat_res = client.post(
            "/chat",
            json={"question": "What is the annual leave policy for full-time employees?"},
        )
        assert chat_res.status_code == 200
        data = chat_res.json()
        assert "answer" in data
        assert len(data["answer"]) > 0
        assert "sources" in data
        assert len(data["sources"]) > 0
        assert data["sources"][0]["filename"] == "sample_hr_policy.txt"

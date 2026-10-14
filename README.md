# Enterprise RAG Knowledge Assistant

A document-based AI assistant that lets authorized users ask questions about company documents and receive answers **grounded in retrieved content**, with source references.

## Overview

Upload PDF, DOCX, and TXT documents → the system extracts text, chunks it, generates embeddings, and stores them in ChromaDB. When a user asks a question, it retrieves the most relevant passages and uses **Anthropic Claude** to generate an answer grounded in the evidence.

## Technology Stack

| Component | Technology |
|-----------|-----------|
| **Backend API** | FastAPI + Uvicorn |
| **RAG Orchestration** | LangChain |
| **Language Model** | Anthropic Claude (claude-sonnet-4) |
| **Embeddings** | OpenAI text-embedding-3-small |
| **Vector Database** | ChromaDB |
| **Frontend** | Streamlit |
| **Document Parsing** | pypdf, docx2txt |
| **Testing** | pytest + FastAPI TestClient |

## Quick Start

### Prerequisites

- Python 3.12+
- Anthropic API key
- OpenAI API key (for embeddings)

### Setup

```bash
# 1. Clone the repository
git clone <repo-url>
cd enterprise-rag-knowledge-assistant

# 2. Create and activate virtual environment
python -m venv venv
# Windows:
.\venv\Scripts\activate
# macOS/Linux:
source venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure environment
cp .env.example .env
# Edit .env with your actual API keys

# 5. Run the backend
uvicorn backend.app.main:app --reload

# 6. Run tests
pytest
```

### Generate Sample Documents

```bash
python data/sample_docs/generate_samples.py
```

## Project Structure

```
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI application entry point
│   │   ├── api/routes.py        # API endpoint handlers
│   │   ├── core/config.py       # Centralized configuration
│   │   ├── schemas/requests.py  # Request/response models
│   │   └── services/
│   │       ├── document_processor.py  # PDF/DOCX/TXT extraction
│   │       ├── embedding_service.py   # Vector embedding generation
│   │       ├── vector_store.py        # ChromaDB operations
│   │       ├── retrieval_service.py   # Similarity search
│   │       └── rag_service.py         # LLM answer generation
│   └── tests/
├── frontend/app.py              # Streamlit UI
├── data/sample_docs/            # Synthetic test documents
├── storage/                     # ChromaDB data (not committed)
├── .env.example                 # Environment variable template
└── requirements.txt             # Pinned dependencies
```

## Configuration

All settings are managed through environment variables. See [`.env.example`](.env.example) for the full list.

| Variable | Description | Default |
|----------|-------------|---------|
| `ANTHROPIC_API_KEY` | Anthropic API key for Claude | (required) |
| `OPENAI_API_KEY` | OpenAI API key for embeddings | (required) |
| `LLM_MODEL` | Claude model name | claude-sonnet-4-20250514 |
| `EMBEDDING_MODEL` | OpenAI embedding model | text-embedding-3-small |
| `TOP_K` | Number of chunks to retrieve | 4 |
| `CHUNK_SIZE` | Characters per chunk | 1000 |
| `CHUNK_OVERLAP` | Overlap between chunks | 200 |
| `MAX_UPLOAD_MB` | Maximum file upload size | 10 |

## API Endpoints

| Method | Endpoint | Purpose |
|--------|----------|---------|
| GET | `/health` | Health check |
| POST | `/documents/upload` | Upload and process a document |
| GET | `/documents` | List indexed documents |
| DELETE | `/documents/{document_id}` | Remove a document |
| POST | `/chat` | Ask a question with conversation memory |
| POST | `/documents/compare` | Compare two documents / policy versions |

## Development Status

- [x] Phase 0: Environment setup & Git repository
- [x] Phase 1: Document processing (PDF with page numbers, DOCX, TXT)
- [x] Phase 2: Text chunking with provenance retention
- [x] Phase 3: Vector Embeddings & persistent ChromaDB storage
- [x] Phase 4: Semantic retrieval & confidence thresholding
- [x] Phase 5: Grounded answer generation with Anthropic Claude & citations
- [x] Phase 6: FastAPI REST backend with input validation
- [x] Phase 7: Streamlit UI with multi-tab workspace
- [x] Phase 8: Multi-turn conversation context & query reformulator
- [x] Phase 9: Document comparison workflow
- [x] Phase 10: Retrieval quality evaluation suite & Recall@k metrics
- [x] Phase 11: Security & reliability controls (file limits, prompt injection mitigation)
- [x] Phase 12: Documentation & 44 automated tests
- [ ] Phase 13: Optional hosted cloud deployment


## License

Private project — not for redistribution.

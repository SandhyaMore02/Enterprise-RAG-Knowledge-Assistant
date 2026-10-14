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
| POST | `/chat` | Ask a question |

## Development Status

- [x] Phase 0: Environment setup
- [x] Phase 1: Document processing (PDF, DOCX, TXT)
- [ ] Phase 2: Text chunking
- [ ] Phase 3: Embeddings + ChromaDB
- [ ] Phase 4: Retrieval
- [ ] Phase 5: LLM answer generation
- [ ] Phase 6: FastAPI endpoints
- [ ] Phase 7: Streamlit UI
- [ ] Phase 8: Conversation context
- [ ] Phase 9: Document comparison
- [ ] Phase 10: Evaluation
- [ ] Phase 11: Security controls
- [ ] Phase 12: Documentation
- [ ] Phase 13: Deployment

## License

Private project — not for redistribution.

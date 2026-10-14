# Enterprise RAG Knowledge Assistant
## Implementation Plan and Engineering Roadmap

**Document type:** Technical implementation plan  
**Project type:** Portfolio-ready AI application  
**Primary stack:** Python, FastAPI, LangChain, LLM API, Embeddings, ChromaDB, Streamlit, Git/GitHub  
**Status:** Planned  
**Audience:** Beginner developer building toward professional software engineering practices

---

## 1. Project Overview

### 1.1 Purpose

Build a document-based AI assistant that lets authorized users ask questions about company documents and receive answers grounded in retrieved content, with source references where available.

Example question:

> What is the annual leave policy for full-time employees?

The application searches uploaded documents, retrieves relevant passages, gives those passages to an LLM, and returns a readable answer with source information.

### 1.2 Problem Statement

Organizations store information in PDFs, Word documents, and text files. Employees can spend significant time searching these documents manually. This application provides a single question-and-answer interface over a selected document collection.

### 1.3 Goals

- Upload and process PDF, DOCX, and TXT documents.
- Extract text and preserve source metadata, including page numbers where available.
- Split long text into smaller chunks.
- Generate embeddings and store them in ChromaDB.
- Retrieve relevant chunks for a user's question.
- Use an LLM to generate an answer grounded in retrieved evidence.
- Display source citations alongside answers.
- Provide a simple Streamlit user interface backed by a FastAPI service.
- Add automated tests, documentation, and a reproducible setup.
- Extend the MVP with conversation context, document comparison, evaluation, and security controls.

### 1.4 Out of Scope for the First MVP

- Training or fine-tuning a foundation model.
- Supporting every document format.
- Production-scale distributed infrastructure.
- Guaranteed factual correctness without evaluation.
- Complex multi-agent workflows.
- Enterprise identity-provider integration before the core workflow is stable.

---

## 2. Technology Stack

| Layer | Technology | Responsibility |
|---|---|---|
| Programming language | Python | Core application logic |
| API/backend | FastAPI | Document and question-answer endpoints |
| API server | Uvicorn | Runs the FastAPI application locally |
| RAG orchestration | LangChain | Connects document processing, retrieval, prompts, and model calls |
| Language model | LLM API provider, selected before implementation | Generates answers from retrieved context |
| Embeddings | Compatible embedding model/provider | Converts text and questions into vectors |
| Vector database | ChromaDB | Stores vectors, text chunks, and metadata; performs similarity search |
| User interface | Streamlit | Document upload, chat, source display, and document management |
| Document parsing | pypdf, docx2txt, Python text handling | Extracts text from PDF, DOCX, and TXT |
| Configuration | python-dotenv and environment variables | Loads local settings and secrets |
| Testing | pytest and FastAPI TestClient | Tests application behavior |
| Version control | Git and GitHub | Tracks changes and hosts the repository |

### 2.1 Stack Rules

- Keep the selected stack unless a documented technical reason requires a change.
- Choose the LLM and embedding provider before implementing provider-specific code.
- Keep the model provider behind small helper/service functions so it can be replaced later.
- Pin tested dependency versions in the project setup after the initial environment works.
- Do not commit API keys, private documents, local databases, or virtual environments.

---

## 3. Architecture

### 3.1 High-Level Flow

```text
                         USER
                          |
                          v
                  Streamlit Frontend
                          |
                   HTTP requests
                          |
                          v
                    FastAPI Backend
                     /          \
                    v            v
           Document Pipeline   Question Pipeline
                    |            |
                    v            v
          Extract text + pages  Embed question
                    |            |
                    v            v
               Chunk text     ChromaDB search
                    |            |
                    v            v
              Create vectors  Relevant chunks
                    |            |
                    v            v
                  ChromaDB ---> Context + question
                                  |
                                  v
                                 LLM
                                  |
                                  v
                       Answer + source metadata
                                  |
                                  v
                         Streamlit response
```

### 3.2 Core Design Principle

Separate the application into small modules with clear responsibilities. The frontend should not contain RAG logic, and document parsing should not be mixed into API route handlers.

### 3.3 Suggested Repository Structure

```text
enterprise-rag-knowledge-assistant/
├── backend/
│   ├── app/
│   │   ├── main.py
│   │   ├── api/
│   │   │   └── routes.py
│   │   ├── core/
│   │   │   └── config.py
│   │   ├── schemas/
│   │   │   └── requests.py
│   │   └── services/
│   │       ├── document_processor.py
│   │       ├── embedding_service.py
│   │       ├── vector_store.py
│   │       ├── retrieval_service.py
│   │       └── rag_service.py
│   └── tests/
│       ├── test_health.py
│       ├── test_document_processor.py
│       └── test_api.py
├── frontend/
│   └── app.py
├── data/
│   └── sample_docs/
│       └── README.md
├── storage/
│   └── .gitkeep
├── .env.example
├── .gitignore
├── requirements.txt
├── README.md
└── IMPLEMENTATION_PLAN.md
```

**Notes:**
- The local `storage/` directory may hold the ChromaDB data during development. Do not commit its contents.
- Keep private or real company documents out of the repository. Use synthetic sample documents.
- The structure can be introduced gradually; do not create every file before its responsibility is understood.

---

## 4. Implementation Phases

Each phase has a clear goal and a definition of done. Complete and test one phase before moving to the next.

## Phase 0 — Define Requirements and Prepare the Environment

### Tasks

1. Confirm the MVP features and the supported document formats.
2. Choose an LLM provider and a compatible embedding model.
3. Install Python and VS Code.
4. Create the project directory and Git repository.
5. Create and activate a Python virtual environment.
6. Create `.gitignore` and `.env.example`.
7. Install the initial dependencies.
8. Record the Python version and dependency versions.

### Deliverables

- Working local Python environment.
- Initial Git repository.
- Project skeleton.
- Documented model-provider choice.

### Definition of Done

- Python and the virtual environment work.
- Dependencies install successfully.
- Secrets and local data are excluded from Git.
- A simple Python script runs successfully.

---

## Phase 1 — Read and Extract Documents

### Tasks

1. Implement a document-processing service.
2. Support PDF, DOCX, and TXT.
3. Extract text without silently discarding errors.
4. Preserve metadata such as filename, file type, page number where supported, and a document identifier.
5. Validate file extensions and reject empty or unreadable documents.
6. Define clear error messages for unsupported or corrupt files.
7. Create synthetic test documents.

### Deliverables

- `document_processor.py`.
- Tests for supported formats, empty files, and invalid files.

### Definition of Done

- Text can be extracted from each supported format.
- PDF page metadata is retained when available.
- Invalid files produce understandable errors.
- No real company document is required for testing.

---

## Phase 2 — Split Documents into Chunks

### Tasks

1. Use a LangChain text splitter.
2. Start with a configurable chunk size and overlap.
3. Keep each chunk linked to its original document and page metadata.
4. Generate stable chunk identifiers where practical.
5. Test how chunk size and overlap affect retrieval.
6. Avoid splitting metadata away from its corresponding text.

### Initial Experiment

Start around 800–1,000 characters per chunk with a modest overlap, then measure results on sample questions. Treat these as initial settings, not universal best values.

### Deliverables

- Chunking function.
- Tests for chunk size, overlap, metadata preservation, and empty text.

### Definition of Done

- Long documents produce manageable chunks.
- Each chunk retains its source metadata.
- Chunking behavior is configurable and tested.

---

## Phase 3 — Generate Embeddings and Store Data in ChromaDB

### Tasks

1. Configure the selected embedding model.
2. Generate embeddings for document chunks.
3. Create a ChromaDB collection for the project.
4. Store chunk text, vectors, and metadata.
5. Use a persistent local directory during development.
6. Prevent accidental duplicate ingestion of the same document.
7. Define what happens when a document is re-uploaded or deleted.
8. Keep the embedding model consistent for document and question embeddings.

### Deliverables

- `embedding_service.py`.
- `vector_store.py`.
- Working persistent ChromaDB collection.

### Definition of Done

- Chunks and metadata are stored.
- The database can be reopened after restarting the app.
- Duplicate and re-upload behavior is defined and tested.
- Embedding-provider errors are handled clearly.

---

## Phase 4 — Implement Retrieval

### Tasks

1. Accept a text question.
2. Generate an embedding for the question.
3. Search ChromaDB for the most relevant chunks.
4. Make the number of retrieved chunks configurable (`top_k`).
5. Return the text, source filename, page number where available, and relevance metadata.
6. Inspect retrieval results before involving the LLM.
7. Test relevant questions, paraphrases, ambiguous questions, and questions with no answer in the documents.

### Deliverables

- `retrieval_service.py`.
- Retrieval tests and sample outputs.

### Definition of Done

- Questions return relevant document chunks.
- Source metadata remains attached.
- Retrieval can be tested independently of answer generation.
- The application can detect when retrieval evidence is weak enough to require a cautious response.

---

## Phase 5 — Generate Grounded Answers with an LLM

### Tasks

1. Configure the selected LLM provider securely.
2. Build a prompt that includes the user question and retrieved context.
3. Instruct the model to answer only from the supplied evidence.
4. Tell the model to say when the answer is not available in the context.
5. Treat retrieved documents as untrusted data, not as instructions to the model.
6. Return the answer and the source metadata used to support it.
7. Handle rate limits, timeouts, and provider errors.
8. Avoid sending unnecessary document content to the model.

### Deliverables

- `rag_service.py`.
- Grounded answer generation.
- Tests for supported and unsupported questions.

### Definition of Done

- The model receives the question and retrieved context.
- Responses include source references where evidence supports them.
- Unsupported questions produce a clear limitation response rather than a fabricated fact.
- Provider failures do not crash the whole application.

---

## Phase 6 — Build the FastAPI Backend

### Suggested Endpoints

| Method | Endpoint | Purpose |
|---|---|---|
| GET | `/health` | Check that the API is running |
| POST | `/documents/upload` | Upload and process a document |
| GET | `/documents` | List indexed documents |
| DELETE | `/documents/{document_id}` | Remove a document and its indexed chunks |
| POST | `/chat` | Ask a question and return an answer with sources |

### Tasks

1. Create the FastAPI application.
2. Define request and response schemas.
3. Implement one endpoint at a time.
4. Add input validation and upload limits.
5. Return consistent HTTP status codes and readable error messages.
6. Keep route handlers thin; delegate work to services.
7. Add API tests using FastAPI TestClient.
8. Document endpoints through FastAPI's generated API documentation.

### Deliverables

- `main.py`, route definitions, and schemas.
- Tested REST API.

### Definition of Done

- Health check works.
- Documents can be uploaded and listed.
- Questions return answers and source metadata.
- Errors are handled predictably.
- API endpoints can be explored locally through `/docs`.

---

## Phase 7 — Build the Streamlit Interface

### Screens and Components

1. **Document management:** upload supported files and show processing status.
2. **Document list:** display indexed filenames and allow permitted deletion.
3. **Question interface:** provide a question input and submit action.
4. **Answer display:** show the generated response clearly.
5. **Sources panel:** show source filename and page number when available.
6. **Conversation display:** retain the visible chat during the session.
7. **Error messages:** explain upload, API, and model failures without exposing secrets.

### Tasks

1. Build a simple, accessible layout.
2. Connect the UI to FastAPI over HTTP.
3. Show loading and processing states.
4. Validate files before sending them to the API.
5. Display citations with answers.
6. Keep backend business logic out of the Streamlit UI.

### Deliverables

- `frontend/app.py`.
- Working end-to-end local application.

### Definition of Done

A user can upload a sample document, ask a question, receive a grounded answer, and see the supporting source through the UI.

---

## Phase 8 — Add Conversation Context

### Tasks

1. Store recent messages in Streamlit session state or a backend conversation service.
2. Assign a conversation identifier if context is managed by the backend.
3. Rewrite follow-up questions into standalone questions when needed.
4. Retrieve document evidence for the rewritten question.
5. Keep conversation context separate from factual source evidence.
6. Limit stored history to a sensible size.
7. Test follow-up questions such as “What about interns?” after asking about leave policy.

### Deliverables

- Follow-up questions that preserve conversational meaning.

### Definition of Done

- Follow-up questions are interpreted using prior turns.
- Answers are still grounded in retrieved documents.
- Old conversation text does not override current document evidence.

---

## Phase 9 — Add Document Comparison

### Tasks

1. Allow users to select two indexed documents or versions.
2. Retrieve or extract relevant content from both documents.
3. Ask the LLM to summarize differences using only the supplied content.
4. Present changes in a structured format: topic, old value, new value, and source.
5. Distinguish confirmed changes from missing or ambiguous information.
6. Cite both documents where possible.

### Deliverables

- Document comparison workflow.

### Definition of Done

- Users can compare two policy versions.
- The output identifies differences and references supporting sources.
- Missing evidence is reported rather than invented.

---

## Phase 10 — Improve Retrieval Quality and Evaluate the System

### Tasks

1. Create a small evaluation dataset of questions, expected source passages, and expected answer points.
2. Measure whether the correct passages appear in retrieved results.
3. Review answer groundedness, citation correctness, and unsupported-answer behavior.
4. Tune chunk size, overlap, and `top_k`.
5. Consider hybrid search or a reranker only if evaluation shows a need.
6. Add optional relevance scores with clear labels.
7. Do not present similarity scores as calibrated answer-confidence percentages.

### Suggested Evaluation Measures

- **Retrieval Recall@k:** whether expected evidence appears in the top-k retrieved chunks.
- **Citation correctness:** whether cited sources support the answer.
- **Answer groundedness:** whether claims are supported by retrieved evidence.
- **Abstention quality:** whether the system avoids answering when evidence is insufficient.
- **Latency:** time required to retrieve and generate an answer.

### Deliverables

- Repeatable evaluation dataset and report.
- Documented retrieval settings and known limitations.

### Definition of Done

- The system is tested on known questions, not only impressive demos.
- Changes to chunking or retrieval can be compared against a baseline.
- Limitations are recorded honestly.

---

## Phase 11 — Add Security and Reliability Controls

### Tasks

1. Validate file type, file size, and upload content.
2. Use generated storage names rather than trusting uploaded filenames as paths.
3. Keep API keys in environment variables or a secrets manager.
4. Add authentication before exposing the application to multiple users.
5. Enforce document-level authorization before retrieval, not only in the UI.
6. Treat document text as untrusted input to reduce prompt-injection risk.
7. Add timeouts, bounded retries, and rate limits where appropriate.
8. Avoid logging sensitive document content or secrets.
9. Define retention and deletion behavior for uploaded documents and vectors.
10. Use HTTPS and managed secrets when deploying.

### Deliverables

- Security checklist and tested input validation.
- Documented access-control design.

### Definition of Done

- Secrets are not committed.
- Unauthorized users cannot access restricted documents.
- Uploads and model calls have reasonable limits.
- Data deletion and retention behavior is documented.

**Important:** Do not describe the app as production-secure until authentication, authorization, deployment settings, and security testing have actually been implemented.

---

## Phase 12 — Testing, Documentation, and GitHub Readiness

### Tasks

1. Add unit tests for document processing, chunking, and retrieval.
2. Add API integration tests.
3. Test the full upload-to-answer workflow.
4. Mock external LLM calls in routine automated tests where practical.
5. Add setup instructions and architecture diagrams to `README.md`.
6. Document environment variables in `.env.example` without real secrets.
7. Include synthetic sample documents or a script that generates them.
8. Record supported file formats, limitations, and known issues.
9. Use meaningful Git commits and keep the repository organized.
10. Verify that a fresh clone can be configured by following the README.

### Deliverables

- Test suite.
- Professional README.
- Clean GitHub repository.

### Definition of Done

A reviewer can understand the architecture, install the project, configure the required provider, run the app, and reproduce the documented demo without needing private company data.

---

## Phase 13 — Optional Deployment

Only begin deployment after the local application and tests are stable.

### Tasks

1. Select a deployment platform that supports the required Python services and storage.
2. Configure environment variables securely.
3. Decide whether ChromaDB will be persistent on a supported volume or replaced by a managed deployment later.
4. Configure API/UI URLs, CORS where required, timeouts, and upload limits.
5. Add a health check and basic operational logging.
6. Test restart behavior and data persistence.
7. Document the deployed version and limitations.

### Definition of Done

- The deployed app is accessible to its intended audience.
- Secrets remain private.
- Storage persistence is understood and tested.
- The README explains how to use the demo safely.

---

## 5. API Contract (Initial Proposal)

### `POST /documents/upload`

**Input:** One or more supported files using multipart form data.

**Successful response example:**

```json
{
  "document_id": "generated-id",
  "filename": "HR_Policy.pdf",
  "status": "indexed",
  "chunks_created": 24
}
```

### `POST /chat`

**Input:**

```json
{
  "question": "How many annual leave days are provided?",
  "conversation_id": null
}
```

**Successful response example:**

```json
{
  "answer": "The policy states that eligible employees receive 20 annual leave days.",
  "sources": [
    {
      "document_id": "generated-id",
      "filename": "HR_Policy.pdf",
      "page": 12
    }
  ],
  "conversation_id": "generated-conversation-id"
}
```

These are proposed examples, not existing application behavior. The final schema should be validated in code. Do not include a numeric answer unless the sample document actually contains it.

---

## 6. Configuration and Secret Management

Create `.env.example` with placeholder values, for example:

```dotenv
LLM_PROVIDER=choose-provider
LLM_API_KEY=replace-with-your-key
LLM_MODEL=replace-with-supported-model
EMBEDDING_MODEL=replace-with-supported-model
CHROMA_PERSIST_DIRECTORY=./storage/chroma
TOP_K=4
MAX_UPLOAD_MB=10
```

Create a local `.env` with real settings. Keep it out of Git.

Do not assume every provider uses the same environment variable names or model identifiers. Match configuration to the selected provider's current documentation.

---

## 7. Testing Strategy

| Test level | What to verify |
|---|---|
| Unit tests | Text extraction, chunking, metadata, validation |
| Retrieval tests | Relevant source chunks are returned for known questions |
| API tests | Status codes, schemas, uploads, errors, health check |
| Integration tests | Upload → index → question → answer → citations |
| Evaluation tests | Retrieval recall, groundedness, citation correctness, abstention |
| Security tests | Invalid uploads, authorization boundaries, secret exposure |
| Manual acceptance test | A new user can follow the README and complete the demo |

Use synthetic company documents for repeatable tests. Never make the test suite depend on confidential company files.

---

## 8. MVP Acceptance Checklist

The first complete version is ready when all of the following are true:

- [x] A user can upload PDF, DOCX, and TXT files.
- [x] Text extraction and chunking preserve useful source metadata.
- [x] Embeddings are stored persistently in ChromaDB.
- [x] A question retrieves relevant document chunks.
- [x] The LLM answers using the retrieved context.
- [x] Answers show supporting source references where available.
- [x] Unsupported questions receive a cautious response.
- [x] FastAPI exposes working endpoints.
- [x] Streamlit provides a usable upload-and-question interface.
- [x] Core behavior has automated tests.
- [x] API keys and private documents are excluded from Git.
- [x] README setup instructions work on a fresh clone.


---

## 9. Recommended Build Order at a Glance

| Order | Milestone | Main result |
|---:|---|---|
| 1 | Environment and repository | Clean development setup |
| 2 | Document processing | Extracted text with metadata |
| 3 | Chunking | Searchable text pieces |
| 4 | Embeddings and ChromaDB | Persistent vector storage |
| 5 | Retrieval | Relevant evidence for a question |
| 6 | LLM generation | Context-grounded answer |
| 7 | FastAPI | Usable backend endpoints |
| 8 | Streamlit | End-to-end user interface |
| 9 | Conversation context | Follow-up questions |
| 10 | Document comparison | Version-difference summary |
| 11 | Evaluation and security | Measured quality and safer behavior |
| 12 | GitHub documentation | Reproducible portfolio project |
| 13 | Optional deployment | Hosted demo |

---

## 10. Engineering Principles

1. **Build in small increments.** Keep the application runnable after every milestone.
2. **Test retrieval before generation.** If the right evidence is not found, a better prompt alone will not fix the system.
3. **Cite evidence, not guesses.** Source references must point to the actual content used.
4. **Measure quality.** Use a repeatable evaluation set rather than judging the project only by a few demos.
5. **Keep secrets private.** Never commit API keys or confidential documents.
6. **Prefer simple architecture first.** Add reranking, hybrid search, advanced memory, and deployment only when the MVP is stable.
7. **Be accurate on the resume.** Describe a feature as implemented only after it works and has been tested.
8. **Document decisions.** Record provider choices, configuration, trade-offs, and known limitations in the README.

---

## 11. Immediate Next Steps

1. Confirm the installed Python version.
2. Create the repository and virtual environment.
3. Select the LLM and embedding provider.
4. Install and test the initial dependencies.
5. Implement Phase 1: read a sample PDF and extract text.
6. Add a small synthetic HR policy document and verify its page text.
7. Move to chunking only after extraction works.

**Recommended approach:** Complete the phases in order. The first milestone is not a chatbot; it is a reliable document reader. The chatbot comes after retrieval and evidence handling work correctly.

# AI Research Knowledge Hub - Project Handoff

## 1. Purpose

AI Research Knowledge Hub is a central-banking research knowledge management application. It is intended to let authorized users upload PDF/DOCX research documents, extract and process text, create embeddings, store vectors in ChromaDB, perform semantic search, ask RAG questions, and generate document summaries with a local Ollama model.

The visual target is the supplied Bank of Tanzania-inspired dashboard screenshot:

- Black institutional sidebar
- Warm ivory/cream main background
- Gold accents
- Tanzania color stripes
- Subtle floating gold particles
- Compact desktop dashboard with a center content area and a right AI Assistant column
- The original greeting section was intentionally removed

The application is a real frontend/backend integration. Do not reintroduce illustrative data where the backend has no data.

## 2. Current Status

### Frontend

The frontend is a React/Vite application and currently includes:

- Dashboard view
- Research Documents view
- Document details view
- Semantic Search view
- Ask AI view
- Research Summaries view
- Upload Document view
- Saved Research empty state
- Profile view
- Settings unavailable-state view
- Responsive sidebar drawer on smaller screens
- Real API-backed documents and dashboard statistics
- Real RAG answers and source citations
- Real summary requests
- JWT token propagation when a token is present
- Header global search navigation
- Document-specific Ask AI action

### Backend

The FastAPI backend currently starts successfully in the supported Python 3.11 environment and exposes:

- Document upload and processing
- Document list and details
- Document deletion
- Semantic search through ChromaDB
- RAG question answering through Ollama
- Summary generation through Ollama
- JWT authentication routes
- Database-backed dashboard summary route

### Verified live data

At the time of this handoff:

- Dashboard summary returns HTTP 200
- Documents endpoint returns HTTP 200
- Database contains at least one processed document
- The repository ChromaDB collection `research_documents` contains 739 indexed chunks
- Ask AI has returned `success: true`, a non-empty answer, and 5 source citations
- Ollama model configured for RAG/chat: `deepseek-r1:1.5b`
- Ollama model configured for research summaries: `qwen3.5:0.8b`

## 3. Repository Structure

```text
ai-research-knowledge-hub/
  backend/
    app/
      main.py
      api/
        auth.py
        chat.py
        dashboard.py
        documents.py
        search.py
        summarization.py
      core/
        security.py
      db/
        database.py
      models/
        document.py
        user.py
      schemas/
        auth.py
      services/
        document_processor.py
        document_service.py
        embedding_service.py
        llm_service.py
        rag_service.py
        summarization_service.py
        vector_store.py
    requirements.txt
  data/
    documents/
    processed/
    uploads/
  frontend/
    src/
      App.jsx
      index.css
      components/Layout/
        Header.jsx
        Sidebar.jsx
        TanzaniaStripe.jsx
      services/api.js
      hooks/useDocuments.js
    public/
      bot-logo.svg
  vectorstore/
    chroma.sqlite3
    <chroma collection directory>/
  PROJECT_HANDOFF.md
```

## 4. Important Frontend Files

### `frontend/src/App.jsx`

Main application orchestration. It owns:

- Current page state
- Sidebar open state
- Documents state
- Dashboard summary state
- Search state
- Chat state and citations
- Summary state
- Upload state
- Current authenticated user state
- Document details loading and error state

The app uses state-based navigation rather than React Router routes. `activePage` values include:

```text
dashboard
documents
document
search
chat
summarize
upload
saved
profile
settings
```

### `frontend/src/services/api.js`

Axios client. Default API base URL:

```text
http://localhost:8002/api
```

It can be overridden with:

```text
VITE_API_BASE_URL
```

The Axios request interceptor reads `localStorage.access_token` and sends it as a Bearer token when present.

### `frontend/src/components/Layout/Header.jsx`

Contains:

- Mobile menu button
- Global search form
- Notification icon
- Help icon
- Authenticated user display when available
- Logout control

### `frontend/src/components/Layout/Sidebar.jsx`

Contains:

- Official local BOT logo asset
- Dashboard navigation
- Documents
- Semantic Search
- Ask AI
- Summaries
- Upload
- Saved Research
- Settings
- Profile
- Authorized environment branding block

### `frontend/src/components/Layout/TanzaniaStripe.jsx`

Reusable stripe used below the header and above the footer. Current color order:

```text
GREEN -> GOLD/YELLOW -> BLACK -> GOLD/YELLOW -> BLUE
```

### `frontend/public/bot-logo.svg`

Downloaded from the official Bank of Tanzania website asset path and stored locally so the UI does not depend on a remote logo request.

## 5. Backend API Contract

Base URL:

```text
http://localhost:8002/api
```

### Health

```http
GET /health
```

Example response:

```json
{
  "status": "healthy",
  "service": "backend",
  "database": "connected"
}
```

### Dashboard summary

```http
GET /dashboard/summary
```

Response shape:

```json
{
  "stats": {
    "total_documents": 1,
    "research_topics": 18,
    "ai_questions": null,
    "processed_documents": 1
  },
  "topics": [
    {"label": "Monetary Policy", "count": 0}
  ],
  "recent_activity": [
    {
      "text": "Document ... completed",
      "time": "ISO datetime"
    }
  ]
}
```

Important: `ai_questions` is currently `null` because the backend does not have an AI question history model/table. The frontend must display an unavailable state, not a fabricated number.

### Documents

```http
GET /documents/
GET /documents/{document_id}
POST /documents/upload
DELETE /documents/{document_id}
```

Document list items include:

```json
{
  "id": 1,
  "title": "...",
  "author": null,
  "publication_year": null,
  "file_name": "...",
  "file_type": "pdf",
  "department": null,
  "document_type": null,
  "chunk_count": 739,
  "is_processed": true,
  "created_at": "ISO datetime"
}
```

The upload endpoint accepts multipart form data. The frontend sends the file and title only when no real author/year is available; it must not invent metadata.

### Semantic search

```http
POST /search/
```

Request:

```json
{
  "query": "inflation",
  "top_k": 5
}
```

Response is an array of results:

```json
[
  {
    "id": "doc_1_chunk_23",
    "document": "retrieved text",
    "metadata": {
      "document_id": 1,
      "chunk_index": 23,
      "page_number": 1,
      "chunk_length": 948
    },
    "distance": 0.84
  }
]
```

### RAG Ask AI

```http
POST /chat/
```

Request:

```json
{
  "question": "What are the main drivers of inflation in Tanzania?",
  "top_k": 5
}
```

Response:

```json
{
  "success": true,
  "question": "...",
  "answer": "real Ollama answer",
  "sources": [
    {
      "document_id": 1,
      "chunk_index": 186,
      "relevance_score": 0.35,
      "excerpt": "real retrieved excerpt"
    }
  ],
  "error": null
}
```

The frontend has a single retry when a successful response contains an empty answer. The backend LLM cleaner was fixed so it only removes actual `<think>...</think>` blocks and does not accidentally erase the answer.

### Summarization

```http
POST /summarize/
GET /summarize/document/{document_id}
```

Request:

```json
{
  "document_id": 1,
  "max_tokens": 500,
  "temperature": 0.3
}
```

The response may contain a structured `summary` object and/or `raw_summary`.

### Authentication

```http
POST /auth/login
POST /auth/register
GET /auth/me
POST /auth/change-password
POST /auth/logout
```

Login request:

```json
{
  "username": "...",
  "password": "..."
}
```

Login response includes `access_token`, `token_type`, `user_id`, `username`, and `role`.

The frontend stores `access_token` in local storage after login. There is currently no dedicated Login UI component in the frontend, although the API service functions exist.

## 6. Environment and Run Commands

### Recommended Python environment

Python 3.11 is installed and the backend environment is:

```text
.venv311/
```

Python 3.14 caused native-package compatibility/build issues with the original dependency set. Use `.venv311` for backend commands.

### Install backend dependencies

From repository root:

```powershell
.\.venv311\Scripts\python.exe -m pip install -r backend\requirements.txt
```

### Start backend

```powershell
.\.venv311\Scripts\python.exe -m uvicorn app.main:app --app-dir backend --host 0.0.0.0 --port 8002
```

The backend loads the embedding model at startup, so the first startup can take time.

### Start frontend

From `frontend`:

```powershell
npm install
npm run dev -- --host 0.0.0.0 --port 5176
```

The machine has used several Vite ports. The currently verified frontend port is `5176`. If the port is occupied, Vite may choose another port; update `VITE_API_BASE_URL` only if the backend port changes.

### Build frontend

```powershell
cd frontend
npm run build
```

### Lint frontend

```powershell
cd frontend
npm run lint
```

## 7. Ollama Requirements

The backend expects Ollama at:

```text
http://localhost:11434
```

Configured models:

```text
RAG/chat: deepseek-r1:1.5b (LLM_MODEL)
Research summaries: qwen3.5:0.8b (SUMMARY_LLM_MODEL)
```

The backend checks Ollama during startup and uses it for:

- RAG answers
- Document summaries

The model can be slow on CPU. Ask AI may take tens of seconds or longer. The UI displays a loading state while waiting.

## 8. Critical Fixes Already Made

1. Added missing backend dependencies:
   - `python-multipart`
   - `email-validator`
   - `python-jose`
   - `passlib`
   - compatible `bcrypt`

2. Created a Python 3.11 virtual environment because Python 3.14 could not reliably build the native dependencies.

3. Upgraded ChromaDB to `1.5.9` to match the persisted vector-store schema.

4. Fixed the vector-store path. The backend previously opened:

```text
C:\Users\abuba\vectorstore
```

The real indexed store is:

```text
C:\Users\abuba\ai-research-knowledge-hub\vectorstore
```

The default `VectorStore` directory is now `vectorstore`, resolved relative to the repository root.

5. Fixed the LLM answer cleaner. The previous condition effectively tested an empty string with `in`, causing valid answers to be reduced to empty text in some cases.

6. Added the database-backed `/api/dashboard/summary` endpoint.

7. Removed frontend fallback/mock dashboard documents, statistics, AI history, and activity data.

8. Added real document metadata fields for department/category and document type.

9. Added document details state and document-specific Ask AI actions.

10. Added JWT request interceptor and login/logout API service functions.

## 9. Current Limitations

These are real backend limitations, not frontend bugs:

- No persisted AI question history endpoint/model exists.
- No saved-research table or endpoint exists. The frontend intentionally shows an empty state instead of treating every document as saved.
- No configurable settings endpoint exists. Settings shows an unavailable-state message.
- No dedicated login/register frontend page exists yet.
- Document download endpoint does not exist.
- Document delete is present in the backend but not yet exposed as a frontend action.
- The dashboard topic statistic currently counts `Keyword` rows, while the visible topic cards use active `Category` rows and document counts. Review this definition before changing it.
- Chroma telemetry may print compatibility warnings in logs. These do not prevent retrieval.
- LLM latency can be high because Ollama runs locally.

Do not solve these limitations by inventing values or fake UI activity. Add backend models/endpoints first when a real feature is required.

## 10. Functional Smoke Tests

### Backend health

```powershell
Invoke-WebRequest -UseBasicParsing http://localhost:8002/api/health
```

Expected status: `200`.

### Dashboard summary

```powershell
Invoke-WebRequest -UseBasicParsing http://localhost:8002/api/dashboard/summary
```

Expected status: `200`.

### Semantic search

```powershell
$payload = '{"query":"inflation","top_k":5}'
Invoke-RestMethod -Method Post -Uri http://localhost:8002/api/search/ -ContentType 'application/json' -Body $payload
```

Expected: an array containing retrieved chunks when the repository Chroma store is available.

### Ask AI

```powershell
$payload = '{"question":"What are the main drivers of inflation in Tanzania?","top_k":5}'
Invoke-RestMethod -Method Post -Uri http://localhost:8002/api/chat/ -ContentType 'application/json' -Body $payload -TimeoutSec 300
```

Expected:

- `success: true`
- non-empty `answer`
- source citations, normally 5 results

### Frontend

Open:

```text
http://localhost:5176/
```

Verify:

- Real document appears after API loading
- Dashboard numbers are backend values
- Global search opens Semantic Search
- Ask AI button enters loading state and eventually displays answer and sources
- View document opens details
- Document-specific Ask AI opens Ask AI with a document-specific question
- Summary page can select a real document
- Upload page sends a real multipart request
- Profile and Settings buttons navigate

## 11. Guidance for the Next AI Agent

When continuing this project:

1. Read this file first.
2. Preserve the screenshot-based visual design.
3. Inspect actual backend routes before adding frontend API calls.
4. Never restore mock/fallback data just to fill empty cards.
5. Keep unavailable backend features as honest empty states.
6. Use `.venv311` for backend commands.
7. Use the repository `vectorstore` directory, not `C:\Users\abuba\vectorstore`.
8. Do not downgrade ChromaDB without checking the persisted store schema.
9. Keep AI answers and sources from the live `/api/chat/` response.
10. Test both direct API responses and browser behavior when debugging Ask AI.
11. Avoid broad UI redesigns. Make small changes tied to a concrete requirement.
12. Do not commit changes unless explicitly requested by the user.

## 12. Last Verified URLs

- Frontend: http://localhost:5176/
- Backend root: http://localhost:8002/
- Backend health: http://localhost:8002/api/health
- Swagger docs: http://localhost:8002/docs

## 13. Last Verification Result

The latest verification confirmed:

- Frontend production build passed.
- Frontend diagnostics reported no errors in changed files.
- Backend syntax checks passed.
- Health endpoint returned HTTP 200.
- Dashboard summary returned HTTP 200.
- Semantic search returned indexed document chunks.
- Ask AI returned a non-empty answer with 5 sources.
- Browser Ask AI flow showed loading, then rendered the real answer and citations.

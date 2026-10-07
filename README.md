# AI Research Knowledge Hub

Central-banking research document management, semantic search, grounded RAG, and document summarization.

## Local Run

Prerequisites:

- PostgreSQL running with the database configured by `DATABASE_URL`.
- Ollama running at `OLLAMA_HOST` with the configured `LLM_MODEL`.
- Python 3.11 and Node.js.

Backend:

```powershell
cd backend
..\.venv311\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8002
```

Frontend:

```powershell
cd frontend
npm install
npm run dev
```

The frontend uses `http://localhost:8002/api` by default. Set `VITE_API_BASE_URL` to override it.

For first-time local setup, create an administrator with the existing `backend/create_admin.py` script and change the bootstrap password immediately.

## Docker

With Docker Desktop installed:

```powershell
$env:SECRET_KEY = 'replace-with-a-long-random-secret'
docker compose up --build
```

Open `http://localhost:5173`. The API is available at `http://localhost:8002`. Ollama models are stored in a named volume; pull the configured model from the Ollama container before using AI features.

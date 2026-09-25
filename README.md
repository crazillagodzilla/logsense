# LogSense - AIOps Log Analytics Platform

LogSense is a real-time AIOps platform for ingesting application and database logs, detecting anomalies, storing incident history in PostgreSQL, and generating AI-assisted root-cause analysis using FAISS-backed runbook retrieval and Gemini.

## Architecture Overview

- Backend: FastAPI + SQLModel + PostgreSQL
- AI & ML: Drain3 template mining, Isolation Forest anomaly detection
- RAG: FAISS vector search with Sentence Transformers embeddings
- AI RCA: Gemini Markdown responses powered by runbook context
- Frontend: React + Vite + Tailwind

## Quick Start

### Prerequisites
Before you start, make sure you have:

- Python 3.12+
- PostgreSQL running locally
- Node.js and npm for the frontend
- Git

### 1. Clone the repository
```bash
git clone <repository-url>
cd logsense
```

### 2. Create the backend virtual environment
```bash
python3 -m venv backend/venv
source backend/venv/bin/activate
```

For Windows PowerShell:
```powershell
python -m venv backend\venv
.\backend\venv\Scripts\Activate.ps1
```

### 3. Install backend dependencies
```bash
cd backend
pip install -r requirements.txt
```

### 4. Start PostgreSQL and create the database
The app expects a PostgreSQL database named `logsense` by default. Make sure Postgres is running, then create the database:

```bash
createdb logsense
```

If `createdb` is not available, use the Postgres shell:

```bash
psql -U postgres
CREATE DATABASE logsense;
\q
```

### 5. Configure environment variables
Create a `.env` file at the project root or inside `backend/` if you want to override the defaults. The backend expects these values (with sensible defaults in code):

```bash
POSTGRES_USER=postgres
POSTGRES_PASSWORD=password
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=logsense
GEMINI_API_KEY=your_key_here
```

If you are using a different local database user or password, update the values before starting the backend.

### 6. Download ML model artifacts
These binaries are intentionally not committed to Git. Download the release bundle before starting the backend for local anomaly detection.

```bash
cd logsense
python scripts/download_model_artifacts.py
```

You can override the bundle URL if needed:

```bash
LOGSENSE_MODEL_BUNDLE_URL=https://github.com/crazillagodzilla/logsense/releases/download/v1.0.0-models/logsense-models-v1.0.0.zip python scripts/download_model_artifacts.py
```

### 7. Start the backend
```bash
cd backend
source ../backend/venv/bin/activate
PYTHONPATH=. uvicorn app.main:app --host 127.0.0.1 --port 8000
```

If you are already in the activated venv from the repo root, this is also valid:

```bash
cd backend
PYTHONPATH=. uvicorn app.main:app --host 127.0.0.1 --port 8000
```

The API will be available at `http://localhost:8000`.

### 8. Frontend setup
```bash
cd frontend
npm install
npm run dev
```

The frontend usually runs on `http://localhost:5173` by default.

### 9. Health check
```bash
curl http://localhost:8000/health
```

Expected response:

```json
{"status": "ok"}
```

## Key Backend Endpoints

- `POST /api/v1/logs/ingest` - ingests a log and evaluates anomaly risk
- `GET /api/v1/incidents` - lists incidents
- `GET /api/v1/incidents/{incident_id}` - returns a detailed incident with RCA context
- `PATCH /api/v1/incidents/{incident_id}/status` - updates status
- `GET /api/v1/runbooks` - lists runbooks
- `POST /api/v1/runbooks` - saves a runbook and indexes it into FAISS
- `GET /api/v1/analytics/summary` - operational summary metrics
- `GET /api/v1/analytics/volume-chart` - chart data

## Model Artifact Policy

Large model binaries and FAISS-generated artifacts are not committed to Git. For development work, the team should use a versioned release bundle and a bootstrap script instead.

Recommended flow:

- upload a release bundle to GitHub Releases containing the `.joblib` files and any required index assets
- keep them versioned by model release
- use `python scripts/download_model_artifacts.py` to fetch the right bundle locally
- validate on startup that required artifacts exist before the anomaly pipeline loads them

This keeps the repo small while ensuring every dev machine gets the same model version.

## RAG & RCA Pipeline

The backend now includes a DB-backed FAISS runbook index:

- Runbooks are stored in PostgreSQL
- Content is embedded using `sentence-transformers/all-MiniLM-L6-v2`
- Embeddings are persisted in a local FAISS index at `backend/faiss_index/`
- The incident RCA path retrieves the most relevant runbooks and includes them in the Gemini prompt
- If Gemini is unavailable, the backend falls back to a Markdown-safe RCA response using the retrieved runbook context

## Testing

Run the focused validation suite for the RAG pipeline:

```bash
cd backend
PYTHONPATH=. pytest tests/test_rag_pipeline.py -q
```

## Development Workflow

To keep the `main` branch stable, create feature branches for your work and open a PR before merge.

```bash
git checkout main
git pull origin main
git checkout -b feature/my-change
```

## Notes

- The legacy in-memory store has been removed in favor of PostgreSQL-backed analytics.
- The project expects the backend virtual environment to live under `backend/venv`.
- Database initialization occurs on app startup via the SQLModel metadata creation call.
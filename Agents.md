# AGENTS.md - LogSense Developer & AI Assistant Instructions

## 1. System Context & Architecture
LogSense is a real-time AIOps log analytics platform built to detect point anomalies and generate automated AI Root Cause Analysis (RCA) reports using RAG.

### Core Data Flow
Filebeat ──► FastAPI Ingestion ──► PostgreSQL (SQLModel) ──► (Drain Parser + Isolation Forest) ──► FAISS + Gemini API (RAG RCA) ──► React Dashboard

---

## 2. Team Role Boundaries & Ownership
AI agents must strictly respect technical domain boundaries to prevent cross-module breaks:

* **AI, Analytics & Schema Lead (Owner):** Owns `database.py`, SQLModel schemas, Drain3 parsing, Isolation Forest window fitting, FAISS vector indexing, and Gemini prompt templates.
* **Data & Pipeline Lead:** Owns Filebeat agent configs, FastAPI `/api/v1/logs/ingest` routes, `chaos_engine.py`, and Loghub benchmark evaluation scripts.
* **Frontend Lead:** Owns the React UI layout, live streaming log table, Recharts visualizations, and Markdown incident drawer.

---

## 3. Strict Coding Rules & Guidelines

### Backend & Database (Python / FastAPI / SQLModel)
* **ORM Usage:** Always use `SQLModel` for database tables and Pydantic validation. Do not write raw SQL strings or introduce secondary ORMs like raw SQLAlchemy or Peewee.
* **Async Ingestion:** Keep log ingestion routes non-blocking. Always offload Drain3 parsing and Isolation Forest evaluations to background tasks or async queues (`BackgroundTasks` in FastAPI).
* **Environment Variables:** Never hardcode database URIs, API keys, or host ports. Use `os.getenv` with sensible fallbacks.
* **Database Schema Modifications:** Do NOT alter `database.py` models (`Log`, `Incident`, `Runbook`) unless explicitly requested by the Schema Lead.

### Machine Learning & Vector Search
* **Model Choice:** The Models are trained in colab and stored at artifacts read "Models.md" for more info.
* **Vector Embeddings:** Use `sentence-transformers/all-MiniLM-L6-v2` to generate embeddings for FAISS runbook indexing.
* **Scope Constraint:** Focus pipeline evaluation exclusively on **application server** and **database log** sources for Semester 1.

### Frontend (React / Tailwind / Shadcn UI)
* **Mock First:** Components must be capable of rendering using fallback JSON objects if the backend service is offline.
* **Markdown Rendering:** Render Gemini API output inside the Incident Drawer using `react-markdown` to properly format bolding, headers, and code blocks.

---

## Technical Stack
- Backend: Python 3.12, FastAPI, SQLModel, PostgreSQL
- ML / Parsing: LogAI (Salesforce), Drain3, Isolation Forest
- RAG & AI: FAISS (`all-MiniLM-L6-v2`), Gemini API
- Frontend: React.js, Vite, Tailwind CSS / Shadcn UI

## Development & Test Commands
- Backend venv: `source backend/venv/bin/activate`
- Run Backend: `uvicorn backend.app.main:app --reload`
- Run Frontend: `cd frontend && npm run dev`
- Test Chaos Generator: `python ingestion/chaos/chaos_engine.py --crash`


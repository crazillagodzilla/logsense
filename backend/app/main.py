from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import analytics, incidents, ingest, runbooks
from app.core.database import init_db


app = FastAPI(
    title="LogSense API",
    description="Operational log analytics, incident RCA, and runbook APIs.",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(ingest.router, prefix="/api/v1")
app.include_router(incidents.router, prefix="/api/v1")
app.include_router(analytics.router, prefix="/api/v1")
app.include_router(runbooks.router, prefix="/api/v1")


@app.on_event("startup")
def on_startup() -> None:
    init_db()


@app.get("/health", tags=["system"])
def health_check() -> dict[str, str]:
    return {"status": "ok"}

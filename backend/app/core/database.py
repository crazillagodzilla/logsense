import fcntl
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional, List

from alembic import command
from alembic.config import Config
from sqlmodel import Field, SQLModel, create_engine, Session, Relationship

from app.core.config import settings

# =====================================================================
# 1. DATABASE CONNECTION CONFIGURATION
# =====================================================================
DATABASE_URL = settings.database_url

engine = create_engine(
    DATABASE_URL,
    echo=settings.database_echo,
    pool_size=20,
    max_overflow=10
)

# =====================================================================
# 2. SQLMODEL / POSTGRESQL TABLES SCHEMA
# =====================================================================

class Log(SQLModel, table=True):
    __tablename__ = "logs"

    id: Optional[int] = Field(default=None, primary_key=True)
    timestamp: datetime = Field(default_factory=datetime.utcnow, index=True)
    source_host: str = Field(index=True, max_length=100)
    log_level: str = Field(index=True, max_length=20)
    raw_message: str

    template_id: Optional[int] = Field(default=None, index=True)
    parsed_template: Optional[str] = Field(default=None)

    incidents: List["Incident"] = Relationship(back_populates="trigger_log")


class Incident(SQLModel, table=True):
    __tablename__ = "incidents"

    id: Optional[int] = Field(default=None, primary_key=True)
    created_at: datetime = Field(default_factory=datetime.utcnow, index=True)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    severity: str = Field(index=True, max_length=20)
    title: str = Field(max_length=255)
    status: str = Field(default="OPEN", index=True, max_length=20)

    trigger_log_id: Optional[int] = Field(default=None, foreign_key="logs.id")
    trigger_log: Optional[Log] = Relationship(back_populates="incidents")

    gemini_rca: str


class Runbook(SQLModel, table=True):
    __tablename__ = "runbooks"

    id: Optional[int] = Field(default=None, primary_key=True)
    title: str = Field(max_length=255)
    category: str = Field(index=True, max_length=100)
    content: str
    created_at: datetime = Field(default_factory=datetime.utcnow, index=True)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

# =====================================================================
# 3. DATABASE INITIALIZATION & HELPER FUNCTIONS
# =====================================================================

def _should_skip_migration_on_reload() -> bool:
    argv = " ".join(sys.argv).lower()
    reload_flags = {"--reload", "--reload-dir", "--reload-include", "--reload-exclude"}
    if any(flag in argv for flag in reload_flags):
        return True
    return os.getenv("UVICORN_RELOAD", "").lower() in {"1", "true", "yes"}


def init_db():
    if _should_skip_migration_on_reload():
        return

    alembic_cfg = Config(str(Path(__file__).resolve().parents[2] / "alembic.ini"))
    lock_path = Path(__file__).resolve().parents[2] / ".migration.lock"

    with lock_path.open("w") as lock_file:
        try:
            fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            return

        command.upgrade(alembic_cfg, "head")


def get_session():
    with Session(engine) as session:
        yield session

if __name__ == "__main__":
    init_db()

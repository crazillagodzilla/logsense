from dataclasses import dataclass
import os
from pathlib import Path
from urllib.parse import quote_plus


ROOT_DIR = Path(__file__).resolve().parents[3]
BACKEND_DIR = Path(__file__).resolve().parents[2]


def load_env_file() -> None:
    """Load root/backend .env values without overriding exported env vars."""
    for env_path in (ROOT_DIR / ".env", BACKEND_DIR / ".env"):
        if not env_path.exists():
            continue

        for line in env_path.read_text().splitlines():
            stripped = line.strip()
            if not stripped or stripped.startswith("#") or "=" not in stripped:
                continue
            key, value = stripped.split("=", 1)
            os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


load_env_file()


@dataclass(frozen=True)
class Settings:
    gemini_api_key: str | None = os.getenv("GEMINI_API_KEY")
    postgres_user: str = os.getenv("POSTGRES_USER", "postgres")
    postgres_password: str = os.getenv("POSTGRES_PASSWORD", "password")
    postgres_host: str = os.getenv("POSTGRES_HOST", "localhost")
    postgres_port: str = os.getenv("POSTGRES_PORT", "5432")
    postgres_db: str = os.getenv("POSTGRES_DB", "logsense")
    database_echo: bool = os.getenv("DATABASE_ECHO", "false").lower() == "true"

    @property
    def database_url(self) -> str:
        user = quote_plus(self.postgres_user)
        password = quote_plus(self.postgres_password)
        host = self.postgres_host
        port = self.postgres_port
        db = quote_plus(self.postgres_db)
        return f"postgresql+psycopg2://{user}:{password}@{host}:{port}/{db}"

    @property
    def safe_database_url(self) -> str:
        user = quote_plus(self.postgres_user)
        host = self.postgres_host
        port = self.postgres_port
        db = quote_plus(self.postgres_db)
        return f"postgresql+psycopg2://{user}:***@{host}:{port}/{db}"


settings = Settings()

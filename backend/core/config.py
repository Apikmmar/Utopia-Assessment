import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv


@dataclass(frozen=True)
class DatabaseSettings:
    url: str = field(repr=False)
    password: str = field(repr=False)


# Load database credentials without expanding dollar signs in passwords.
def get_database_settings() -> DatabaseSettings:
    env_path = Path(__file__).resolve().parents[1] / ".env"
    load_dotenv(env_path, override=False, interpolate=False)
    url = os.environ.get("DATABASE_URL", "").strip()
    password = os.environ.get("DATABASE_PASSWORD", "")
    if not url or not password:
        raise ValueError("Set DATABASE_URL and DATABASE_PASSWORD in backend/.env first.")
    if not url.startswith(("postgresql://", "postgres://")):
        raise ValueError("DATABASE_URL must be a PostgreSQL connection URI.")
    if "[PROJECT-REF]" in url or "[POOLER-HOST]" in url:
        raise ValueError("Copy the actual Session pooler URI from Supabase Connect.")
    return DatabaseSettings(url=url, password=password)

import psycopg

from backend.core.config import get_database_settings


# Open a bounded, encrypted connection; the caller owns its transaction and closure.
def get_connection() -> psycopg.Connection:
    settings = get_database_settings()
    return psycopg.connect(
        settings.url,
        password=settings.password,
        sslmode="require",
        connect_timeout=10,
        options="-c statement_timeout=10000 -c lock_timeout=5000",
        prepare_threshold=None,
    )

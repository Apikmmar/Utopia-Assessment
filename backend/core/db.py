import threading

from sqlalchemy import TIMESTAMP, Column, Integer, MetaData, String, Table, create_engine, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.exc import IntegrityError as ConflictError, SQLAlchemyError as DatabaseError

from backend.core import config

meta = MetaData()
_engine = None
_engineLock = threading.Lock()

tokenUsageTable = Table(
    "token_usage", meta,
    Column("usage_id", UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")),
    Column("model_id", String(100), nullable=False),
    Column("input_token", Integer, nullable=False), Column("output_token", Integer, nullable=False), Column("total_token", Integer, nullable=False),
    Column("created_at", TIMESTAMP(timezone=True), nullable=False, server_default=text("NOW()")),
    Column("created_by", String(100), nullable=False, server_default=text("'System'")),
)

# Rewrites a plain Postgres URL onto the psycopg driver SQLAlchemy is configured for.
def psycopgUrl(url):
    for scheme in config.POSTGRES_SCHEMES:
        if url.startswith(scheme):
            return "postgresql+psycopg://" + url[len(scheme):]
    return url

# Returns the pooled, encrypted engine with bounded connect, statement, and lock waits.
def getEngine():
    global _engine
    if _engine is None:
        with _engineLock:
            if _engine is None:
                _engine = create_engine(
                    psycopgUrl(config.databaseUrl()),
                    connect_args={
                        "password": config.databasePassword(),
                        "sslmode": "require",
                        "connect_timeout": 10,
                        "options": "-c statement_timeout=10000 -c lock_timeout=5000",
                        "prepare_threshold": None,
                    },
                    pool_pre_ping=True, pool_size=10, max_overflow=20, pool_timeout=30,
                )
    return _engine

# Closes the connection pool and forgets the engine.
def disposeEngine():
    global _engine
    with _engineLock:
        if _engine is not None:
            _engine.dispose()
            _engine = None

# Opens one transaction, committed on success and rolled back on an exception.
def transaction():
    return getEngine().begin()

# Opens one read-only connection.
def connection():
    return getEngine().connect()

# Raises when the database does not answer a trivial query.
def ping():
    with getEngine().connect() as conn:
        conn.execute(text("SELECT 1"))

__all__ = [
    "ConflictError",
    "DatabaseError",
    "connection",
    "disposeEngine",
    "getEngine",
    "meta",
    "ping",
    "psycopgUrl",
    "tokenUsageTable",
    "transaction",
]

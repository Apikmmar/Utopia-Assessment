import threading
from psycopg.errors import UniqueViolation
from sqlalchemy import CHAR, TIMESTAMP, BigInteger, Boolean, Column, ForeignKey, Integer, MetaData, Numeric, SmallInteger, String, Table, Text, UniqueConstraint, create_engine, event, text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.exc import IntegrityError as ConflictError, SQLAlchemyError as DatabaseError
from core import config

meta = MetaData()
_engine = None
_engineLock = threading.Lock()

POOL_SIZE = 10
MAX_OVERFLOW = 20
POOL_TIMEOUT_SECONDS = 30
CONNECT_TIMEOUT_SECONDS = 10
STATEMENT_TIMEOUT_MS = 10000
LOCK_TIMEOUT_MS = 5000
LIKE_ESCAPE = "\\"

tokenUsageTable = Table(
    "token_usage", meta,
    Column("usage_id", UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")),
    Column("model_id", String(100), nullable=False),
    Column("input_token", Integer, nullable=False), Column("output_token", Integer, nullable=False), Column("total_token", Integer, nullable=False),
    Column("created_at", TIMESTAMP(timezone=True), nullable=False, server_default=text("NOW()")),
    Column("created_by", String(100), nullable=False, server_default=text("'System'")),
)

llmModelTable = Table(
    "llm_model", meta,
    Column("llm_model_id", UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")),
    Column("provider", String(50), nullable=False), Column("model", String(100), nullable=False),
    Column("is_active", Boolean, nullable=False, server_default=text("true")),
    Column("created_at", TIMESTAMP(timezone=True), nullable=False, server_default=text("NOW()")),
    Column("created_by", String(100), nullable=False, server_default=text("'System'")),
    Column("updated_at", TIMESTAMP(timezone=True), nullable=False, server_default=text("NOW()")),
    Column("updated_by", String(100), nullable=False, server_default=text("'System'")),
    UniqueConstraint("provider", "model", name="llm_model_provider_model_key"),
)

jobTable = Table(
    "job", meta,
    Column("job_id", UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")),
    Column("job_type", String(100), nullable=False, index=True),
    Column("payload", JSONB, nullable=False, server_default=text("'{}'::jsonb")),
    Column("status", String(20), nullable=False, server_default=text("'pending'")),
    Column("attempt", Integer, nullable=False, server_default=text("0")), Column("max_attempt", Integer, nullable=False, server_default=text("3")),
    Column("run_at", TIMESTAMP(timezone=True), nullable=False, server_default=text("NOW()")),
    Column("locked_by", String(100)), Column("locked_at", TIMESTAMP(timezone=True)),
    Column("started_at", TIMESTAMP(timezone=True)), Column("finished_at", TIMESTAMP(timezone=True)),
    Column("result", JSONB), Column("error_message", Text),
    Column("idempotency_key", String(100), unique=True), Column("request_id", String(100)),
    Column("created_at", TIMESTAMP(timezone=True), nullable=False, server_default=text("NOW()")),
    Column("created_by", String(100), nullable=False, server_default=text("'System'")),
    Column("updated_at", TIMESTAMP(timezone=True), nullable=False, server_default=text("NOW()")),
    Column("updated_by", String(100), nullable=False, server_default=text("'System'")),
)

llmInvocationTable = Table(
    "llm_invocation", meta,
    Column("llm_invocation_id", UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")),
    Column("llm_model_id", UUID(as_uuid=True), ForeignKey("llm_model.llm_model_id", ondelete="RESTRICT"), nullable=False, index=True),
    Column("request_id", String(100)), Column("status", String(20), nullable=False),
    Column("latency_ms", Integer), Column("error_message", Text),
    Column("created_at", TIMESTAMP(timezone=True), nullable=False, server_default=text("NOW()")),
    Column("created_by", String(100), nullable=False, server_default=text("'System'")),
    Column("updated_at", TIMESTAMP(timezone=True), nullable=False, server_default=text("NOW()")),
    Column("updated_by", String(100), nullable=False, server_default=text("'System'")),
)

userTable = Table(
    "user", meta,
    Column("user_id", UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")),
    Column("name", String(100), nullable=False), Column("email", String(255), nullable=False, unique=True),
    Column("phone", String(20)), Column("age", SmallInteger),
    Column("role_id", UUID(as_uuid=True), ForeignKey("role.role_id", ondelete="RESTRICT"), nullable=False, index=True),
    Column("last_login_at", TIMESTAMP(timezone=True)),
    Column("password_hash", String(255)), Column("password_changed_at", TIMESTAMP(timezone=True)),
    Column("created_at", TIMESTAMP(timezone=True), nullable=False, server_default=text("NOW()")),
    Column("created_by", String(100), nullable=False, server_default=text("'System'")),
    Column("updated_at", TIMESTAMP(timezone=True), nullable=False, server_default=text("NOW()")),
    Column("updated_by", String(100), nullable=False, server_default=text("'System'")),
)

sessionTable = Table(
    "session", meta,
    Column("session_id", UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")),
    Column("user_id", UUID(as_uuid=True), ForeignKey("user.user_id", ondelete="RESTRICT"), nullable=False, index=True),
    Column("token_hash", CHAR(64), nullable=False, unique=True),
    Column("expires_at", TIMESTAMP(timezone=True), nullable=False, index=True),
    Column("revoked_at", TIMESTAMP(timezone=True)),
    Column("last_used_at", TIMESTAMP(timezone=True), nullable=False, server_default=text("NOW()")),
    Column("ip", String(45)), Column("user_agent", String(300)),
    Column("created_at", TIMESTAMP(timezone=True), nullable=False, server_default=text("NOW()")),
    Column("created_by", String(100), nullable=False, server_default=text("'System'")),
    Column("updated_at", TIMESTAMP(timezone=True), nullable=False, server_default=text("NOW()")),
    Column("updated_by", String(100), nullable=False, server_default=text("'System'")),
)

roleTable = Table(
    "role", meta,
    Column("role_id", UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")),
    Column("role_code", String(30), nullable=False, unique=True), Column("role_name", String(50), nullable=False),
    Column("description", Text), Column("is_active", Boolean, nullable=False, server_default=text("true")),
    Column("created_at", TIMESTAMP(timezone=True), nullable=False, server_default=text("NOW()")),
    Column("created_by", String(100), nullable=False, server_default=text("'System'")),
    Column("updated_at", TIMESTAMP(timezone=True), nullable=False, server_default=text("NOW()")),
    Column("updated_by", String(100), nullable=False, server_default=text("'System'")),
)

settingTable = Table(
    "setting", meta,
    Column("setting_id", UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")),
    Column("setting_key", String(100), nullable=False, unique=True), Column("setting_value", Text, nullable=False),
    Column("value_type", String(20), nullable=False, server_default=text("'string'")), Column("description", Text),
    Column("created_at", TIMESTAMP(timezone=True), nullable=False, server_default=text("NOW()")),
    Column("created_by", String(100), nullable=False, server_default=text("'System'")),
    Column("updated_at", TIMESTAMP(timezone=True), nullable=False, server_default=text("NOW()")),
    Column("updated_by", String(100), nullable=False, server_default=text("'System'")),
)

serviceTypeTable = Table(
    "service_type", meta,
    Column("service_type_id", UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")),
    Column("service_type_code", String(30), nullable=False, unique=True), Column("service_type_name", String(50), nullable=False),
    Column("sort_order", SmallInteger, nullable=False, server_default=text("0")),
    Column("is_active", Boolean, nullable=False, server_default=text("true")),
    Column("created_at", TIMESTAMP(timezone=True), nullable=False, server_default=text("NOW()")),
    Column("created_by", String(100), nullable=False, server_default=text("'System'")),
    Column("updated_at", TIMESTAMP(timezone=True), nullable=False, server_default=text("NOW()")),
    Column("updated_by", String(100), nullable=False, server_default=text("'System'")),
)

serviceOrderTable = Table(
    "service_order", meta,
    Column("service_order_id", UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")),
    Column("order_no", String(20), nullable=False, unique=True, server_default=text("next_service_order_no()")),
    Column("customer_name", String(100), nullable=False), Column("customer_phone", String(20), nullable=False),
    Column("address", String(500), nullable=False), Column("problem_description", String(2000), nullable=False),
    Column("service_type_id", UUID(as_uuid=True), ForeignKey("service_type.service_type_id", ondelete="RESTRICT"), nullable=False, index=True),
    Column("quoted_price", Numeric(10, 2), nullable=False),
    Column("assigned_technician_id", UUID(as_uuid=True), ForeignKey("user.user_id", ondelete="RESTRICT")),
    Column("admin_notes", String(2000)),
    Column("status", String(20), nullable=False),
    Column("status_changed_at", TIMESTAMP(timezone=True), nullable=False, server_default=text("NOW()")),
    Column("started_at", TIMESTAMP(timezone=True)), Column("job_done_at", TIMESTAMP(timezone=True)),
    Column("reviewed_at", TIMESTAMP(timezone=True)),
    Column("reviewed_by_id", UUID(as_uuid=True), ForeignKey("user.user_id", ondelete="RESTRICT")),
    Column("closed_at", TIMESTAMP(timezone=True)),
    Column("closed_by_id", UUID(as_uuid=True), ForeignKey("user.user_id", ondelete="RESTRICT")),
    Column("created_by_id", UUID(as_uuid=True), ForeignKey("user.user_id", ondelete="RESTRICT"), nullable=False),
    Column("created_at", TIMESTAMP(timezone=True), nullable=False, server_default=text("NOW()")),
    Column("created_by", String(100), nullable=False, server_default=text("'System'")),
    Column("updated_at", TIMESTAMP(timezone=True), nullable=False, server_default=text("NOW()")),
    Column("updated_by", String(100), nullable=False, server_default=text("'System'")),
)

orderAttachmentTable = Table(
    "order_attachment", meta,
    Column("order_attachment_id", UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")),
    Column("service_order_id", UUID(as_uuid=True), ForeignKey("service_order.service_order_id", ondelete="RESTRICT"), nullable=False),
    Column("kind", String(20), nullable=False),
    Column("storage_path", String(300), nullable=False, unique=True), Column("file_name", String(255), nullable=False),
    Column("content_type", String(100), nullable=False), Column("size_bytes", BigInteger, nullable=False),
    Column("status", String(20), nullable=False, server_default=text("'pending'")),
    Column("uploaded_by_id", UUID(as_uuid=True), ForeignKey("user.user_id", ondelete="RESTRICT"), nullable=False),
    Column("confirmed_at", TIMESTAMP(timezone=True)),
    Column("created_at", TIMESTAMP(timezone=True), nullable=False, server_default=text("NOW()")),
    Column("created_by", String(100), nullable=False, server_default=text("'System'")),
    Column("updated_at", TIMESTAMP(timezone=True), nullable=False, server_default=text("NOW()")),
    Column("updated_by", String(100), nullable=False, server_default=text("'System'")),
)

orderCompletionTable = Table(
    "order_completion", meta,
    Column("order_completion_id", UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")),
    Column("service_order_id", UUID(as_uuid=True), ForeignKey("service_order.service_order_id", ondelete="RESTRICT"), nullable=False, unique=True),
    Column("technician_id", UUID(as_uuid=True), ForeignKey("user.user_id", ondelete="RESTRICT"), nullable=False),
    Column("work_done", String(2000), nullable=False),
    Column("quoted_price", Numeric(10, 2), nullable=False),
    Column("extra_charges", Numeric(10, 2), nullable=False, server_default=text("0")),
    Column("final_amount", Numeric(10, 2), nullable=False),
    Column("remarks", String(2000)),
    Column("payment_amount", Numeric(10, 2)), Column("payment_method", String(20)),
    Column("receipt_attachment_id", UUID(as_uuid=True), ForeignKey("order_attachment.order_attachment_id", ondelete="RESTRICT")),
    Column("completed_at", TIMESTAMP(timezone=True), nullable=False, server_default=text("NOW()")),
    Column("created_at", TIMESTAMP(timezone=True), nullable=False, server_default=text("NOW()")),
    Column("created_by", String(100), nullable=False, server_default=text("'System'")),
    Column("updated_at", TIMESTAMP(timezone=True), nullable=False, server_default=text("NOW()")),
    Column("updated_by", String(100), nullable=False, server_default=text("'System'")),
)

orderEventTable = Table(
    "order_event", meta,
    Column("order_event_id", UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")),
    Column("service_order_id", UUID(as_uuid=True), ForeignKey("service_order.service_order_id", ondelete="RESTRICT"), nullable=False),
    Column("event_type", String(40), nullable=False),
    Column("from_status", String(20)), Column("to_status", String(20)),
    Column("actor_id", UUID(as_uuid=True), ForeignKey("user.user_id", ondelete="RESTRICT"), nullable=False),
    Column("request_id", String(100)),
    Column("detail", JSONB, nullable=False, server_default=text("'{}'::jsonb")),
    Column("created_at", TIMESTAMP(timezone=True), nullable=False, server_default=text("NOW()")),
    Column("created_by", String(100), nullable=False, server_default=text("'System'")),
)

notificationTable = Table(
    "notification", meta,
    Column("notification_id", UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")),
    Column("service_order_id", UUID(as_uuid=True), ForeignKey("service_order.service_order_id", ondelete="RESTRICT"), nullable=False),
    Column("notification_type", String(40), nullable=False),
    Column("channel", String(20), nullable=False, server_default=text("'whatsapp'")),
    Column("provider", String(30), nullable=False, server_default=text("'deeplink'")),
    Column("recipient_type", String(20), nullable=False),
    Column("recipient_user_id", UUID(as_uuid=True), ForeignKey("user.user_id", ondelete="RESTRICT")),
    Column("recipient_name", String(100), nullable=False), Column("recipient_phone", String(20), nullable=False),
    Column("order_no", String(20), nullable=False),
    Column("sender_user_id", UUID(as_uuid=True), ForeignKey("user.user_id", ondelete="RESTRICT")),
    Column("template_data", JSONB, nullable=False),
    Column("message", String(4000)), Column("deep_link", String(8000)),
    Column("status", String(20), nullable=False, server_default=text("'queued'")),
    Column("provider_message_id", String(100)), Column("error_message", String(500)),
    Column("ready_at", TIMESTAMP(timezone=True)), Column("opened_at", TIMESTAMP(timezone=True)),
    Column("opened_by_id", UUID(as_uuid=True), ForeignKey("user.user_id", ondelete="RESTRICT")),
    Column("sent_at", TIMESTAMP(timezone=True)),
    Column("request_id", String(100)),
    Column("created_at", TIMESTAMP(timezone=True), nullable=False, server_default=text("NOW()")),
    Column("created_by", String(100), nullable=False, server_default=text("'System'")),
    Column("updated_at", TIMESTAMP(timezone=True), nullable=False, server_default=text("NOW()")),
    Column("updated_by", String(100), nullable=False, server_default=text("'System'")),
)

# Rewrites a plain Postgres URL onto the psycopg driver SQLAlchemy is configured for.
def psycopgUrl(url):
    for scheme in config.POSTGRES_SCHEMES:
        if url.startswith(scheme):
            return "postgresql+psycopg://" + url[len(scheme):]
    return url

# Sets the per-session timeouts on a new raw connection, because the Supabase pooler drops
# them when they arrive as startup options.
def applySessionTimeouts(dbapiConnection, connectionRecord):
    autocommit = dbapiConnection.autocommit
    dbapiConnection.autocommit = True
    with dbapiConnection.cursor() as cursor:
        cursor.execute("SELECT set_config('statement_timeout', %s, false)", (str(STATEMENT_TIMEOUT_MS),))
        cursor.execute("SELECT set_config('lock_timeout', %s, false)", (str(LOCK_TIMEOUT_MS),))
    dbapiConnection.autocommit = autocommit

# Builds an encrypted, bounded engine for one URL and password with the session timeouts applied.
def buildEngine(url, password, poolSize=POOL_SIZE, maxOverflow=MAX_OVERFLOW, prePing=True):
    engine = create_engine(
        psycopgUrl(url),
        connect_args={
            "password": password,
            "sslmode": "require",
            "connect_timeout": CONNECT_TIMEOUT_SECONDS,
            "prepare_threshold": None,
        },
        pool_pre_ping=prePing, pool_size=poolSize, max_overflow=maxOverflow, pool_timeout=POOL_TIMEOUT_SECONDS,
    )
    event.listen(engine, "connect", applySessionTimeouts)
    return engine

# Returns the shared application engine, built once from configuration.
def getEngine():
    global _engine
    if _engine is None:
        with _engineLock:
            if _engine is None:
                _engine = buildEngine(config.databaseUrl(), config.databasePassword())
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

# Opens one connection for reads.
def connection():
    return getEngine().connect()

# Raises when the database does not answer a trivial query.
def ping():
    with connection() as conn:
        conn.execute(text("SELECT 1"))

# Returns the ILIKE pattern matching a search term anywhere, with its wildcards taken literally.
def containsPattern(search):
    escaped = search.replace(LIKE_ESCAPE, LIKE_ESCAPE * 2).replace("%", LIKE_ESCAPE + "%").replace("_", LIKE_ESCAPE + "_")
    return f"%{escaped}%"

# Runs one read on the caller's connection, or on its own one with the rows already fetched.
def runRead(statement, conn=None):
    if conn is not None:
        return conn.execute(statement)
    with connection() as ownConn:
        return ownConn.execute(statement).freeze()()

# Returns the first row of a read as a plain dict, or None.
def readOne(statement, conn=None):
    row = runRead(statement, conn).mappings().first()
    return dict(row) if row is not None else None

# Returns every row of a read as plain dicts.
def readAll(statement, conn=None):
    return [dict(row) for row in runRead(statement, conn).mappings().all()]

# Returns the single value of a read.
def readScalar(statement, conn=None):
    return runRead(statement, conn).scalar_one()

# Runs one write in the caller's transaction, or in its own one, and returns the rows it touched.
def runWrite(statement, conn=None):
    if conn is not None:
        return conn.execute(statement).rowcount
    with transaction() as ownConn:
        return ownConn.execute(statement).rowcount

# Runs a write that may break a mapped unique constraint and returns (value, conflict), where the
# value is the RETURNING scalar or the row count; a savepoint keeps the caller's transaction usable.
def runUniqueWrite(statement, conflicts, conn=None):
    try:
        if conn is not None:
            with conn.begin_nested():
                return writtenValue(conn.execute(statement)), None
        with transaction() as ownConn:
            return writtenValue(ownConn.execute(statement)), None
    except ConflictError as error:
        violated = error.orig if isinstance(error.orig, UniqueViolation) else None
        constraint = violated.diag.constraint_name if violated is not None else None
        if constraint not in conflicts:
            raise
        return None, conflicts[constraint]

# Returns the RETURNING scalar of a write result, or its row count when it returns no rows.
def writtenValue(result):
    return result.scalar_one() if result.returns_rows else result.rowcount


__all__ = [
    "ConflictError",
    "DatabaseError",
    "applySessionTimeouts",
    "buildEngine",
    "connection",
    "containsPattern",
    "disposeEngine",
    "getEngine",
    "jobTable",
    "llmInvocationTable",
    "llmModelTable",
    "meta",
    "ping",
    "psycopgUrl",
    "readAll",
    "readOne",
    "readScalar",
    "roleTable",
    "runRead",
    "runUniqueWrite",
    "runWrite",
    "sessionTable",
    "settingTable",
    "tokenUsageTable",
    "transaction",
    "userTable",
]

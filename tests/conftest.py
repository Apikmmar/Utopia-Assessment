import os
import sys
import uuid
from functools import partial
from pathlib import Path
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import event, text
from api.main import createApp
from core import config
from core import db as coreDb
from core.crypto import hashPassword
from db.migration import runSql
from tests.support import ORIGIN, STATE_HEADERS, STRONG_PASSWORD, schemaMigrations

TEST_LEVELS = ("unit", "integration", "db")
TESTS_DIRECTORY = Path(__file__).resolve().parent
RUN_DB_TESTS = "RUN_DB_TESTS"
TEST_DATABASE_URL = "TEST_DATABASE_URL"
TEST_DATABASE_PASSWORD = "TEST_DATABASE_PASSWORD"
SCHEMA_PREFIX = "utopia_test_"
QUARANTINE_SCHEMA = SCHEMA_PREFIX + "none"
DEFAULTED_SETTINGS = (
    "AUTH_SESSION_HOURS", "AUTH_COOKIE_NAME", "AUTH_ARGON2_MEMORY_KIB", "AUTH_ARGON2_ITERATIONS",
    "STORAGE_BUCKET", "STORAGE_VIEW_URL_SECONDS", "WORKER_POLL_SECONDS", "WORKER_EMBEDDED",
)
TEST_POOL_SIZE = 3
TEST_MAX_OVERFLOW = 5

activeSchema = {"name": QUARANTINE_SCHEMA}

# Marks every test by the folder it lives in, so `pytest -m unit` needs no per-test decorator.
def pytest_collection_modifyitems(items):
    for item in items:
        parts = Path(item.path).resolve().relative_to(TESTS_DIRECTORY).parts
        for level in TEST_LEVELS:
            if level in parts:
                item.add_marker(getattr(pytest.mark, level))

# Pins the settings every test relies on, so a developer's backend/.env cannot change the expectations.
@pytest.fixture(autouse=True)
def appEnvironment(monkeypatch):
    monkeypatch.setenv("APP_ALLOWED_ORIGIN", ORIGIN)
    monkeypatch.setenv("AUTH_COOKIE_SECURE", "false")
    for name in DEFAULTED_SETTINGS:
        monkeypatch.delenv(name, raising=False)

# Points a pooled connection at the active test schema when it last served another one.
def pointAtActiveSchema(dbapiConnection, connectionRecord, connectionProxy):
    schema = activeSchema["name"]
    if connectionRecord.info.get("searchPath") == schema:
        return
    autocommit = dbapiConnection.autocommit
    dbapiConnection.autocommit = True
    with dbapiConnection.cursor() as cursor:
        cursor.execute("SELECT set_config('search_path', %s, false)", (schema,))
    dbapiConnection.autocommit = autocommit
    connectionRecord.info["searchPath"] = schema

# One engine for the whole run, skipped unless RUN_DB_TESTS=1. It targets TEST_DATABASE_URL and
# TEST_DATABASE_PASSWORD, falling back to DATABASE_URL and DATABASE_PASSWORD from backend/.env.
@pytest.fixture(scope="session")
def testEngine():
    if os.getenv(RUN_DB_TESTS) != "1":
        pytest.skip(f"Set {RUN_DB_TESTS}=1 to run PostgreSQL-backed checks in a throwaway schema")
    url = os.getenv(TEST_DATABASE_URL) or config.databaseUrl()
    password = os.getenv(TEST_DATABASE_PASSWORD) or config.databasePassword()
    engine = coreDb.buildEngine(url, password, poolSize=TEST_POOL_SIZE, maxOverflow=TEST_MAX_OVERFLOW, prePing=False)
    event.listen(engine, "checkout", pointAtActiveSchema)
    yield engine
    engine.dispose()

# A fresh empty schema per test with every getEngine pointed at it, dropped afterwards.
@pytest.fixture
def testSchema(testEngine, monkeypatch):
    schema = SCHEMA_PREFIX + uuid.uuid4().hex
    original = coreDb.getEngine
    for module in list(sys.modules.values()):
        if getattr(module, "getEngine", None) is original:
            monkeypatch.setattr(module, "getEngine", lambda: testEngine)
    with testEngine.begin() as conn:
        conn.execute(text(f"CREATE SCHEMA {schema}"))
    activeSchema["name"] = schema
    try:
        yield schema
    finally:
        activeSchema["name"] = QUARANTINE_SCHEMA
        with testEngine.begin() as conn:
            conn.execute(text(f"DROP SCHEMA IF EXISTS {schema} CASCADE"))

# The throwaway schema with every repository migration applied in one round trip.
@pytest.fixture
def appDb(testEngine, testSchema):
    with testEngine.begin() as conn:
        runSql(conn, "\n".join(migration.up for migration in schemaMigrations(testSchema)))
    return testEngine

# Inserts one user with a hashed password, or none when password is None, and returns its id.
def insertSeedUser(engine, email, roleCode="technician", password=STRONG_PASSWORD, name="Seed User", phone=None):
    passwordHash = hashPassword(password) if password is not None else None
    with engine.begin() as conn:
        return conn.execute(
            text(
                'INSERT INTO "user" (name, email, phone, role_id, password_hash, created_by, updated_by) '
                "SELECT :name, :email, :phone, role_id, :passwordHash, 'test', 'test' FROM role WHERE role_code = :roleCode "
                "RETURNING user_id"
            ),
            {"name": name, "email": email, "phone": phone, "passwordHash": passwordHash, "roleCode": roleCode},
        ).scalar_one()

# Runs one query against the test schema and returns its single value.
def selectScalar(engine, sql, **params):
    with engine.connect() as conn:
        return conn.execute(text(sql), params).scalar_one()

# Runs one statement against the test schema in its own transaction.
def executeSql(engine, sql, **params):
    with engine.begin() as conn:
        conn.execute(text(sql), params)

# Returns a client that logged in through the real login route.
def loginClient(app, email, password=STRONG_PASSWORD):
    client = TestClient(app)
    response = client.post("/auth/login", json={"email": email, "password": password}, headers=STATE_HEADERS)
    assert response.status_code == 200, response.text
    return client

# Seeds users in the test schema.
@pytest.fixture
def seedUser(appDb):
    return partial(insertSeedUser, appDb)

# Reads one value from the test schema.
@pytest.fixture
def scalar(appDb):
    return partial(selectScalar, appDb)

# Writes directly to the test schema, bypassing the application.
@pytest.fixture
def execute(appDb):
    return partial(executeSql, appDb)

# The real application built by its factory.
@pytest.fixture
def app():
    return createApp()

# Logs a fresh client in as the given user.
@pytest.fixture
def loggedIn(app):
    return partial(loginClient, app)

# Replaces the storage client with an in-memory fake; tests using it are labelled as mocked storage.
@pytest.fixture
def fakeStorage(monkeypatch):
    from core import storage as coreStorage
    from tests.order_support import FakeStorage
    fake = FakeStorage()
    monkeypatch.setattr(coreStorage, "getStorage", lambda: fake)
    return fake

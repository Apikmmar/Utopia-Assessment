from dataclasses import replace
import pytest
from sqlalchemy import text
from core.db import DatabaseError
from db.migration import HISTORY_MIGRATION, acquireMigrationLock, applyPending, getHistory, loadMigrations, rollbackLatest
from tests.support import schemaMigrations

APPLICATION_TABLES = ("token_usage", "llm_model", "setting", "llm_invocation", "role", "user", "job", "session",
    "service_type", "service_order", "order_attachment", "order_completion", "order_event", "notification",
)


# One connection inside an outer transaction on the throwaway schema, rolled back afterwards.
@pytest.fixture
def conn(testEngine, testSchema):
    connection = testEngine.connect()
    outer = connection.begin()
    try:
        yield connection
    finally:
        outer.rollback()
        connection.close()

# The repository migrations pointed at the throwaway schema.
@pytest.fixture
def repoMigrations(testSchema):
    return schemaMigrations(testSchema)

# Writes test migrations into a temporary directory that tables land in the throwaway schema from.
@pytest.fixture
def writeMigration(tmp_path):
    return lambda name, up, down: (tmp_path / name).write_text(f"-- migrate:up\n{up}\n-- migrate:down\n{down}\n", encoding="utf-8")

# Returns the history baseline followed by the temporary test migrations.
@pytest.fixture
def withBaseline(conn, repoMigrations, testSchema, tmp_path):
    baseline = [migration for migration in repoMigrations if migration.name == HISTORY_MIGRATION]
    applyPending(conn, baseline, schema=testSchema)
    return lambda: baseline + loadMigrations(tmp_path)

# Returns whether a table exists in the throwaway schema.
def tableExists(conn, schema, name):
    return conn.execute(text("SELECT to_regclass(:name)"), {"name": f'{schema}."{name}"'}).scalar() is not None

# Every repository migration applies into an empty schema, and a second run is a no-op.
def testRepositoryMigrationsApplyThenRerunIsNoop(conn, repoMigrations, testSchema):
    names = [migration.name for migration in repoMigrations]
    assert applyPending(conn, repoMigrations, schema=testSchema) == names
    assert applyPending(conn, repoMigrations, schema=testSchema) == []
    assert all(tableExists(conn, testSchema, table) for table in APPLICATION_TABLES)
    assert conn.execute(text("SELECT count(*) FROM role")).scalar_one() == 3

# Rolling back one by one runs each down section in reverse order, stops at the history table, and reapplies cleanly.
def testRepositoryMigrationsRollBackInReverseAndReapply(conn, repoMigrations, testSchema):
    applyPending(conn, repoMigrations, schema=testSchema)
    rolledBack = []
    while len(getHistory(conn, testSchema)) > 1:
        rolledBack.extend(rollbackLatest(conn, repoMigrations, schema=testSchema))
    assert rolledBack == [migration.name for migration in repoMigrations[1:]][::-1]
    assert not any(tableExists(conn, testSchema, table) for table in APPLICATION_TABLES)
    with pytest.raises(ValueError):
        rollbackLatest(conn, repoMigrations, schema=testSchema)
    assert applyPending(conn, repoMigrations, schema=testSchema) == rolledBack[::-1]

# Rollback follows execution order rather than the newest migration file on disk.
def testReversesOnlyLatestAppliedMigration(conn, testSchema, withBaseline, writeMigration):
    writeMigration("9997_first.sql", "CREATE TABLE migration_first (id int);", "DROP TABLE migration_first;")
    writeMigration("9998_second.sql", "CREATE TABLE migration_second (id int);", "DROP TABLE migration_second;")
    assert applyPending(conn, withBaseline(), schema=testSchema) == ["9997_first.sql", "9998_second.sql"]
    writeMigration("9999_unapplied.sql", "CREATE TABLE migration_unapplied (id int);", "DROP TABLE migration_unapplied;")
    assert rollbackLatest(conn, withBaseline(), schema=testSchema) == ["9998_second.sql"]
    assert tableExists(conn, testSchema, "migration_first")
    assert not tableExists(conn, testSchema, "migration_second")
    assert not tableExists(conn, testSchema, "migration_unapplied")
    assert rollbackLatest(conn, withBaseline(), schema=testSchema) == ["9997_first.sql"]
    assert [name for name, _ in getHistory(conn, testSchema)] == [HISTORY_MIGRATION]

# Failed forward SQL leaves neither its table nor its history record behind.
def testFailedMigrationPreservesPriorState(conn, testSchema, withBaseline, writeMigration):
    writeMigration("9998_before_failure.sql", "CREATE TABLE migration_before_failure (id int);", "DROP TABLE migration_before_failure;")
    writeMigration("9999_failed.sql", "CREATE TABLE migration_failed (id int); SELECT 1 / 0;", "DROP TABLE migration_failed;")
    baseline = getHistory(conn, testSchema)
    with pytest.raises(DatabaseError):
        with conn.begin_nested():
            applyPending(conn, withBaseline(), schema=testSchema)
    assert not tableExists(conn, testSchema, "migration_failed")
    assert not tableExists(conn, testSchema, "migration_before_failure")
    assert getHistory(conn, testSchema) == baseline

# Failed reverse SQL restores both the dropped table and the applied history record.
def testFailedRollbackPreservesAppliedState(conn, testSchema, withBaseline, writeMigration):
    writeMigration("9999_failed_down.sql", "CREATE TABLE migration_failed_down (id int);", "DROP TABLE migration_failed_down; SELECT 1 / 0;")
    applyPending(conn, withBaseline(), schema=testSchema)
    history = getHistory(conn, testSchema)
    with pytest.raises(DatabaseError):
        with conn.begin_nested():
            rollbackLatest(conn, withBaseline(), schema=testSchema)
    assert tableExists(conn, testSchema, "migration_failed_down")
    assert getHistory(conn, testSchema) == history

# Reverse SQL never runs when its applied source is missing or has changed.
def testMissingOrChangedMigrationCannotBeReversed(conn, testSchema, withBaseline, writeMigration):
    writeMigration("9999_integrity.sql", "CREATE TABLE migration_integrity (id int);", "DROP TABLE migration_integrity;")
    migrations = withBaseline()
    applyPending(conn, migrations, schema=testSchema)
    changed = migrations[:-1] + [replace(migrations[-1], checksum="changed")]
    for available in (changed, migrations[:-1]):
        with pytest.raises(ValueError):
            rollbackLatest(conn, available, schema=testSchema)
        with pytest.raises(ValueError):
            applyPending(conn, available, schema=testSchema)
    assert tableExists(conn, testSchema, "migration_integrity")

# The history table migration stays applied whatever its reverse SQL contains.
def testHistoryMigrationCannotBeReversed(conn, testSchema, withBaseline):
    baseline = getHistory(conn, testSchema)
    with pytest.raises(ValueError):
        rollbackLatest(conn, withBaseline(), schema=testSchema)
    assert getHistory(conn, testSchema) == baseline == [(HISTORY_MIGRATION, baseline[0][1])]

# Both preview modes leave tables and migration history unchanged.
def testPreviewsDoNotApplyOrReverseSql(conn, testSchema, withBaseline, writeMigration):
    writeMigration("9999_preview.sql", "CREATE TABLE migration_preview (id int);", "DROP TABLE migration_preview;")
    baseline = getHistory(conn, testSchema)
    assert applyPending(conn, withBaseline(), dryRun=True, schema=testSchema) == ["9999_preview.sql"]
    assert not tableExists(conn, testSchema, "migration_preview")
    assert getHistory(conn, testSchema) == baseline
    applyPending(conn, withBaseline(), schema=testSchema)
    history = getHistory(conn, testSchema)
    assert rollbackLatest(conn, withBaseline(), dryRun=True, schema=testSchema) == ["9999_preview.sql"]
    assert tableExists(conn, testSchema, "migration_preview")
    assert getHistory(conn, testSchema) == history

# A second migration command is refused while another holds the lock.
def testMigrationLockIsExclusive(testEngine, testSchema):
    with testEngine.connect() as first, testEngine.connect() as second:
        with first.begin():
            acquireMigrationLock(first)
            with second.begin(), pytest.raises(ValueError):
                acquireMigrationLock(second)

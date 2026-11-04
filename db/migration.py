import argparse
import hashlib
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

BACKEND_DIRECTORY = str(Path(__file__).resolve().parents[1] / "backend")
if BACKEND_DIRECTORY not in sys.path:
    sys.path.insert(0, BACKEND_DIRECTORY)

from sqlalchemy import Connection, text
from core.db import DatabaseError, transaction

MIGRATIONS_DIRECTORY = Path(__file__).resolve().parent / "migrations"
MIGRATION_LOCK = 2026110301
HISTORY_MIGRATION = "0001_schema_migrations.sql"
DEFAULT_SCHEMA = "public"
SCHEMA_NAME_PATTERN = re.compile(r"[a-z_][a-z0-9_]*")
UP_MARKER = "-- migrate:up\n"
DOWN_MARKER = "-- migrate:down\n"


@dataclass(frozen=True)
class Migration:
    name: str
    checksum: str
    up: str
    down: str


# Reads forward and reverse SQL from each migration, with a checksum for change detection.
def loadMigrations(directory: Path = MIGRATIONS_DIRECTORY) -> list[Migration]:
    migrations = []
    for path in sorted(directory.glob("*.sql")):
        content = path.read_text(encoding="utf-8")
        prefix, upMarker, remainder = content.partition(UP_MARKER)
        up, downMarker, down = remainder.partition(DOWN_MARKER)
        if (
            prefix.strip()
            or not upMarker
            or not downMarker
            or content.count(UP_MARKER) != 1
            or content.count(DOWN_MARKER) != 1
            or not up.strip()
            or not down.strip()
        ):
            raise ValueError(f"{path.name} must contain one nonempty migrate:up and migrate:down section.")
        migrations.append(Migration(path.name, hashlib.sha256(content.encode("utf-8")).hexdigest(), up, down))
    return migrations


# Returns the schema-qualified history table name, refusing anything but a plain lowercase identifier.
def historyTable(schema: str) -> str:
    if not SCHEMA_NAME_PATTERN.fullmatch(schema):
        raise ValueError(f"Invalid schema name: {schema}.")
    return f"{schema}.schema_migrations"


# Runs migration SQL verbatim, so colons and percent signs are never read as parameters.
def runSql(connection: Connection, sql: str) -> None:
    connection.execution_options(no_parameters=True).exec_driver_sql(sql)


# Serializes migration commands without waiting indefinitely for another process.
def acquireMigrationLock(connection: Connection) -> None:
    locked = connection.execute(text("SELECT pg_try_advisory_xact_lock(:lock)"), {"lock": MIGRATION_LOCK}).scalar()
    if not locked:
        raise ValueError("Another migration command is running. Try again after it finishes.")


# Reads execution order from the database rather than inferring it from local files.
def getHistory(connection: Connection, schema: str = DEFAULT_SCHEMA) -> list[tuple[str, str]]:
    table = historyTable(schema)
    if connection.execute(text("SELECT to_regclass(:name)"), {"name": table}).scalar() is None:
        return []
    rows = connection.execute(text(f"SELECT name, checksum FROM {table} ORDER BY id"))
    return [(row[0], row[1]) for row in rows]


# Applies pending SQL and its history records within the caller's transaction.
def applyPending(connection: Connection, migrations: list[Migration], *, dryRun: bool = False, schema: str = DEFAULT_SCHEMA) -> list[str]:
    history = dict(getHistory(connection, schema))
    available = {migration.name: migration for migration in migrations}
    for name, checksum in history.items():
        if name not in available or available[name].checksum != checksum:
            raise ValueError(f"Applied migration is missing or changed: {name}.")
    pending = [migration for migration in migrations if migration.name not in history]
    if pending and not dryRun:
        insert = text(f"INSERT INTO {historyTable(schema)} (name, checksum) VALUES (:name, :checksum)")
        for migration in pending:
            runSql(connection, migration.up)
            connection.execute(insert, {"name": migration.name, "checksum": migration.checksum})
    return [migration.name for migration in pending]


# Reverses only the last applied migration using its own SQL, then removes its history record.
def rollbackLatest(connection: Connection, migrations: list[Migration], *, dryRun: bool = False, schema: str = DEFAULT_SCHEMA) -> list[str]:
    history = getHistory(connection, schema)
    if not history:
        return []
    name, checksum = history[-1]
    if name == HISTORY_MIGRATION:
        raise ValueError(f"{name} creates the migration history table and cannot be rolled back.")
    migration = next((item for item in migrations if item.name == name), None)
    if migration is None or migration.checksum != checksum:
        raise ValueError(f"Applied migration is missing or changed: {name}.")
    if not dryRun:
        runSql(connection, migration.down)
        connection.execute(text(f"DELETE FROM {historyTable(schema)} WHERE name = :name"), {"name": name})
    return [name]


# Commits schema and history together; previews leave both unchanged.
def runCommand(direction: Literal["up", "down"]) -> int:
    action = "apply pending migrations" if direction == "up" else "roll back the last applied migration"
    parser = argparse.ArgumentParser(description=f"{action.capitalize()} using db/migrations/*.sql.")
    parser.add_argument("--dry-run", action="store_true", help="Preview without changing the database.")
    args = parser.parse_args()
    try:
        migrations = loadMigrations()
        with transaction() as connection:
            acquireMigrationLock(connection)
            operation = applyPending if direction == "up" else rollbackLatest
            names = operation(connection, migrations, dryRun=args.dry_run)
        if not names:
            print("No pending migrations." if direction == "up" else "No applied migrations to roll back.")
        else:
            label = "Would apply" if direction == "up" else "Would roll back"
            if not args.dry_run:
                label = "Applied" if direction == "up" else "Rolled back"
            for name in names:
                print(f"{label}: {name}")
        return 0
    except (ValueError, OSError, RuntimeError) as error:
        print(str(error))
    except DatabaseError as error:
        sqlstate = getattr(getattr(error, "orig", None), "sqlstate", None)
        print(f"Migration failed ({type(error).__name__}, SQLSTATE: {sqlstate or 'unavailable'}).")
        print("No changes committed.")
    return 1


# Runs pending migrations through the shared transactional runner.
def main() -> int:
    return runCommand("up")


if __name__ == "__main__":
    raise SystemExit(main())

__all__ = [
    "DEFAULT_SCHEMA",
    "HISTORY_MIGRATION",
    "MIGRATIONS_DIRECTORY",
    "Migration",
    "acquireMigrationLock",
    "applyPending",
    "getHistory",
    "historyTable",
    "loadMigrations",
    "main",
    "rollbackLatest",
    "runCommand",
    "runSql",
]

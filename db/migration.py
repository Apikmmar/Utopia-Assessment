import argparse
import hashlib
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from sqlalchemy import Connection, text

from backend.core.db import DatabaseError, transaction

MIGRATIONS_DIRECTORY = Path(__file__).resolve().parent / "migrations"
MIGRATION_LOCK = 2026110301


@dataclass(frozen=True)
class Migration:
    name: str
    checksum: str
    up: str
    down: str


# Read forward and reverse SQL from each migration, with a checksum for change detection.
def load_migrations(directory: Path = MIGRATIONS_DIRECTORY) -> list[Migration]:
    migrations = []
    for path in sorted(directory.glob("*.sql")):
        content = path.read_text(encoding="utf-8")
        prefix, up_marker, remainder = content.partition("-- migrate:up\n")
        up, down_marker, down = remainder.partition("-- migrate:down\n")
        if (
            prefix.strip()
            or not up_marker
            or not down_marker
            or content.count("-- migrate:up\n") != 1
            or content.count("-- migrate:down\n") != 1
            or not up.strip()
            or not down.strip()
        ):
            raise ValueError(f"{path.name} must contain one nonempty migrate:up and migrate:down section.")
        migrations.append(
            Migration(path.name, hashlib.sha256(content.encode("utf-8")).hexdigest(), up, down)
        )
    return migrations


# Run migration SQL verbatim, so colons and percent signs are never read as parameters.
def run_sql(connection: Connection, sql: str) -> None:
    connection.execution_options(no_parameters=True).exec_driver_sql(sql)


# Serialize migration commands without waiting indefinitely for another process.
def acquire_migration_lock(connection: Connection) -> None:
    locked = connection.execute(
        text("SELECT pg_try_advisory_xact_lock(:lock)"), {"lock": MIGRATION_LOCK}
    ).scalar()
    if not locked:
        raise ValueError("Another migration command is running. Try again after it finishes.")


# Keep applied migration records private from browser database roles.
def ensure_history(connection: Connection) -> None:
    run_sql(
        connection,
        "CREATE TABLE IF NOT EXISTS public.schema_migrations ("
        "id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY, "
        "name text NOT NULL UNIQUE, "
        "checksum text NOT NULL, "
        "applied_at timestamptz NOT NULL DEFAULT now()); "
        "ALTER TABLE public.schema_migrations ENABLE ROW LEVEL SECURITY; "
        "REVOKE ALL ON TABLE public.schema_migrations FROM anon, authenticated;",
    )


# Read execution order from the database rather than inferring it from local files.
def get_history(connection: Connection) -> list[tuple[str, str]]:
    exists = connection.execute(text("SELECT to_regclass('public.schema_migrations')")).scalar()
    if exists is None:
        return []
    rows = connection.execute(text("SELECT name, checksum FROM public.schema_migrations ORDER BY id"))
    return [(row[0], row[1]) for row in rows]


# Apply pending SQL and its history records within the caller's transaction.
def apply_pending(
    connection: Connection, migrations: list[Migration], *, dry_run: bool = False
) -> list[str]:
    history = dict(get_history(connection))
    available = {migration.name: migration for migration in migrations}
    for name, checksum in history.items():
        if name not in available or available[name].checksum != checksum:
            raise ValueError(f"Applied migration is missing or changed: {name}.")
    pending = [migration for migration in migrations if migration.name not in history]
    if pending and not dry_run:
        ensure_history(connection)
        for migration in pending:
            run_sql(connection, migration.up)
            connection.execute(
                text("INSERT INTO public.schema_migrations (name, checksum) VALUES (:name, :checksum)"),
                {"name": migration.name, "checksum": migration.checksum},
            )
    return [migration.name for migration in pending]


# Reverse only the last applied migration using its own SQL, then remove its history record.
def rollback_latest(
    connection: Connection, migrations: list[Migration], *, dry_run: bool = False
) -> list[str]:
    history = get_history(connection)
    if not history:
        return []
    name, checksum = history[-1]
    migration = next((item for item in migrations if item.name == name), None)
    if migration is None or migration.checksum != checksum:
        raise ValueError(f"Applied migration is missing or changed: {name}.")
    if not dry_run:
        run_sql(connection, migration.down)
        connection.execute(text("DELETE FROM public.schema_migrations WHERE name = :name"), {"name": name})
    return [name]


# Commit schema and history together; previews leave both unchanged.
def run_command(direction: Literal["up", "down"]) -> int:
    action = "apply pending migrations" if direction == "up" else "roll back the last applied migration"
    parser = argparse.ArgumentParser(description=f"{action.capitalize()} using db/migrations/*.sql.")
    parser.add_argument("--dry-run", action="store_true", help="Preview without changing the database.")
    args = parser.parse_args()
    try:
        migrations = load_migrations()
        with transaction() as connection:
            acquire_migration_lock(connection)
            operation = apply_pending if direction == "up" else rollback_latest
            names = operation(connection, migrations, dry_run=args.dry_run)
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


# Run pending migrations through the shared transactional runner.
def main() -> int:
    return run_command("up")


if __name__ == "__main__":
    raise SystemExit(main())

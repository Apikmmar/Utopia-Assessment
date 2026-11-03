import os
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path

from sqlalchemy import text

from backend.core.db import DatabaseError, connection
from db.migration import (
    HISTORY_MIGRATION,
    Migration,
    acquire_migration_lock,
    apply_pending,
    get_history,
    load_migrations,
    rollback_latest,
)


class MigrationFileTests(unittest.TestCase):
    # Preserve SQL function bodies while separating migration directions.
    def test_loads_both_directions_without_splitting_sql_statements(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "0001_example.sql"
            up = "CREATE FUNCTION example() RETURNS int LANGUAGE sql AS $$ SELECT 1; $$;\n"
            down = "DROP FUNCTION example();\n"
            path.write_text(f"-- migrate:up\n{up}-- migrate:down\n{down}", encoding="utf-8")
            migration = load_migrations(Path(directory))[0]
            self.assertEqual(migration.name, path.name)
            self.assertEqual(migration.up, up)
            self.assertEqual(migration.down, down)

    # Reject incomplete or ambiguous migration files before connecting to the database.
    def test_rejects_missing_empty_and_duplicate_sections(self) -> None:
        invalid = (
            "SELECT 1;",
            "-- migrate:up\nSELECT 1;\n-- migrate:down\n",
            "-- migrate:up\nSELECT 1;\n-- migrate:down\nSELECT 2;\n-- migrate:down\nSELECT 3;\n",
        )
        for content in invalid:
            with self.subTest(content=content), tempfile.TemporaryDirectory() as directory:
                (Path(directory) / "0001_bad.sql").write_text(content, encoding="utf-8")
                with self.assertRaises(ValueError):
                    load_migrations(Path(directory))


@unittest.skipUnless(
    os.environ.get("RUN_MIGRATION_INTEGRATION_TESTS") == "1",
    "Set RUN_MIGRATION_INTEGRATION_TESTS=1 for transactional PostgreSQL checks.",
)
class MigrationDatabaseTests(unittest.TestCase):
    # Isolate every test in a rolled-back transaction and use only temporary application tables.
    def setUp(self) -> None:
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.connection = connection()
        self.addCleanup(self.connection.close)
        outer = self.connection.begin()
        self.addCleanup(outer.rollback)
        acquire_migration_lock(self.connection)
        if not get_history(self.connection):
            bootstrap = [item for item in load_migrations() if item.name == HISTORY_MIGRATION]
            apply_pending(self.connection, bootstrap)
        self.baseline = get_history(self.connection)
        applied = dict(self.baseline)
        self.baseline_files = [migration for migration in load_migrations() if migration.name in applied]

    # Write test migrations only inside a temporary fixture directory.
    def write_migration(self, name: str, up: str, down: str) -> None:
        (Path(self.directory.name) / name).write_text(
            f"-- migrate:up\n{up}\n-- migrate:down\n{down}\n", encoding="utf-8"
        )

    # Include applied repository history without running any pending application migrations.
    def migrations(self) -> list[Migration]:
        return self.baseline_files + load_migrations(Path(self.directory.name))

    # Check a temporary relation through PostgreSQL's catalog.
    def table_exists(self, name: str) -> bool:
        result = self.connection.execute(text("SELECT to_regclass(:name)"), {"name": f"pg_temp.{name}"}).scalar()
        return result is not None

    # Roll back execution order rather than the newest migration file on disk.
    def test_reverses_only_latest_applied_migration(self) -> None:
        self.write_migration(
            "9997_first.sql", "CREATE TEMP TABLE migration_first (id int);", "DROP TABLE pg_temp.migration_first;"
        )
        self.write_migration(
            "9998_second.sql", "CREATE TEMP TABLE migration_second (id int);", "DROP TABLE pg_temp.migration_second;"
        )
        self.assertEqual(
            apply_pending(self.connection, self.migrations()), ["9997_first.sql", "9998_second.sql"]
        )
        self.assertEqual(apply_pending(self.connection, self.migrations()), [])
        self.write_migration(
            "9999_unapplied.sql",
            "CREATE TEMP TABLE migration_unapplied (id int);",
            "DROP TABLE pg_temp.migration_unapplied;",
        )
        self.assertEqual(rollback_latest(self.connection, self.migrations()), ["9998_second.sql"])
        self.assertTrue(self.table_exists("migration_first"))
        self.assertFalse(self.table_exists("migration_second"))
        self.assertFalse(self.table_exists("migration_unapplied"))
        self.assertEqual(rollback_latest(self.connection, self.migrations()), ["9997_first.sql"])
        self.assertEqual(get_history(self.connection), self.baseline)

    # Failed forward SQL must not leave either its table or its history record behind.
    def test_failed_migration_preserves_prior_state(self) -> None:
        self.write_migration(
            "9998_before_failure.sql",
            "CREATE TEMP TABLE migration_before_failure (id int);",
            "DROP TABLE pg_temp.migration_before_failure;",
        )
        self.write_migration(
            "9999_failed.sql",
            "CREATE TEMP TABLE migration_failed (id int); SELECT 1 / 0;",
            "DROP TABLE pg_temp.migration_failed;",
        )
        with self.assertRaises(DatabaseError):
            with self.connection.begin_nested():
                apply_pending(self.connection, self.migrations())
        self.assertFalse(self.table_exists("migration_failed"))
        self.assertFalse(self.table_exists("migration_before_failure"))
        self.assertEqual(get_history(self.connection), self.baseline)

    # Failed reverse SQL must restore both the dropped table and the applied history record.
    def test_failed_rollback_preserves_applied_state(self) -> None:
        self.write_migration(
            "9999_failed_down.sql",
            "CREATE TEMP TABLE migration_failed_down (id int);",
            "DROP TABLE pg_temp.migration_failed_down; SELECT 1 / 0;",
        )
        apply_pending(self.connection, self.migrations())
        history = get_history(self.connection)
        with self.assertRaises(DatabaseError):
            with self.connection.begin_nested():
                rollback_latest(self.connection, self.migrations())
        self.assertTrue(self.table_exists("migration_failed_down"))
        self.assertEqual(get_history(self.connection), history)

    # Refuse to execute reverse SQL when its applied source is missing or has changed.
    def test_missing_or_changed_migration_cannot_be_reversed(self) -> None:
        self.write_migration(
            "9999_integrity.sql",
            "CREATE TEMP TABLE migration_integrity (id int);",
            "DROP TABLE pg_temp.migration_integrity;",
        )
        migrations = self.migrations()
        apply_pending(self.connection, migrations)
        changed = migrations[:-1] + [replace(migrations[-1], checksum="changed")]
        for available in (changed, migrations[:-1]):
            with self.subTest(available=available), self.assertRaises(ValueError):
                rollback_latest(self.connection, available)
        self.assertTrue(self.table_exists("migration_integrity"))

    # The history table migration must stay applied, whatever its reverse SQL contains.
    def test_history_migration_cannot_be_reversed(self) -> None:
        self.connection.execute(
            text("DELETE FROM public.schema_migrations WHERE name <> :name"), {"name": HISTORY_MIGRATION}
        )
        self.baseline = get_history(self.connection)
        with self.assertRaises(ValueError):
            rollback_latest(self.connection, self.migrations())
        self.assertEqual(get_history(self.connection), self.baseline)
        self.assertEqual([name for name, _ in self.baseline][:1], [HISTORY_MIGRATION])

    # Both preview modes must leave tables and migration history unchanged.
    def test_previews_do_not_apply_or_reverse_sql(self) -> None:
        self.write_migration(
            "9999_preview.sql", "CREATE TEMP TABLE migration_preview (id int);", "DROP TABLE pg_temp.migration_preview;"
        )
        migrations = self.migrations()
        self.assertEqual(apply_pending(self.connection, migrations, dry_run=True), ["9999_preview.sql"])
        self.assertFalse(self.table_exists("migration_preview"))
        self.assertEqual(get_history(self.connection), self.baseline)
        apply_pending(self.connection, migrations)
        history = get_history(self.connection)
        self.assertEqual(rollback_latest(self.connection, migrations, dry_run=True), ["9999_preview.sql"])
        self.assertTrue(self.table_exists("migration_preview"))
        self.assertEqual(get_history(self.connection), history)


if __name__ == "__main__":
    unittest.main()

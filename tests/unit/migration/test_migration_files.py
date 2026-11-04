from pathlib import Path
import pytest
from db.migration import HISTORY_MIGRATION, historyTable, loadMigrations

# Preserves SQL function bodies while separating migration directions.
def testLoadsBothDirectionsWithoutSplittingStatements(tmp_path):
    up = "CREATE FUNCTION example() RETURNS int LANGUAGE sql AS $$ SELECT 1; $$;\n"
    down = "DROP FUNCTION example();\n"
    (tmp_path / "0001_example.sql").write_text(f"-- migrate:up\n{up}-- migrate:down\n{down}", encoding="utf-8")
    migration = loadMigrations(tmp_path)[0]
    assert (migration.name, migration.up, migration.down) == ("0001_example.sql", up, down)

# Rejects incomplete or ambiguous migration files before connecting to the database.
@pytest.mark.parametrize("content", [
    "SELECT 1;",
    "-- migrate:up\nSELECT 1;\n-- migrate:down\n",
    "-- migrate:up\nSELECT 1;\n-- migrate:down\nSELECT 2;\n-- migrate:down\nSELECT 3;\n",
    "SELECT 0;\n-- migrate:up\nSELECT 1;\n-- migrate:down\nSELECT 2;\n",
])
def testRejectsMalformedFiles(tmp_path, content):
    (tmp_path / "0001_bad.sql").write_text(content, encoding="utf-8")
    with pytest.raises(ValueError):
        loadMigrations(tmp_path)

# Every repository migration parses, is numbered in order, and starts with the history table.
def testRepositoryMigrationsAreWellFormed():
    migrations = loadMigrations()
    names = [migration.name for migration in migrations]
    assert names[0] == HISTORY_MIGRATION
    assert names == sorted(names)
    assert all(Path(name).stem[:4].isdigit() for name in names)

# The history table is qualified by a plain schema name and anything else is refused.
@pytest.mark.parametrize("schema", ["Public", "a;b", "x.y", ""])
def testHistoryTableRejectsUnsafeSchema(schema):
    assert historyTable("public") == "public.schema_migrations"
    with pytest.raises(ValueError):
        historyTable(schema)

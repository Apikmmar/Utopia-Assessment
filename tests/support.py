from dataclasses import replace
from db.migration import loadMigrations

ORIGIN = "http://localhost:5173"
STATE_HEADERS = {"Origin": ORIGIN}
STRONG_PASSWORD = "correct-horse-battery-staple"
COOKIE = "utopia_session"
MISSING_ID = "00000000-0000-0000-0000-000000000000"
SOURCE_SCHEMA_QUALIFIER = "public."

# Returns the migrations with every public. qualifier pointed at the given schema, keeping the file checksums.
def schemaMigrations(schema):
    qualifier = f"{schema}."
    return [
        replace(migration, up=migration.up.replace(SOURCE_SCHEMA_QUALIFIER, qualifier), down=migration.down.replace(SOURCE_SCHEMA_QUALIFIER, qualifier))
        for migration in loadMigrations()
    ]


__all__ = ["COOKIE", "MISSING_ID", "ORIGIN", "STATE_HEADERS", "STRONG_PASSWORD", "schemaMigrations"]

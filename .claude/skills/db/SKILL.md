---
name: db
description: Write and review database schema, versioned SQL migrations, table definitions, connection and transaction code, and migration tooling in this repository's house style. Use for any change under db/ or backend/core/db.py; pair with the backend skill for services and the testing skill for verification.
---

# Database conventions

Keep schema changes versioned, reversible, and reviewable. Apply the shared standards in [AGENTS.md](../../../AGENTS.md) and the [backend](../backend/SKILL.md) and [testing](../testing/SKILL.md) skills. The current stack is PostgreSQL on Supabase, accessed from Python through SQLAlchemy with the psycopg driver; confirm against `backend/requirements.txt` and `zdocumentation/` before relying on that.

## Migrations

- Schema changes live only in `db/migrations/NNNN_name.sql`, numbered in execution order with four digits. Never change the schema by hand, from application code, or from a script outside this directory.
- Each file has exactly one nonempty `-- migrate:up` section followed by one nonempty `-- migrate:down` section, with nothing before the first marker. Keep SQL as plain statements; function bodies stay intact because files are never split on semicolons.
- Never edit a migration that has been applied anywhere. Applied files are checksummed, and a changed or missing file blocks every later run. Fix forward with a new numbered migration.
- `0001_schema_migrations.sql` creates the history table and is permanent. Its down section is a no-op and the rollback command refuses it. Never add SQL that drops `public.schema_migrations`.
- Make down SQL the exact inverse of up. Rollback reverses only the latest applied migration, by execution order rather than by file name.
- Run with `python -m db.migration` from the repository root, and preview first with `--dry-run`. Use `python -m db.rollback` to reverse the latest one. Migrations run in one transaction under an advisory lock, so schema and history commit together or not at all.
- Before applying to a shared or remote database, show the dry-run result and get the user's go-ahead.

## Table design

- Use `snake_case` singular table names and `snake_case` columns. Name the primary key `<table>_id`. Use `uuid` keys with `DEFAULT gen_random_uuid()` unless an existing natural key is required.
- Use `timestamptz` for time, `varchar(n)` for bounded text, `text` for unbounded text, `jsonb` for structured payloads, and explicit lengths on identifiers.
- Give audit columns `created_at timestamptz NOT NULL DEFAULT now()` and `created_by varchar(100) NOT NULL DEFAULT 'System'`. Add `updated_at` and `updated_by` for mutable rows.
- State constraints in the database: `NOT NULL`, `CHECK` for ranges and allowed values, foreign keys with an explicit `ON DELETE` choice, and unique constraints for real business keys. Do not rely on application code alone.
- Enable row level security on every table in `public` and revoke `anon` and `authenticated` access unless the browser is meant to reach it. The backend connects with its own credentials, so policies must be a deliberate decision, not an accident.
- Add indexes for measured or clearly structural access paths such as foreign keys and frequent filters. Avoid speculative indexes.

## Python access

- `backend/core/config.py` reads settings; `backend/core/db.py` owns one lazily built, thread-safe SQLAlchemy engine with a bounded pool, encrypted connections, and connect, statement, and lock timeouts. Do not open connections elsewhere.
- Define each table once in `backend/core/db.py` as a SQLAlchemy `Table` on the shared `meta`, named `<camelCase>Table`, matching its migration column for column. A migration and its `Table` change together.
- Use `transaction()` for writes, which commits on success and rolls back on error, and `connection()` for reads. The use case owns the transaction; repositories do not commit on their own.
- Bind every value as a parameter. Never build SQL by formatting strings. Run raw migration SQL only through the migration runner, which disables parameter parsing for it.
- Catch `DatabaseError` and `ConflictError` from `backend/core/db.py` rather than driver exceptions. Do not print URLs, passwords, or raw driver errors.
- Credentials come from `backend/.env` through config: `DATABASE_URL` for the Session pooler URI and `DATABASE_PASSWORD` for the password, which is passed separately so special characters survive. Never commit or print either.

## Verify

- Unit-test migration parsing and rules without a database. Run engine-specific behavior, such as transactions, locking, and constraints, against real PostgreSQL inside a rolled-back transaction with temporary tables, enabled by `RUN_MIGRATION_INTEGRATION_TESTS=1`.
- When adding a migration, confirm that down reverses up, that a second `python -m db.migration` is a no-op, and that the matching `Table` columns agree with the SQL.
- Follow the comment rule from the testing skill: one concise comment above each function, at most two lines, with no inline comments or docstrings. SQL files may carry a short comment after a marker when a down section is intentionally a no-op.

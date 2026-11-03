-- migrate:up
CREATE TABLE IF NOT EXISTS public.schema_migrations (
    id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    name text NOT NULL UNIQUE,
    checksum text NOT NULL,
    applied_at timestamptz NOT NULL DEFAULT now()
);

ALTER TABLE public.schema_migrations ENABLE ROW LEVEL SECURITY;

REVOKE ALL ON TABLE public.schema_migrations FROM anon, authenticated;

-- migrate:down
-- Protected: this table records every applied migration, so reversing it is a no-op.
SELECT 1;

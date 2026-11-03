-- migrate:up
CREATE TABLE IF NOT EXISTS public.job (
    job_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    job_type varchar(100) NOT NULL,
    payload jsonb NOT NULL DEFAULT '{}'::jsonb,
    status varchar(20) NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'running', 'succeeded', 'failed', 'cancelled')),
    attempt integer NOT NULL DEFAULT 0 CHECK (attempt >= 0),
    max_attempt integer NOT NULL DEFAULT 3 CHECK (max_attempt >= 1),
    run_at timestamptz NOT NULL DEFAULT now(),
    locked_by varchar(100),
    locked_at timestamptz,
    started_at timestamptz,
    finished_at timestamptz,
    result jsonb,
    error_message text,
    idempotency_key varchar(100),
    request_id varchar(100),
    created_at timestamptz NOT NULL DEFAULT now(),
    created_by varchar(100) NOT NULL DEFAULT 'System',
    updated_at timestamptz NOT NULL DEFAULT now(),
    updated_by varchar(100) NOT NULL DEFAULT 'System',
    CONSTRAINT job_idempotency_key_key UNIQUE (idempotency_key)
);

CREATE INDEX IF NOT EXISTS job_pending_run_at_idx ON public.job (run_at) WHERE status = 'pending';

CREATE INDEX IF NOT EXISTS job_job_type_idx ON public.job (job_type);

ALTER TABLE public.job ENABLE ROW LEVEL SECURITY;

REVOKE ALL ON TABLE public.job FROM anon, authenticated;

-- migrate:down
DROP TABLE IF EXISTS public.job;

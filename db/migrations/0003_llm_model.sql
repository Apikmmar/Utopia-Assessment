-- migrate:up
CREATE TABLE IF NOT EXISTS public.llm_model (
    llm_model_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    provider varchar(50) NOT NULL,
    model varchar(100) NOT NULL,
    is_active boolean NOT NULL DEFAULT true,
    created_at timestamptz NOT NULL DEFAULT now(),
    created_by varchar(100) NOT NULL DEFAULT 'System',
    updated_at timestamptz NOT NULL DEFAULT now(),
    updated_by varchar(100) NOT NULL DEFAULT 'System',
    CONSTRAINT llm_model_provider_model_key UNIQUE (provider, model)
);

ALTER TABLE public.llm_model ENABLE ROW LEVEL SECURITY;

REVOKE ALL ON TABLE public.llm_model FROM anon, authenticated;

-- migrate:down
DROP TABLE IF EXISTS public.llm_model;

-- migrate:up
CREATE TABLE IF NOT EXISTS public.llm_invocation (
    llm_invocation_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    llm_model_id uuid NOT NULL REFERENCES public.llm_model (llm_model_id) ON DELETE RESTRICT,
    request_id varchar(100),
    status varchar(20) NOT NULL CHECK (status IN ('success', 'error', 'timeout')),
    latency_ms integer CHECK (latency_ms >= 0),
    error_message text,
    created_at timestamptz NOT NULL DEFAULT now(),
    created_by varchar(100) NOT NULL DEFAULT 'System',
    updated_at timestamptz NOT NULL DEFAULT now(),
    updated_by varchar(100) NOT NULL DEFAULT 'System'
);

CREATE INDEX IF NOT EXISTS llm_invocation_llm_model_id_idx ON public.llm_invocation (llm_model_id);

CREATE INDEX IF NOT EXISTS llm_invocation_created_at_idx ON public.llm_invocation (created_at DESC);

ALTER TABLE public.llm_invocation ENABLE ROW LEVEL SECURITY;

REVOKE ALL ON TABLE public.llm_invocation FROM anon, authenticated;

-- migrate:down
DROP TABLE IF EXISTS public.llm_invocation;

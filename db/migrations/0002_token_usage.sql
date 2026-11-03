-- migrate:up
CREATE TABLE public.token_usage (
    usage_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    model_id varchar(100) NOT NULL,
    input_token integer NOT NULL CHECK (input_token >= 0),
    output_token integer NOT NULL CHECK (output_token >= 0),
    total_token integer NOT NULL CHECK (total_token >= 0),
    created_at timestamptz NOT NULL DEFAULT now(),
    created_by varchar(100) NOT NULL DEFAULT 'System',
    updated_at timestamptz NOT NULL DEFAULT now(),
    updated_by varchar(100) NOT NULL DEFAULT 'System'
);

ALTER TABLE public.token_usage ENABLE ROW LEVEL SECURITY;

REVOKE ALL ON TABLE public.token_usage FROM anon, authenticated;

-- migrate:down
DROP TABLE public.token_usage;

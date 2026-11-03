-- migrate:up
CREATE TABLE IF NOT EXISTS public.setting (
    setting_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    setting_key varchar(100) NOT NULL,
    setting_value text NOT NULL,
    value_type varchar(20) NOT NULL DEFAULT 'string' CHECK (value_type IN ('string', 'integer', 'number', 'boolean', 'json')),
    description text,
    created_at timestamptz NOT NULL DEFAULT now(),
    created_by varchar(100) NOT NULL DEFAULT 'System',
    updated_at timestamptz NOT NULL DEFAULT now(),
    updated_by varchar(100) NOT NULL DEFAULT 'System',
    CONSTRAINT setting_setting_key_key UNIQUE (setting_key)
);

ALTER TABLE public.setting ENABLE ROW LEVEL SECURITY;

REVOKE ALL ON TABLE public.setting FROM anon, authenticated;

-- migrate:down
DROP TABLE IF EXISTS public.setting;

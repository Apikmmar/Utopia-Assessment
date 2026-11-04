-- migrate:up
CREATE TABLE IF NOT EXISTS public.service_type (
    service_type_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    service_type_code varchar(30) NOT NULL,
    service_type_name varchar(50) NOT NULL,
    sort_order smallint NOT NULL DEFAULT 0,
    is_active boolean NOT NULL DEFAULT true,
    created_at timestamptz NOT NULL DEFAULT now(),
    created_by varchar(100) NOT NULL DEFAULT 'System',
    updated_at timestamptz NOT NULL DEFAULT now(),
    updated_by varchar(100) NOT NULL DEFAULT 'System',
    CONSTRAINT service_type_service_type_code_key UNIQUE (service_type_code)
);

ALTER TABLE public.service_type ENABLE ROW LEVEL SECURITY;

REVOKE ALL ON TABLE public.service_type FROM anon, authenticated;

INSERT INTO public.service_type (service_type_code, service_type_name, sort_order) VALUES
    ('cleaning', 'Aircond cleaning', 1),
    ('repair', 'Repair', 2),
    ('gas_refill', 'Gas refill', 3),
    ('installation', 'Installation', 4),
    ('general_servicing', 'General servicing', 5)
ON CONFLICT (service_type_code) DO NOTHING;

-- migrate:down
DROP TABLE IF EXISTS public.service_type;

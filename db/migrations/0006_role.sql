-- migrate:up
CREATE TABLE IF NOT EXISTS public.role (
    role_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    role_code varchar(30) NOT NULL,
    role_name varchar(50) NOT NULL,
    description text,
    is_active boolean NOT NULL DEFAULT true,
    created_at timestamptz NOT NULL DEFAULT now(),
    created_by varchar(100) NOT NULL DEFAULT 'System',
    updated_at timestamptz NOT NULL DEFAULT now(),
    updated_by varchar(100) NOT NULL DEFAULT 'System',
    CONSTRAINT role_role_code_key UNIQUE (role_code)
);

ALTER TABLE public.role ENABLE ROW LEVEL SECURITY;

REVOKE ALL ON TABLE public.role FROM anon, authenticated;

INSERT INTO public.role (role_code, role_name, description) VALUES
    ('admin', 'Admin', 'Submits orders and assigns technicians.'),
    ('technician', 'Technician', 'Performs assigned jobs and marks them completed.'),
    ('manager', 'Manager', 'Reviews completed jobs and views performance.')
ON CONFLICT (role_code) DO NOTHING;

-- migrate:down
DROP TABLE IF EXISTS public.role;

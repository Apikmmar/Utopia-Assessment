-- migrate:up
CREATE TABLE IF NOT EXISTS public."user" (
    user_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    name varchar(100) NOT NULL,
    email varchar(255) NOT NULL,
    phone varchar(20),
    age smallint CHECK (age BETWEEN 16 AND 100),
    role_id uuid NOT NULL REFERENCES public.role (role_id) ON DELETE RESTRICT,
    is_active boolean NOT NULL DEFAULT true,
    created_at timestamptz NOT NULL DEFAULT now(),
    created_by varchar(100) NOT NULL DEFAULT 'System',
    updated_at timestamptz NOT NULL DEFAULT now(),
    updated_by varchar(100) NOT NULL DEFAULT 'System',
    CONSTRAINT user_email_key UNIQUE (email)
);

CREATE INDEX IF NOT EXISTS user_role_id_idx ON public."user" (role_id);

ALTER TABLE public."user" ENABLE ROW LEVEL SECURITY;

REVOKE ALL ON TABLE public."user" FROM anon, authenticated;

-- migrate:down
DROP TABLE IF EXISTS public."user";

-- migrate:up
ALTER TABLE public."user" ADD COLUMN IF NOT EXISTS password_hash varchar(255);

ALTER TABLE public."user" ADD COLUMN IF NOT EXISTS password_changed_at timestamptz;

ALTER TABLE public."user" ADD CONSTRAINT user_email_lowercase_check CHECK (email = lower(email));

ALTER TABLE public."user" ADD CONSTRAINT user_phone_digits_check CHECK (phone IS NULL OR phone ~ '^[0-9]{8,15}$');

CREATE TABLE IF NOT EXISTS public.session (
    session_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id uuid NOT NULL REFERENCES public."user" (user_id) ON DELETE RESTRICT,
    token_hash char(64) NOT NULL,
    expires_at timestamptz NOT NULL,
    revoked_at timestamptz,
    last_used_at timestamptz NOT NULL DEFAULT now(),
    ip varchar(45),
    user_agent varchar(300),
    created_at timestamptz NOT NULL DEFAULT now(),
    created_by varchar(100) NOT NULL DEFAULT 'System',
    updated_at timestamptz NOT NULL DEFAULT now(),
    updated_by varchar(100) NOT NULL DEFAULT 'System',
    CONSTRAINT session_token_hash_key UNIQUE (token_hash)
);

CREATE INDEX IF NOT EXISTS session_user_id_idx ON public.session (user_id);

CREATE INDEX IF NOT EXISTS session_expires_at_idx ON public.session (expires_at);

ALTER TABLE public.session ENABLE ROW LEVEL SECURITY;

REVOKE ALL ON TABLE public.session FROM anon, authenticated;

-- migrate:down
DROP TABLE IF EXISTS public.session;

ALTER TABLE public."user" DROP CONSTRAINT IF EXISTS user_phone_digits_check;

ALTER TABLE public."user" DROP CONSTRAINT IF EXISTS user_email_lowercase_check;

ALTER TABLE public."user" DROP COLUMN IF EXISTS password_changed_at;

ALTER TABLE public."user" DROP COLUMN IF EXISTS password_hash;

-- migrate:up
CREATE TABLE IF NOT EXISTS public.order_attachment (
    order_attachment_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    service_order_id uuid NOT NULL REFERENCES public.service_order (service_order_id) ON DELETE RESTRICT,
    kind varchar(20) NOT NULL CHECK (kind IN ('completion', 'receipt')),
    storage_path varchar(300) NOT NULL,
    file_name varchar(255) NOT NULL,
    content_type varchar(100) NOT NULL,
    size_bytes bigint NOT NULL CHECK (size_bytes > 0),
    status varchar(20) NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'uploaded')),
    uploaded_by_id uuid NOT NULL REFERENCES public."user" (user_id) ON DELETE RESTRICT,
    confirmed_at timestamptz,
    created_at timestamptz NOT NULL DEFAULT now(),
    created_by varchar(100) NOT NULL DEFAULT 'System',
    updated_at timestamptz NOT NULL DEFAULT now(),
    updated_by varchar(100) NOT NULL DEFAULT 'System',
    CONSTRAINT order_attachment_storage_path_key UNIQUE (storage_path)
);

CREATE INDEX IF NOT EXISTS order_attachment_order_kind_idx ON public.order_attachment (service_order_id, kind);

ALTER TABLE public.order_attachment ENABLE ROW LEVEL SECURITY;

REVOKE ALL ON TABLE public.order_attachment FROM anon, authenticated;

-- migrate:down
DROP TABLE IF EXISTS public.order_attachment;

-- migrate:up
CREATE SEQUENCE IF NOT EXISTS public.service_order_no_seq;

CREATE OR REPLACE FUNCTION public.next_service_order_no() RETURNS varchar
LANGUAGE sql AS $$
    SELECT 'ORD-' || lpad(n::text, greatest(6, length(n::text)), '0')
    FROM (SELECT nextval('public.service_order_no_seq') AS n) AS s
$$;

REVOKE ALL ON FUNCTION public.next_service_order_no() FROM PUBLIC, anon, authenticated;

REVOKE ALL ON SEQUENCE public.service_order_no_seq FROM anon, authenticated;

CREATE TABLE IF NOT EXISTS public.service_order (
    service_order_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    order_no varchar(20) NOT NULL DEFAULT public.next_service_order_no(),
    customer_name varchar(100) NOT NULL,
    customer_phone varchar(20) NOT NULL CHECK (customer_phone ~ '^[0-9]{8,15}$'),
    address varchar(500) NOT NULL,
    problem_description varchar(2000) NOT NULL,
    service_type_id uuid NOT NULL REFERENCES public.service_type (service_type_id) ON DELETE RESTRICT,
    quoted_price numeric(10,2) NOT NULL CHECK (quoted_price >= 0),
    assigned_technician_id uuid REFERENCES public."user" (user_id) ON DELETE RESTRICT,
    admin_notes varchar(2000),
    status varchar(20) NOT NULL CHECK (status IN ('new', 'assigned', 'in_progress', 'job_done', 'reviewed', 'closed')),
    status_changed_at timestamptz NOT NULL DEFAULT now(),
    started_at timestamptz,
    job_done_at timestamptz,
    reviewed_at timestamptz,
    reviewed_by_id uuid REFERENCES public."user" (user_id) ON DELETE RESTRICT,
    closed_at timestamptz,
    closed_by_id uuid REFERENCES public."user" (user_id) ON DELETE RESTRICT,
    created_by_id uuid NOT NULL REFERENCES public."user" (user_id) ON DELETE RESTRICT,
    created_at timestamptz NOT NULL DEFAULT now(),
    created_by varchar(100) NOT NULL DEFAULT 'System',
    updated_at timestamptz NOT NULL DEFAULT now(),
    updated_by varchar(100) NOT NULL DEFAULT 'System',
    CONSTRAINT service_order_order_no_key UNIQUE (order_no),
    CONSTRAINT service_order_technician_matches_status_check CHECK ((status = 'new') = (assigned_technician_id IS NULL))
);

CREATE INDEX IF NOT EXISTS service_order_status_created_at_idx ON public.service_order (status, created_at);

CREATE INDEX IF NOT EXISTS service_order_technician_status_idx ON public.service_order (assigned_technician_id, status);

CREATE INDEX IF NOT EXISTS service_order_created_at_idx ON public.service_order (created_at);

CREATE INDEX IF NOT EXISTS service_order_service_type_id_idx ON public.service_order (service_type_id);

ALTER TABLE public.service_order ENABLE ROW LEVEL SECURITY;

REVOKE ALL ON TABLE public.service_order FROM anon, authenticated;

-- migrate:down
DROP TABLE IF EXISTS public.service_order;

DROP FUNCTION IF EXISTS public.next_service_order_no();

DROP SEQUENCE IF EXISTS public.service_order_no_seq;

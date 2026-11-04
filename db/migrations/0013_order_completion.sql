-- migrate:up
CREATE TABLE IF NOT EXISTS public.order_completion (
    order_completion_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    service_order_id uuid NOT NULL REFERENCES public.service_order (service_order_id) ON DELETE RESTRICT,
    technician_id uuid NOT NULL REFERENCES public."user" (user_id) ON DELETE RESTRICT,
    work_done varchar(2000) NOT NULL,
    quoted_price numeric(10,2) NOT NULL CHECK (quoted_price >= 0),
    extra_charges numeric(10,2) NOT NULL DEFAULT 0 CHECK (extra_charges >= 0),
    final_amount numeric(10,2) NOT NULL,
    remarks varchar(2000),
    payment_amount numeric(10,2) CHECK (payment_amount >= 0),
    payment_method varchar(20) CHECK (payment_method IN ('cash', 'card', 'bank_transfer', 'ewallet')),
    receipt_attachment_id uuid REFERENCES public.order_attachment (order_attachment_id) ON DELETE RESTRICT,
    completed_at timestamptz NOT NULL DEFAULT now(),
    created_at timestamptz NOT NULL DEFAULT now(),
    created_by varchar(100) NOT NULL DEFAULT 'System',
    updated_at timestamptz NOT NULL DEFAULT now(),
    updated_by varchar(100) NOT NULL DEFAULT 'System',
    CONSTRAINT order_completion_service_order_id_key UNIQUE (service_order_id),
    CONSTRAINT order_completion_final_amount_check CHECK (final_amount = quoted_price + extra_charges),
    CONSTRAINT order_completion_payment_pair_check CHECK ((payment_amount IS NULL) = (payment_method IS NULL)),
    CONSTRAINT order_completion_receipt_needs_payment_check CHECK (receipt_attachment_id IS NULL OR payment_amount IS NOT NULL)
);

CREATE INDEX IF NOT EXISTS order_completion_technician_completed_at_idx ON public.order_completion (technician_id, completed_at);

ALTER TABLE public.order_completion ENABLE ROW LEVEL SECURITY;

REVOKE ALL ON TABLE public.order_completion FROM anon, authenticated;

-- migrate:down
DROP TABLE IF EXISTS public.order_completion;

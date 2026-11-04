-- migrate:up
CREATE TABLE IF NOT EXISTS public.order_event (
    order_event_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    service_order_id uuid NOT NULL REFERENCES public.service_order (service_order_id) ON DELETE RESTRICT,
    event_type varchar(40) NOT NULL CHECK (event_type IN (
        'created', 'edited', 'assigned', 'reassigned', 'started', 'completed',
        'reviewed', 'closed', 'notification_queued'
    )),
    from_status varchar(20),
    to_status varchar(20),
    actor_id uuid NOT NULL REFERENCES public."user" (user_id) ON DELETE RESTRICT,
    request_id varchar(100),
    detail jsonb NOT NULL DEFAULT '{}'::jsonb,
    created_at timestamptz NOT NULL DEFAULT now(),
    created_by varchar(100) NOT NULL DEFAULT 'System'
);

CREATE INDEX IF NOT EXISTS order_event_order_created_at_idx ON public.order_event (service_order_id, created_at);

ALTER TABLE public.order_event ENABLE ROW LEVEL SECURITY;

REVOKE ALL ON TABLE public.order_event FROM anon, authenticated;

-- migrate:down
DROP TABLE IF EXISTS public.order_event;

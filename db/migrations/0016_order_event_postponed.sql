-- migrate:up
ALTER TABLE public.order_event DROP CONSTRAINT IF EXISTS order_event_event_type_check;
ALTER TABLE public.order_event ADD CONSTRAINT order_event_event_type_check CHECK (event_type IN (
    'created', 'edited', 'assigned', 'reassigned', 'started', 'completed',
    'reviewed', 'closed', 'notification_queued', 'postponed'
));

CREATE INDEX IF NOT EXISTS order_event_postponed_created_at_idx
    ON public.order_event (created_at) WHERE event_type = 'postponed';

-- migrate:down
DROP INDEX IF EXISTS public.order_event_postponed_created_at_idx;
ALTER TABLE public.order_event DROP CONSTRAINT IF EXISTS order_event_event_type_check;
ALTER TABLE public.order_event ADD CONSTRAINT order_event_event_type_check CHECK (event_type IN (
    'created', 'edited', 'assigned', 'reassigned', 'started', 'completed',
    'reviewed', 'closed', 'notification_queued'
));

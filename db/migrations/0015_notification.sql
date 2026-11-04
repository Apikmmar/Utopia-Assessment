-- migrate:up
CREATE TABLE IF NOT EXISTS public.notification (
    notification_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    service_order_id uuid NOT NULL REFERENCES public.service_order (service_order_id) ON DELETE RESTRICT,
    notification_type varchar(40) NOT NULL CHECK (notification_type IN ('job_assigned', 'job_done')),
    channel varchar(20) NOT NULL DEFAULT 'whatsapp' CHECK (channel IN ('whatsapp')),
    provider varchar(30) NOT NULL DEFAULT 'deeplink' CHECK (provider IN ('deeplink')),
    recipient_type varchar(20) NOT NULL CHECK (recipient_type IN ('customer', 'technician')),
    recipient_user_id uuid REFERENCES public."user" (user_id) ON DELETE RESTRICT,
    recipient_name varchar(100) NOT NULL,
    recipient_phone varchar(20) NOT NULL CHECK (recipient_phone ~ '^[0-9]{8,15}$'),
    order_no varchar(20) NOT NULL,
    sender_user_id uuid REFERENCES public."user" (user_id) ON DELETE RESTRICT,
    template_data jsonb NOT NULL,
    message varchar(4000),
    deep_link varchar(8000),
    status varchar(20) NOT NULL DEFAULT 'queued' CHECK (status IN ('queued', 'ready', 'opened', 'sent', 'failed')),
    job_id uuid REFERENCES public.job (job_id) ON DELETE RESTRICT,
    provider_message_id varchar(100),
    error_message varchar(500),
    ready_at timestamptz,
    opened_at timestamptz,
    opened_by_id uuid REFERENCES public."user" (user_id) ON DELETE RESTRICT,
    sent_at timestamptz,
    request_id varchar(100),
    created_at timestamptz NOT NULL DEFAULT now(),
    created_by varchar(100) NOT NULL DEFAULT 'System',
    updated_at timestamptz NOT NULL DEFAULT now(),
    updated_by varchar(100) NOT NULL DEFAULT 'System',
    CONSTRAINT notification_recipient_user_check CHECK ((recipient_type = 'technician') = (recipient_user_id IS NOT NULL)),
    CONSTRAINT notification_ready_has_link_check CHECK (status IN ('queued', 'failed') OR (message IS NOT NULL AND deep_link IS NOT NULL))
);

CREATE INDEX IF NOT EXISTS notification_order_created_at_idx ON public.notification (service_order_id, created_at);

CREATE INDEX IF NOT EXISTS notification_job_id_idx ON public.notification (job_id);

CREATE INDEX IF NOT EXISTS notification_status_created_at_idx ON public.notification (status, created_at);

CREATE INDEX IF NOT EXISTS notification_sender_status_idx ON public.notification (sender_user_id, status);

ALTER TABLE public.notification ENABLE ROW LEVEL SECURITY;

REVOKE ALL ON TABLE public.notification FROM anon, authenticated;

-- migrate:down
DROP TABLE IF EXISTS public.notification;

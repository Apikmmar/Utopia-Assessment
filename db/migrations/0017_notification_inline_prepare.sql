-- migrate:up
UPDATE public.job SET status = 'cancelled', locked_by = NULL, locked_at = NULL, finished_at = now(), updated_at = now(), updated_by = 'System'
    WHERE job_type = 'notification.deliver' AND status IN ('pending', 'running');

UPDATE public.notification SET status = 'failed', error_message = 'WorkerRemoved', updated_at = now(), updated_by = 'System'
    WHERE status = 'queued';

DROP INDEX IF EXISTS public.notification_job_id_idx;

ALTER TABLE public.notification DROP COLUMN IF EXISTS job_id;

-- migrate:down
ALTER TABLE public.notification ADD COLUMN IF NOT EXISTS job_id uuid REFERENCES public.job (job_id) ON DELETE RESTRICT;

CREATE INDEX IF NOT EXISTS notification_job_id_idx ON public.notification (job_id);

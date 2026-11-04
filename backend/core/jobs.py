from sqlalchemy import select, text
from sqlalchemy.dialects.postgresql import insert
from core.db import jobTable, readOne, transaction

RETRY_BACKOFF_SECONDS = (10, 60, 300)
STALE_JOB_SECONDS = 300
ERROR_MESSAGE_MAX_LENGTH = 500
JOB_ACTOR = "worker"

CLAIM_SQL = text(
    "UPDATE job SET status = 'running', locked_by = :workerId, locked_at = now(), started_at = now(), "
    "attempt = attempt + 1, updated_at = now(), updated_by = :actor "
    "WHERE job_id = ("
    "    SELECT job_id FROM job WHERE status = 'pending' AND run_at <= now() "
    "    ORDER BY run_at FOR UPDATE SKIP LOCKED LIMIT 1"
    ") RETURNING job_id, job_type, payload, attempt, max_attempt, request_id"
)
FINISH_SQL = text(
    "UPDATE job SET status = 'succeeded', result = CAST(:result AS jsonb), finished_at = now(), "
    "locked_by = NULL, locked_at = NULL, updated_at = now(), updated_by = :actor "
    "WHERE job_id = :jobId AND status = 'running'"
)
FAIL_SQL = text(
    "UPDATE job SET "
    "status = CASE WHEN attempt < max_attempt THEN 'pending' ELSE 'failed' END, "
    "run_at = CASE WHEN attempt < max_attempt THEN now() + make_interval(secs => :delaySeconds) ELSE run_at END, "
    "finished_at = CASE WHEN attempt < max_attempt THEN NULL ELSE now() END, "
    "error_message = :errorMessage, locked_by = NULL, locked_at = NULL, updated_at = now(), updated_by = :actor "
    "WHERE job_id = :jobId AND status = 'running' RETURNING status"
)
RECLAIM_SQL = text(
    "UPDATE job SET status = 'pending', locked_by = NULL, locked_at = NULL, updated_at = now(), updated_by = :actor "
    "WHERE status = 'running' AND locked_at < now() - make_interval(secs => :staleSeconds) RETURNING job_id"
)

# Inserts a pending job in the caller's transaction and returns its id; a repeated idempotency key
# returns the existing job instead of adding a second one.
def enqueueJob(conn, jobType, payload, idempotencyKey, requestId=None, actor=JOB_ACTOR):
    statement = (
        insert(jobTable)
        .values(job_type=jobType, payload=payload, idempotency_key=idempotencyKey, request_id=requestId, created_by=actor, updated_by=actor)
        .on_conflict_do_nothing(index_elements=[jobTable.c.idempotency_key])
        .returning(jobTable.c.job_id)
    )
    jobId = conn.execute(statement).scalar()
    if jobId is not None:
        return jobId
    return conn.execute(select(jobTable.c.job_id).where(jobTable.c.idempotency_key == idempotencyKey)).scalar_one()

# Claims the next due job for one worker in its own short transaction, or returns None when none is due.
def claimJob(workerId):
    with transaction() as conn:
        row = conn.execute(CLAIM_SQL, {"workerId": workerId, "actor": JOB_ACTOR}).mappings().first()
    return dict(row) if row is not None else None

# Marks a running job succeeded with an optional JSON-encoded result.
def finishJob(jobId, resultJson=None):
    with transaction() as conn:
        conn.execute(FINISH_SQL, {"jobId": jobId, "result": resultJson, "actor": JOB_ACTOR})

# Returns the wait before the next try after the given attempt number.
def retryDelaySeconds(attempt):
    return RETRY_BACKOFF_SECONDS[min(max(attempt, 1), len(RETRY_BACKOFF_SECONDS)) - 1]

# Puts a failed running job back to pending with back-off, or fails it for good after its last
# attempt; returns True when the job is exhausted.
def failJob(jobId, attempt, errorMessage):
    params = {
        "jobId": jobId, "delaySeconds": retryDelaySeconds(attempt),
        "errorMessage": (errorMessage or "")[:ERROR_MESSAGE_MAX_LENGTH], "actor": JOB_ACTOR,
    }
    with transaction() as conn:
        status = conn.execute(FAIL_SQL, params).scalar()
    return status == "failed"

# Returns jobs left running longer than the stale limit, for example after a crash, to pending and
# returns how many were reclaimed.
def reclaimStaleJobs(staleSeconds=STALE_JOB_SECONDS):
    with transaction() as conn:
        return len(conn.execute(RECLAIM_SQL, {"staleSeconds": staleSeconds, "actor": JOB_ACTOR}).all())

# Returns one job row by id, for checks and tests.
def getJob(jobId, conn=None):
    return readOne(select(jobTable).where(jobTable.c.job_id == jobId), conn)


__all__ = [
    "RETRY_BACKOFF_SECONDS",
    "STALE_JOB_SECONDS",
    "claimJob",
    "enqueueJob",
    "failJob",
    "finishJob",
    "getJob",
    "reclaimStaleJobs",
    "retryDelaySeconds",
]

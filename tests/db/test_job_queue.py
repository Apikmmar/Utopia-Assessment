from concurrent.futures import ThreadPoolExecutor
import pytest
from sqlalchemy import text
from core import jobs

JOB_TYPE = "test.job"
CONCURRENT_JOBS = 6
CONCURRENT_WORKERS = 3


class Rollback(Exception):
    pass

# Enqueues one job in its own transaction and returns its id.
def enqueue(engine, key, payload=None):
    with engine.begin() as conn:
        return jobs.enqueueJob(conn, JOB_TYPE, payload or {}, key, requestId="req-1")

# Returns the seconds from now until a job's run_at.
def secondsUntilRun(scalar, jobId):
    return scalar("SELECT extract(epoch FROM run_at - now()) FROM job WHERE job_id = :jobId", jobId=jobId)

# A repeated idempotency key returns the first job instead of adding a second.
def testEnqueueIsIdempotent(appDb, scalar):
    first = enqueue(appDb, "key-1", {"a": 1})
    assert enqueue(appDb, "key-1", {"a": 2}) == first
    assert scalar("SELECT count(*) FROM job") == 1
    assert scalar("SELECT payload ->> 'a' FROM job") == "1"

# A job enqueued in a transaction that rolls back leaves nothing behind.
def testEnqueueRollsBackWithItsTransaction(appDb, scalar):
    with pytest.raises(Rollback):
        with appDb.begin() as conn:
            jobs.enqueueJob(conn, JOB_TYPE, {}, "key-rollback")
            raise Rollback()
    assert scalar("SELECT count(*) FROM job") == 0

# Claiming marks the job running for that worker and counts the attempt; nothing else is then due.
def testClaimMarksRunning(appDb):
    jobId = enqueue(appDb, "key-claim")
    claimed = jobs.claimJob("worker-a")
    assert (claimed["job_id"], claimed["job_type"], claimed["attempt"], claimed["request_id"]) == (jobId, JOB_TYPE, 1, "req-1")
    row = jobs.getJob(jobId)
    assert (row["status"], row["locked_by"]) == ("running", "worker-a")
    assert jobs.claimJob("worker-b") is None

# A job scheduled in the future is not claimed yet.
def testClaimSkipsJobsNotDue(appDb, execute):
    jobId = enqueue(appDb, "key-later")
    execute("UPDATE job SET run_at = now() + interval '1 hour' WHERE job_id = :jobId", jobId=jobId)
    assert jobs.claimJob("worker-a") is None

# Several workers claiming at once each get distinct jobs and together take every job once.
def testConcurrentWorkersNeverShareJobs(appDb):
    expected = {enqueue(appDb, f"key-{index}") for index in range(CONCURRENT_JOBS)}

    # Claims jobs until none is due and returns their ids.
    def drain(workerId):
        claimed = []
        while (job := jobs.claimJob(workerId)) is not None:
            claimed.append(job["job_id"])
        return claimed

    with ThreadPoolExecutor(max_workers=CONCURRENT_WORKERS) as pool:
        results = list(pool.map(drain, [f"worker-{index}" for index in range(CONCURRENT_WORKERS)]))
    claimed = [jobId for result in results for jobId in result]
    assert len(claimed) == len(set(claimed)) == CONCURRENT_JOBS
    assert set(claimed) == expected

# Finishing marks the job succeeded and releases its lock.
def testFinishJob(appDb):
    jobId = enqueue(appDb, "key-finish")
    jobs.claimJob("worker-a")
    jobs.finishJob(jobId, '{"ok": true}')
    row = jobs.getJob(jobId)
    assert (row["status"], row["locked_by"], row["result"]) == ("succeeded", None, {"ok": True})
    assert row["finished_at"] is not None

# Each failed attempt goes back to pending after 10, then 60 seconds, and the last one fails for good.
def testFailBacksOffThenExhausts(appDb, scalar, execute):
    jobId = enqueue(appDb, "key-fail")
    for attempt, delay in ((1, 10), (2, 60)):
        claimed = jobs.claimJob("worker-a")
        assert claimed["attempt"] == attempt
        assert jobs.failJob(jobId, attempt, "RuntimeError") is False
        assert jobs.getJob(jobId)["status"] == "pending"
        assert delay - 2 < secondsUntilRun(scalar, jobId) <= delay
        execute("UPDATE job SET run_at = now() WHERE job_id = :jobId", jobId=jobId)
    jobs.claimJob("worker-a")
    assert jobs.failJob(jobId, 3, "RuntimeError") is True
    row = jobs.getJob(jobId)
    assert (row["status"], row["error_message"], row["attempt"]) == ("failed", "RuntimeError", 3)
    assert row["finished_at"] is not None

# The back-off grows 10, 60, 300 seconds and stays at the last step.
def testRetryDelays():
    assert [jobs.retryDelaySeconds(attempt) for attempt in (1, 2, 3, 4)] == [10, 60, 300, 300]

# A job left running past the stale limit returns to pending; a fresh running job is left alone.
def testReclaimStaleJobs(appDb, execute):
    staleId = enqueue(appDb, "key-stale")
    freshId = enqueue(appDb, "key-fresh")
    jobs.claimJob("worker-a")
    jobs.claimJob("worker-b")
    execute("UPDATE job SET locked_at = now() - interval '10 minutes' WHERE job_id = :jobId", jobId=staleId)
    assert jobs.reclaimStaleJobs() == 1
    assert jobs.getJob(staleId)["status"] == "pending"
    assert jobs.getJob(freshId)["status"] == "running"

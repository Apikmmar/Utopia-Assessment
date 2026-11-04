from core import jobs
from worker.handlers import JobHandler
from worker.main import Worker

# Enqueues one job of the given type in its own transaction and returns its id.
def enqueue(engine, jobType, key, payload=None):
    with engine.begin() as conn:
        return jobs.enqueueJob(conn, jobType, payload or {}, key)

# One loop iteration runs a due job through its handler and marks it succeeded.
def testRunOnceDeliversDueJob(appDb):
    seen = []
    jobId = enqueue(appDb, "test.ok", "key-ok", {"value": 7})
    worker = Worker({"test.ok": JobHandler(run=seen.append)}, pollSeconds=1, workerId="test-worker")
    assert worker.runOnce() is True
    assert seen == [{"value": 7}]
    assert jobs.getJob(jobId)["status"] == "succeeded"
    assert worker.runOnce() is False

# A handler that keeps failing is retried, then failed, and its failure hook gets the error type.
def testFailingHandlerEndsFailedWithHook(appDb, execute):
    failures = []

    # Always fails the way a broken delivery would.
    def explode(payload):
        raise RuntimeError("secret detail 60123456789")

    jobId = enqueue(appDb, "test.fail", "key-fail", {"id": 1})
    execute("UPDATE job SET max_attempt = 1 WHERE job_id = :jobId", jobId=jobId)
    handler = JobHandler(run=explode, onExhausted=lambda payload, reason: failures.append((payload, reason)))
    Worker({"test.fail": handler}, pollSeconds=1, workerId="test-worker").runOnce()
    row = jobs.getJob(jobId)
    assert (row["status"], row["error_message"]) == ("failed", "RuntimeError")
    assert failures == [({"id": 1}, "RuntimeError")]

# A job with no registered handler is retried later rather than lost.
def testUnknownJobTypeIsRetried(appDb):
    jobId = enqueue(appDb, "test.unknown", "key-unknown")
    Worker({}, pollSeconds=1, workerId="test-worker").runOnce()
    row = jobs.getJob(jobId)
    assert (row["status"], row["error_message"]) == ("pending", "UnknownJobType")

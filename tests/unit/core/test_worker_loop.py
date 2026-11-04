import logging
import signal
import threading
from core import jobs
from worker import main as workerMain
from worker.handlers import JobHandler
from worker.main import Worker

JOIN_SECONDS = 5


class FakeQueue:
    # Hands out the given jobs once each and records how each one ended.
    def __init__(self, queued):
        self.queued = list(queued)
        self.finished = []
        self.failed = []
        self.reclaims = 0

    # Returns the next queued job, or None when none is left.
    def claim(self, workerId):
        return self.queued.pop(0) if self.queued else None

    # Records a finished job.
    def finish(self, jobId, resultJson=None):
        self.finished.append(jobId)

    # Records a failed attempt and reports exhaustion on the job's last attempt.
    def fail(self, jobId, attempt, reason):
        self.failed.append((jobId, reason))
        return attempt >= 1

    # Counts reclaim calls.
    def reclaim(self):
        self.reclaims += 1
        return 0

# Replaces the job queue functions the worker calls with the fake.
def useQueue(monkeypatch, queue):
    monkeypatch.setattr(jobs, "claimJob", queue.claim)
    monkeypatch.setattr(jobs, "finishJob", queue.finish)
    monkeypatch.setattr(jobs, "failJob", queue.fail)
    monkeypatch.setattr(jobs, "reclaimStaleJobs", queue.reclaim)

# Returns one claimed job row of the given type.
def job(jobId, jobType="test.job"):
    return {"job_id": jobId, "job_type": jobType, "payload": {"id": jobId}, "attempt": 1, "max_attempt": 1, "request_id": None}

# A failure hook that raises is logged and does not stop the worker.
def testFailureHookErrorIsContained(monkeypatch, caplog):
    queue = FakeQueue([job("a"), job("b", "test.ok")])
    useQueue(monkeypatch, queue)

    # Fails every run.
    def explode(payload):
        raise ValueError("boom")

    # Fails while handling the failure.
    def brokenHook(payload, reason):
        raise RuntimeError("hook")

    worker = Worker({"test.job": JobHandler(run=explode, onExhausted=brokenHook), "test.ok": JobHandler(run=lambda payload: None)}, pollSeconds=1)
    with caplog.at_level(logging.ERROR):
        assert worker.runOnce() and worker.runOnce()
    assert queue.failed == [("a", "ValueError")]
    assert queue.finished == ["b"]
    assert "job_failure_hook_failed" in caplog.text

# The loop reclaims at start, sleeps when idle, and stops promptly when asked.
def testRunStopsWhenAsked(monkeypatch):
    queue = FakeQueue([])
    useQueue(monkeypatch, queue)
    idle = threading.Event()
    monkeypatch.setattr(jobs, "claimJob", lambda workerId: idle.set())
    worker = Worker({}, pollSeconds=60)
    thread = threading.Thread(target=worker.run)
    thread.start()
    assert idle.wait(JOIN_SECONDS)
    worker.stop()
    thread.join(JOIN_SECONDS)
    assert not thread.is_alive()
    assert queue.reclaims == 1

# Reclaim runs again only after the reclaim interval has passed.
def testReclaimRunsOncePerInterval(monkeypatch):
    queue = FakeQueue([])
    useQueue(monkeypatch, queue)
    now = [0.0]
    worker = Worker({}, pollSeconds=1, clock=lambda: now[0])
    worker.reclaimIfDue()
    now[0] = 30.0
    worker.reclaimIfDue()
    now[0] = 61.0
    worker.reclaimIfDue()
    assert queue.reclaims == 2

# A loop step that raises, such as a database outage, is logged and the loop keeps going.
def testLoopSurvivesStepErrors(monkeypatch, caplog):
    worker = Worker({}, pollSeconds=0)
    calls = []

    # Fails once, then stops the worker.
    def flaky(workerId):
        calls.append(workerId)
        if len(calls) == 1:
            raise ConnectionError("db down")
        worker.stop()

    monkeypatch.setattr(jobs, "claimJob", flaky)
    monkeypatch.setattr(jobs, "reclaimStaleJobs", lambda: 0)
    with caplog.at_level(logging.ERROR):
        worker.run()
    assert len(calls) == 2
    assert "worker_loop_failed error_type=ConnectionError" in caplog.text

# SIGTERM and SIGINT both stop the foreground worker after the current job.
def testSignalsStopTheWorker(monkeypatch):
    installed = {}
    built = []
    monkeypatch.setattr(workerMain.signal, "signal", lambda signum, handler: installed.__setitem__(signum, handler))
    monkeypatch.setattr(workerMain.config, "requireStartupSettings", lambda: None)
    monkeypatch.setattr(workerMain, "configureLogging", lambda: None)
    monkeypatch.setattr(Worker, "run", lambda self: built.append(self))
    workerMain.main()
    assert set(installed) == {signal.SIGTERM, signal.SIGINT}
    installed[signal.SIGTERM](signal.SIGTERM, None)
    assert built[0].stopping.is_set()

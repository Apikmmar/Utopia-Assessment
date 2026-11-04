import os
import signal
import socket
import threading
import time
import uuid
from core import config
from core import jobs
from core.logger import configureLogging, getLogger
from core.request_context import bindRequestId, resetRequestId
from worker.handlers import jobHandlers

log = getLogger(__name__)

RECLAIM_INTERVAL_SECONDS = 60
WORKER_ID_MAX_LENGTH = 100
UNKNOWN_JOB_TYPE = "UnknownJobType"
STOP_SIGNALS = (signal.SIGTERM, signal.SIGINT)


class Worker:
    # Holds the handler map, the poll interval, and a stop flag; clock and wait are injectable for tests.
    def __init__(self, handlers, pollSeconds, workerId=None, clock=time.monotonic):
        self.handlers = handlers
        self.pollSeconds = pollSeconds
        self.workerId = (workerId or newWorkerId())[:WORKER_ID_MAX_LENGTH]
        self.clock = clock
        self.stopping = threading.Event()
        self.lastReclaim = None

    # Asks the loop to stop after the job it is running.
    def stop(self):
        self.stopping.set()

    # Returns stale running jobs to pending when the reclaim interval has passed.
    def reclaimIfDue(self):
        now = self.clock()
        if self.lastReclaim is not None and now - self.lastReclaim < RECLAIM_INTERVAL_SECONDS:
            return
        self.lastReclaim = now
        reclaimed = jobs.reclaimStaleJobs()
        if reclaimed:
            log.warning("job_reclaimed count=%s", reclaimed)

    # Claims and runs one due job, returning False when none was due.
    def runOnce(self):
        job = jobs.claimJob(self.workerId)
        if job is None:
            return False
        token = bindRequestId(job["request_id"])
        try:
            self.runJob(job)
        finally:
            resetRequestId(token)
        return True

    # Runs one claimed job through its handler, then finishes it or schedules a retry, running the
    # handler's failure hook when the last attempt fails.
    def runJob(self, job):
        jobId, jobType = job["job_id"], job["job_type"]
        log.info("job_claimed job_id=%s job_type=%s attempt=%s", jobId, jobType, job["attempt"])
        handler = self.handlers.get(jobType)
        try:
            if handler is None:
                raise LookupError(UNKNOWN_JOB_TYPE)
            handler.run(job["payload"])
        except Exception as error:
            reason = str(error) if isinstance(error, LookupError) else type(error).__name__
            exhausted = jobs.failJob(jobId, job["attempt"], reason)
            if not exhausted:
                log.warning("job_retry job_id=%s job_type=%s attempt=%s error_type=%s", jobId, jobType, job["attempt"], reason)
                return
            log.error("job_failed job_id=%s job_type=%s attempt=%s error_type=%s", jobId, jobType, job["attempt"], reason)
            if handler is not None and handler.onExhausted is not None:
                self.runFailureHook(handler, job, reason)
            return
        jobs.finishJob(jobId)
        log.info("job_succeeded job_id=%s job_type=%s", jobId, jobType)

    # Runs a handler's failure hook, logging rather than raising when the hook itself fails.
    def runFailureHook(self, handler, job, reason):
        try:
            handler.onExhausted(job["payload"], reason)
        except Exception as error:
            log.error("job_failure_hook_failed job_id=%s error_type=%s", job["job_id"], type(error).__name__)

    # Loops until stopped: reclaims stale jobs at start and once a minute, runs due jobs, and sleeps
    # for the poll interval when none is due; a failed loop step is logged and retried after a sleep.
    def run(self):
        log.info("worker_started worker_id=%s", self.workerId)
        while not self.stopping.is_set():
            try:
                self.reclaimIfDue()
                ranJob = self.runOnce()
            except Exception as error:
                log.error("worker_loop_failed error_type=%s", type(error).__name__)
                ranJob = False
            if not ranJob:
                self.stopping.wait(self.pollSeconds)
        log.info("worker_stopped worker_id=%s", self.workerId)

# Returns an id naming this host and process, unique per worker instance.
def newWorkerId():
    return f"{socket.gethostname()}:{os.getpid()}:{uuid.uuid4().hex[:8]}"

# Returns a worker built from configuration and the registered handlers.
def buildWorker():
    return Worker(jobHandlers(), config.workerPollSeconds())

# Starts a worker in one daemon thread inside the API process and returns it with its thread.
def startEmbeddedWorker():
    worker = buildWorker()
    thread = threading.Thread(target=worker.run, name="embedded-worker", daemon=True)
    thread.start()
    return worker, thread

# Runs the worker in the foreground until SIGTERM or SIGINT; run from backend/ with python -m worker.main.
def main():
    configureLogging()
    config.requireStartupSettings()
    worker = buildWorker()
    for stopSignal in STOP_SIGNALS:
        signal.signal(stopSignal, lambda signum, frame: worker.stop())
    worker.run()


if __name__ == "__main__":
    main()


__all__ = ["Worker", "buildWorker", "main", "startEmbeddedWorker"]

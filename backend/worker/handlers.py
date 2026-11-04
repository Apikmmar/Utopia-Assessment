from dataclasses import dataclass
from typing import Callable, Optional
from modules.notification import service as notificationService
from modules.notification.constants import JOB_TYPE_DELIVER


@dataclass(frozen=True)
class JobHandler:
    run: Callable[[dict], None]
    onExhausted: Optional[Callable[[dict, str], None]] = None

# Returns the job type to handler map the worker dispatches by; feature handlers are added here.
def jobHandlers():
    return {
        JOB_TYPE_DELIVER: JobHandler(run=notificationService.deliverJob, onExhausted=notificationService.deliverJobExhausted),
    }


__all__ = ["JobHandler", "jobHandlers"]

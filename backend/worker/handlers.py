from dataclasses import dataclass
from typing import Callable, Optional


@dataclass(frozen=True)
class JobHandler:
    run: Callable[[dict], None]
    onExhausted: Optional[Callable[[dict, str], None]] = None

# Returns the job type to handler map the worker dispatches by; feature handlers are added here.
def jobHandlers():
    return {}


__all__ = ["JobHandler", "jobHandlers"]

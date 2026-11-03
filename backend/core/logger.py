import logging

from backend.core.request_context import currentRequestId

LOG_FORMAT = "%(asctime)s %(levelname)s [%(request_id)s] %(name)s: %(message)s"


class RequestIdFilter(logging.Filter):
    # Stamps every log record with the current request id, or "-" outside a request.
    def filter(self, record):
        record.request_id = currentRequestId() or "-"
        return True

# Configures root logging once so every record carries the request id.
def configureLogging(level=logging.INFO):
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter(LOG_FORMAT))
    handler.addFilter(RequestIdFilter())
    root = logging.getLogger()
    root.handlers = [handler]
    root.setLevel(level)

# Returns a named logger.
def getLogger(name):
    return logging.getLogger(name)


__all__ = ["RequestIdFilter", "configureLogging", "getLogger"]

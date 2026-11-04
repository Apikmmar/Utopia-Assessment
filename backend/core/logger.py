import logging
import re
import traceback
from core.request_context import currentRequestId

REDACTED_FIELDS = ("new_password", "newPassword", "password_hash", "passwordHash", "password", "token")
REDACTED_VALUE = "[redacted]"
SECRET_PATTERN = re.compile(
    r"""(["']?(?:new_password|newPassword|password_hash|passwordHash|password|token)["']?\s*[=:]\s*)("[^"]*"|'[^']*'|[^\s,}]+)""",
    re.IGNORECASE,
)
LOG_FORMAT = "%(asctime)s %(levelname)s [%(request_id)s] %(name)s: %(message)s"


class RequestIdFilter(logging.Filter):
    # Stamps every log record with the current request id, or "-" outside a request.
    def filter(self, record):
        record.request_id = currentRequestId() or "-"
        return True


class RedactionFilter(logging.Filter):
    # Masks secret-named fields, mapping arguments, and key=value text in the message and traceback.
    def filter(self, record):
        for name in REDACTED_FIELDS:
            if hasattr(record, name):
                setattr(record, name, REDACTED_VALUE)
        if isinstance(record.args, dict):
            record.args = {key: REDACTED_VALUE if key in REDACTED_FIELDS else value for key, value in record.args.items()}
        record.msg = redact(record.getMessage())
        record.args = None
        if record.exc_info and not record.exc_text:
            record.exc_text = redact("".join(traceback.format_exception(*record.exc_info)).rstrip("\n"))
        return True


class AppHandler(logging.StreamHandler):
    pass

# Replaces the value of every secret-named key=value pair in a text with the redaction marker.
def redact(text):
    return SECRET_PATTERN.sub(lambda match: match.group(1) + REDACTED_VALUE, text)

# Installs the application handler on the root logger once, leaving other handlers in place.
def configureLogging(level=logging.INFO):
    handler = AppHandler()
    handler.setFormatter(logging.Formatter(LOG_FORMAT))
    handler.addFilter(RequestIdFilter())
    handler.addFilter(RedactionFilter())
    root = logging.getLogger()
    root.handlers = [existing for existing in root.handlers if not isinstance(existing, AppHandler)] + [handler]
    root.setLevel(level)

# Returns a named logger.
def getLogger(name):
    return logging.getLogger(name)


__all__ = ["AppHandler", "RedactionFilter", "RequestIdFilter", "configureLogging", "getLogger", "redact"]

import re
import uuid
from contextvars import ContextVar

REQUEST_ID_HEADER = "X-Request-ID"
REQUEST_ID_MAX_LENGTH = 100
REQUEST_ID_PATTERN = re.compile(r"[A-Za-z0-9._-]+")

_requestId = ContextVar("requestId", default=None)

# Returns a fresh server-generated request id.
def newRequestId():
    return uuid.uuid4().hex

# Returns a client-supplied id only when it is short and made of safe characters, else None.
def sanitizeRequestId(value):
    if not value or len(value) > REQUEST_ID_MAX_LENGTH or not REQUEST_ID_PATTERN.fullmatch(value):
        return None
    return value

# Returns the request id bound to the current context, or None outside a request.
def currentRequestId():
    return _requestId.get()

# Binds a request id to the current context and returns the token needed to reset it.
def bindRequestId(requestId):
    return _requestId.set(requestId)

# Restores the context to what it was before the matching bindRequestId call.
def resetRequestId(token):
    _requestId.reset(token)


__all__ = [
    "REQUEST_ID_HEADER",
    "REQUEST_ID_MAX_LENGTH",
    "bindRequestId",
    "currentRequestId",
    "newRequestId",
    "resetRequestId",
    "sanitizeRequestId",
]

import asyncio
import logging
import re
from functools import partial
import pytest
from core.logger import RequestIdFilter
from core.middleware import RequestIdMiddleware
from core.request_context import currentRequestId, sanitizeRequestId

GENERATED_ID = re.compile(r"[0-9a-f]{32}")


class RecordingApp:
    # Starts with no request id seen.
    def __init__(self):
        self.seenId = None
        self.seenScope = None

    # Records the bound request id and scope, then answers an empty 200.
    async def __call__(self, scope, receive, send):
        self.seenId = currentRequestId()
        self.seenScope = scope
        await send({"type": "http.response.start", "status": 200, "headers": []})
        await send({"type": "http.response.body", "body": b""})

# Answers the request body read with an empty request.
async def receiveRequest():
    return {"type": "http.request"}

# Runs one fake HTTP request through the middleware and returns the app and the response headers.
def callMiddleware(headers):
    app = RecordingApp()
    sent = []
    asyncio.run(RequestIdMiddleware(app)({"type": "http", "headers": headers}, receiveRequest, partial(recordMessage, sent)))
    return app, dict(sent[0]["headers"])

# Collects one message the middleware sends.
async def recordMessage(sent, message):
    sent.append(message)

# A safe client id is kept, echoed back, and stored on the scope for the error handlers.
def testKeepsSafeClientId():
    app, headers = callMiddleware([(b"x-request-id", b"abc-123_X.y")])
    assert app.seenId == "abc-123_X.y"
    assert headers[b"x-request-id"] == b"abc-123_X.y"
    assert app.seenScope["state"]["requestId"] == "abc-123_X.y"

# A missing id is replaced by a generated 32-character hex id.
def testGeneratesIdWhenAbsent():
    app, headers = callMiddleware([])
    assert GENERATED_ID.fullmatch(app.seenId)
    assert headers[b"x-request-id"] == app.seenId.encode()

# Unsafe or oversized client ids are discarded and replaced.
@pytest.mark.parametrize("bad", ["has space", "new\nline", "a" * 101, "semi;colon", ""])
def testRejectsUnsafeClientIds(bad):
    assert sanitizeRequestId(bad) is None
    app, _ = callMiddleware([(b"x-request-id", bad.encode())])
    assert GENERATED_ID.fullmatch(app.seenId)

# The id is cleared after the request finishes.
def testContextClearedAfterRequest():
    callMiddleware([(b"x-request-id", b"abc")])
    assert currentRequestId() is None

# A boundary-length id of exactly 100 characters is accepted.
def testAcceptsBoundaryLength():
    assert sanitizeRequestId("a" * 100) == "a" * 100

# Log records carry the dash placeholder outside a request.
def testLogFilterUsesDashOutsideRequest():
    record = logging.LogRecord("n", logging.INFO, "p", 1, "m", None, None)
    RequestIdFilter().filter(record)
    assert record.request_id == "-"

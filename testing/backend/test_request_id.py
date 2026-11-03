import asyncio
import logging
import unittest

from backend.api.middleware import RequestIdMiddleware
from backend.core.logger import RequestIdFilter
from backend.core.request_context import currentRequestId, sanitizeRequestId


# Runs one fake HTTP request through the middleware and returns the id seen inside and the response headers.
def callMiddleware(headers):
    seen = {}

    async def app(scope, receive, send):
        seen["id"] = currentRequestId()
        await send({"type": "http.response.start", "status": 200, "headers": []})
        await send({"type": "http.response.body", "body": b""})

    sent = []

    async def send(message):
        sent.append(message)

    async def receive():
        return {"type": "http.request"}

    scope = {"type": "http", "headers": headers}
    asyncio.run(RequestIdMiddleware(app)(scope, receive, send))
    return seen["id"], dict(sent[0]["headers"])


class RequestIdTests(unittest.TestCase):
    # A safe client id is kept and echoed back.
    def test_keeps_safe_client_id(self) -> None:
        seenId, headers = callMiddleware([(b"x-request-id", b"abc-123_X.y")])
        self.assertEqual(seenId, "abc-123_X.y")
        self.assertEqual(headers[b"x-request-id"], b"abc-123_X.y")

    # A missing id is replaced by a generated 32-char hex id.
    def test_generates_id_when_absent(self) -> None:
        seenId, headers = callMiddleware([])
        self.assertRegex(seenId, r"^[0-9a-f]{32}$")
        self.assertEqual(headers[b"x-request-id"], seenId.encode())

    # Unsafe or oversized client ids are discarded and replaced.
    def test_rejects_unsafe_client_ids(self) -> None:
        for bad in ("has space", "new\nline", "a" * 101, "semi;colon", ""):
            self.assertIsNone(sanitizeRequestId(bad))
            seenId, _ = callMiddleware([(b"x-request-id", bad.encode())])
            self.assertRegex(seenId, r"^[0-9a-f]{32}$")

    # The id is cleared after the request finishes.
    def test_context_cleared_after_request(self) -> None:
        callMiddleware([(b"x-request-id", b"abc")])
        self.assertIsNone(currentRequestId())

    # A boundary-length id of exactly 100 chars is accepted.
    def test_accepts_boundary_length(self) -> None:
        self.assertEqual(sanitizeRequestId("a" * 100), "a" * 100)

    # Log records carry the dash placeholder outside a request.
    def test_log_filter_uses_dash_outside_request(self) -> None:
        record = logging.LogRecord("n", logging.INFO, "p", 1, "m", None, None)
        RequestIdFilter().filter(record)
        self.assertEqual(record.request_id, "-")


if __name__ == "__main__":
    unittest.main()

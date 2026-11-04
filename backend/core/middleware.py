import json
from functools import partial
from urllib.parse import urlsplit
from core import config
from core.error import BAD_ORIGIN_CODE, errorBody
from core.request_context import REQUEST_ID_HEADER, bindRequestId, newRequestId, resetRequestId, sanitizeRequestId

HEADER_KEY = REQUEST_ID_HEADER.lower().encode("latin-1")
UNSAFE_METHODS = frozenset({"POST", "PATCH", "PUT", "DELETE"})
BAD_ORIGIN_MESSAGE = "Request origin is not allowed."
BAD_ORIGIN_BODY = json.dumps(errorBody(BAD_ORIGIN_MESSAGE, BAD_ORIGIN_CODE)).encode("utf-8")

# Sends one ASGI message, replacing any request id header on the response start with this request's id.
async def sendWithRequestId(send, requestId, message):
    if message["type"] == "http.response.start":
        headers = [pair for pair in message.get("headers", []) if pair[0].lower() != HEADER_KEY]
        headers.append((HEADER_KEY, requestId.encode("latin-1")))
        message = {**message, "headers": headers}
    await send(message)


class RequestIdMiddleware:
    # Stores the wrapped ASGI application.
    def __init__(self, app):
        self.app = app

    # Binds one request id per HTTP request, keeps it on the scope, and echoes it in the response header.
    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        requestId = sanitizeRequestId(self.incomingId(scope)) or newRequestId()
        scope.setdefault("state", {})["requestId"] = requestId
        token = bindRequestId(requestId)
        try:
            await self.app(scope, receive, partial(sendWithRequestId, send, requestId))
        finally:
            resetRequestId(token)

    # Reads the client-supplied request id header, decoded, or None.
    @staticmethod
    def incomingId(scope):
        for key, value in scope.get("headers", []):
            if key.lower() == HEADER_KEY:
                return value.decode("latin-1")
        return None


class OriginCheckMiddleware:
    # Stores the wrapped ASGI application.
    def __init__(self, app):
        self.app = app

    # Rejects state-changing requests whose Origin or Referer is not the allowed origin.
    async def __call__(self, scope, receive, send):
        if scope["type"] != "http" or scope["method"] not in UNSAFE_METHODS:
            await self.app(scope, receive, send)
            return
        if self.requestOrigin(scope) == config.allowedOrigin():
            await self.app(scope, receive, send)
            return
        await send({
            "type": "http.response.start", "status": 403,
            "headers": [(b"content-type", b"application/json"), (b"content-length", str(len(BAD_ORIGIN_BODY)).encode("latin-1"))],
        })
        await send({"type": "http.response.body", "body": BAD_ORIGIN_BODY})

    # Returns the Origin header, or the origin part of Referer when Origin is absent.
    @staticmethod
    def requestOrigin(scope):
        headers = {key.lower(): value.decode("latin-1") for key, value in scope.get("headers", [])}
        origin = headers.get(b"origin")
        if origin is not None:
            return origin.rstrip("/")
        referer = headers.get(b"referer")
        if not referer:
            return None
        parts = urlsplit(referer)
        return f"{parts.scheme}://{parts.netloc}" if parts.scheme and parts.netloc else None


__all__ = ["OriginCheckMiddleware", "RequestIdMiddleware"]

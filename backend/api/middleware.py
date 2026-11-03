from backend.core.request_context import (
    REQUEST_ID_HEADER,
    bindRequestId,
    newRequestId,
    resetRequestId,
    sanitizeRequestId,
)

HEADER_KEY = REQUEST_ID_HEADER.lower().encode("latin-1")


class RequestIdMiddleware:
    # Stores the wrapped ASGI application.
    def __init__(self, app):
        self.app = app

    # Binds one request id per HTTP request and echoes it in the response header.
    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        requestId = sanitizeRequestId(self.incomingId(scope)) or newRequestId()
        token = bindRequestId(requestId)

        # Adds the request id header to the response start message.
        async def sendWithId(message):
            if message["type"] == "http.response.start":
                headers = [pair for pair in message.get("headers", []) if pair[0].lower() != HEADER_KEY]
                headers.append((HEADER_KEY, requestId.encode("latin-1")))
                message = {**message, "headers": headers}
            await send(message)

        try:
            await self.app(scope, receive, sendWithId)
        finally:
            resetRequestId(token)

    # Reads the client-supplied request id header, decoded or None.
    @staticmethod
    def incomingId(scope):
        for key, value in scope.get("headers", []):
            if key.lower() == HEADER_KEY:
                return value.decode("latin-1")
        return None


__all__ = ["RequestIdMiddleware"]

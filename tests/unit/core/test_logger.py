import logging
import sys
from core.logger import AppHandler, RedactionFilter, configureLogging

# Builds one log record with the given message, arguments, and exception.
def logRecord(message, args=None, excInfo=None):
    return logging.LogRecord("n", logging.ERROR, "p", 1, message, args, excInfo)

# Returns a record carrying a traceback of an exception whose message holds a secret.
def recordWithTraceback():
    try:
        raise RuntimeError("password=hunter2")
    except RuntimeError:
        return logRecord("unhandled", excInfo=sys.exc_info())

# Secret-named extras and key=value text in the message are masked.
def testMasksExtrasAndKeyValueText():
    record = logRecord("login password=hunter2 token: abc newPassword=xyz")
    record.new_password = "hunter2"
    RedactionFilter().filter(record)
    message = record.getMessage()
    for secret in ("hunter2", "abc", "xyz"):
        assert secret not in message
    assert record.new_password == "[redacted]"

# Mapping arguments named like secrets are masked while other arguments survive.
def testMasksMappingArguments():
    record = logRecord("%(password)s %(name)s", ({"password": "hunter2", "name": "ok"},))
    RedactionFilter().filter(record)
    assert record.getMessage() == "[redacted] ok"

# A quoted JSON secret is masked.
def testMasksQuotedJsonValue():
    record = logRecord('{"password_hash": "$argon2id$x"}')
    RedactionFilter().filter(record)
    assert "argon2id" not in record.getMessage()

# Secrets in an attached traceback are masked before the formatter renders it.
def testMasksTracebackText():
    record = recordWithTraceback()
    RedactionFilter().filter(record)
    rendered = logging.Formatter().format(record)
    assert "RuntimeError" in rendered
    assert "hunter2" not in rendered

# Configuring twice keeps one application handler and leaves foreign handlers in place.
def testConfigureLoggingIsIdempotentAndKeepsOtherHandlers():
    root = logging.getLogger()
    original = list(root.handlers)
    foreign = logging.NullHandler()
    root.addHandler(foreign)
    try:
        configureLogging()
        configureLogging()
        assert sum(isinstance(handler, AppHandler) for handler in root.handlers) == 1
        assert foreign in root.handlers
    finally:
        root.handlers = original

# Bearer and apikey header values and bare JWTs, the forms the service role key travels in, are masked.
def testMasksCredentialHeadersAndJwts():
    jwt = "eyJhbGciOiJIUzI1NiJ9.eyJyb2xlIjoic2VydmljZV9yb2xlIn0.c2lnbmF0dXJl"
    text = f"headers Authorization: Bearer {jwt} apikey: {jwt} raw {jwt} order ORD-000123"
    record = logRecord(text)
    RedactionFilter().filter(record)
    assert jwt not in record.getMessage() and "eyJ" not in record.getMessage()
    assert "ORD-000123" in record.getMessage()

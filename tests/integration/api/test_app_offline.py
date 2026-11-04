import logging
import re
import pytest
from fastapi import APIRouter, Depends
from fastapi.testclient import TestClient
from sqlalchemy.exc import OperationalError
from api.main import assertRoutesProtected, featureRouters
from core import db as coreDb
from core.auth import requireRole
from tests.support import ORIGIN, STATE_HEADERS

EMAIL = "offline.test@example.com"
GENERATED_ID = re.compile(r"[0-9a-f]{32}")


class BrokenEngine:
    # Fails every connection attempt the way an unreachable database does.
    def connect(self):
        raise OperationalError("SELECT 1", {}, Exception("db down"))

    # Fails every transaction attempt the way an unreachable database does.
    def begin(self):
        raise OperationalError("SELECT 1", {}, Exception("db down"))

# Raises an unexpected error carrying a secret-looking message.
def explode():
    raise RuntimeError("password=hunter2 exploded")

# Points the application at a database that cannot be reached.
@pytest.fixture
def brokenDatabase(monkeypatch):
    monkeypatch.setattr(coreDb, "getEngine", lambda: BrokenEngine())

# A client for the real app that never needs the database.
@pytest.fixture
def client(app):
    return TestClient(app)

# The info route is public, answers without a database, and carries a request id.
def testInfoIsPublicLiveness(client, brokenDatabase):
    response = client.get("/info")
    assert response.status_code == 200
    assert response.json()["app"] == "Utopia"
    assert GENERATED_ID.fullmatch(response.headers["x-request-id"])

# The health route reports the database as down with 503 when it cannot be reached.
def testHealthReportsDatabaseDown(client, brokenDatabase):
    response = client.get("/health")
    assert (response.status_code, response.json()) == (503, {"status": "down", "checks": {"db": "error"}})

# A state-changing request without Origin or with another origin is rejected with BAD_ORIGIN.
@pytest.mark.parametrize("headers", [{}, {"Origin": "https://evil.example"}, {"Origin": "null"}, {"Referer": "https://evil.example/page"}])
def testBadOriginRejected(client, headers):
    response = client.post("/auth/login", json={"email": EMAIL, "password": "whatever-password"}, headers=headers)
    assert response.status_code == 403
    assert response.json() == {"detail": "Request origin is not allowed.", "code": "BAD_ORIGIN"}
    assert "x-request-id" in response.headers

# A matching Referer is accepted when Origin is absent, and a safe method needs no origin.
def testRefererAndSafeMethodsPassOriginCheck(client):
    assert client.post("/auth/logout", headers={"Referer": ORIGIN + "/some/page"}).status_code == 401
    assert client.get("/auth/me").status_code == 401

# Every other state-changing method is checked too.
@pytest.mark.parametrize("method", ["PUT", "PATCH", "DELETE"])
def testOtherUnsafeMethodsChecked(client, method):
    response = client.request(method, "/anything", headers={"Origin": "https://evil.example"})
    assert (response.status_code, response.json()["code"]) == (403, "BAD_ORIGIN")

# A protected route without a session cookie answers 401 NOT_AUTHENTICATED.
def testProtectedRouteWithoutSessionIs401(client):
    response = client.get("/auth/me")
    assert response.status_code == 401
    assert response.json() == {"detail": "Authentication required.", "code": "NOT_AUTHENTICATED"}

# Validation failures return 422 with camelCase field names, reject unknown fields, and never echo the password.
@pytest.mark.parametrize("body,field", [
    ({"email": "not-an-email", "password": "secret-value-xyz"}, "email"),
    ({"password": "secret-value-xyz"}, "email"),
    ({"email": EMAIL}, "password"),
    ({"email": EMAIL, "password": "secret-value-xyz", "role": "admin"}, "role"),
    ({"email": EMAIL, "password": ""}, "password"),
])
def testLoginValidationErrors(client, body, field):
    response = client.post("/auth/login", json=body, headers=STATE_HEADERS)
    assert response.status_code == 422
    payload = response.json()
    assert (payload["code"], payload["detail"]) == ("VALIDATION_FAILED", "Request validation failed.")
    assert field in payload["fields"]
    assert "secret-value-xyz" not in response.text

# A reset body is read in camelCase, so the snake_case field name is an unknown field.
def testResetRequiresCamelCaseField(client):
    response = client.post("/auth/password/reset", json={"email": EMAIL, "newPassword": "short"}, headers=STATE_HEADERS)
    assert (response.status_code, response.json()["code"], response.json()["fields"]) == (422, "WEAK_PASSWORD", {"newPassword": "too_short"})

# Unknown routes and methods use the shared error shape.
def testUnknownRouteErrorShape(client):
    response = client.get("/nope")
    assert response.status_code == 404
    assert response.json() == {"detail": "Not Found", "code": "NOT_FOUND"}
    assert client.get("/auth/login").json()["code"] == "METHOD_NOT_ALLOWED"

# An unreachable database returns 503 SERVICE_UNAVAILABLE with no detail.
def testDatabaseDownReturns503(client, brokenDatabase):
    response = client.post("/auth/login", json={"email": EMAIL, "password": "whatever-password"}, headers=STATE_HEADERS)
    assert response.status_code == 503
    assert response.json() == {"detail": "Service temporarily unavailable.", "code": "SERVICE_UNAVAILABLE"}
    assert "db down" not in response.text

# An unexpected error answers 500 with the request id as correlation id, logs it, and hides the message.
def testUnhandledErrorReturnsCorrelationId(app, caplog):
    app.add_api_route("/explode", explode, methods=["GET"])
    with caplog.at_level(logging.ERROR):
        response = TestClient(app, raise_server_exceptions=False).get("/explode", headers={"X-Request-ID": "trace-42", "Origin": ORIGIN})
    assert response.status_code == 500
    assert response.json() == {"detail": "Internal server error.", "code": "INTERNAL_ERROR", "correlationId": "trace-42"}
    assert response.headers["x-request-id"] == "trace-42"
    assert response.headers["access-control-allow-origin"] == ORIGIN
    assert "hunter2" not in response.text
    assert any("unhandled_exception" in record.getMessage() and record.exc_info for record in caplog.records)

# The CORS allow list contains only the configured origin and never a wildcard.
def testCorsAllowsOnlyConfiguredOrigin(client):
    allowed = client.options("/auth/login", headers={"Origin": ORIGIN, "Access-Control-Request-Method": "POST"})
    assert allowed.headers["access-control-allow-origin"] == ORIGIN
    denied = client.options("/auth/login", headers={"Origin": "https://evil.example", "Access-Control-Request-Method": "POST"})
    assert "access-control-allow-origin" not in denied.headers

# The registered routes are all protected or on the allow list, and docs are not exposed.
@pytest.mark.parametrize("path", ["/docs", "/redoc", "/openapi.json"])
def testRouteTableIsProtectedAndDocsHidden(client, path):
    assertRoutesProtected(featureRouters())
    assert client.get(path).status_code == 404

# A route without an auth dependency is detected, while a role-gated one passes.
def testUnprotectedRouteDetected():
    leaking = APIRouter()
    leaking.add_api_route("/leak", explode, methods=["GET"])
    with pytest.raises(RuntimeError, match="GET /leak"):
        assertRoutesProtected([leaking])
    gated = APIRouter()
    gated.add_api_route("/ok", explode, methods=["GET"], dependencies=[Depends(requireRole("admin"))])
    assertRoutesProtected([gated])

# The list route checks the session before it reports a bad page size, so anonymous callers learn nothing.
def testListUsersAnonymousIs401EvenWithBadPaging(client):
    assert client.get("/users", params={"pageSize": 500}).status_code == 401

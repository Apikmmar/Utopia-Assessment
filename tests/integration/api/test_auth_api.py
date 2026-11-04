import logging
import pytest
from fastapi import APIRouter, Depends
from fastapi.testclient import TestClient
from core.auth import requireRole
from tests.support import COOKIE, STATE_HEADERS, STRONG_PASSWORD

EMAIL = "auth.api.test@example.com"
ADMIN_EMAIL = "auth.api.admin@example.com"
NO_HASH_EMAIL = "auth.api.nohash@example.com"
NEW_PASSWORD = "a-brand-new-password"
INVALID_BODY = {"detail": "Invalid email or password.", "code": "INVALID_CREDENTIALS"}
RESET_BODY = {"message": "If the account exists, the password was updated."}


# Answers with the email of an admin caller.
def adminOnly(user=Depends(requireRole("admin"))):
    return {"email": user.email}

# Answers with the role of an admin or technician caller.
def staffOnly(user=Depends(requireRole("admin", "technician"))):
    return {"role": user.roleCode}

# Seeds a technician, an admin, and a manager without a password, returning their ids by role.
@pytest.fixture
def users(seedUser):
    return {
        "technician": seedUser(EMAIL, "technician", name="Tech One"),
        "admin": seedUser(ADMIN_EMAIL, "admin", name="Admin One"),
        "manager": seedUser(NO_HASH_EMAIL, "manager", password=None),
    }

# The real app plus two role-gated probe routes.
@pytest.fixture
def gatedApp(app, users):
    gated = APIRouter()
    gated.add_api_route("/admin-only", adminOnly, methods=["GET"])
    gated.add_api_route("/staff", staffOnly, methods=["GET"])
    app.include_router(gated)
    return app

# Sends one login request from a fresh client.
def postLogin(app, email, password=STRONG_PASSWORD):
    return TestClient(app).post("/auth/login", json={"email": email, "password": password}, headers=STATE_HEADERS)

# Sends one password reset request from a fresh client.
def postReset(app, body):
    return TestClient(app).post("/auth/password/reset", json=body, headers=STATE_HEADERS)

# Login returns 200 with only the four camelCase user fields and a cookie carrying every required attribute.
def testLoginSuccessBodyAndCookie(app, users):
    response = postLogin(app, "  AUTH.api.test@example.com")
    assert response.status_code == 200
    assert response.json() == {"user": {"userId": str(users["technician"]), "name": "Tech One", "email": EMAIL, "roleCode": "technician"}}
    cookie = response.headers["set-cookie"]
    assert cookie.startswith(f"{COOKIE}=") and len(response.cookies[COOKIE]) == 43
    lowered = cookie.lower()
    for attribute in ("httponly", "samesite=lax", "path=/", "max-age=43200"):
        assert attribute in lowered
    assert "secure" not in lowered
    for forbidden in (response.cookies[COOKIE], "argon2", "password_hash", "passwordHash", "token_hash"):
        assert forbidden not in response.text

# The Secure attribute is present when the cookie setting is on.
def testCookieSecureWhenEnabled(app, users, monkeypatch):
    monkeypatch.setenv("AUTH_COOKIE_SECURE", "true")
    assert "secure" in postLogin(app, EMAIL).headers["set-cookie"].lower()

# Wrong password, unknown email, and a user without a hash give the identical 401 body and no cookie.
@pytest.mark.parametrize("email,password", [(EMAIL, "wrong-password-value"), ("nobody@example.com", STRONG_PASSWORD), (NO_HASH_EMAIL, STRONG_PASSWORD)])
def testLoginFailuresAreIndistinguishable(app, users, email, password):
    response = postLogin(app, email, password)
    assert (response.status_code, response.json()) == (401, INVALID_BODY)
    assert "set-cookie" not in response.headers

# The session cookie authenticates /auth/me and the response carries no secrets.
def testMeReturnsCurrentUser(users, loggedIn):
    response = loggedIn(EMAIL).get("/auth/me")
    assert response.status_code == 200
    assert response.json()["user"]["email"] == EMAIL
    assert "password" not in response.text.lower()

# An invalid cookie value is a 401.
def testMeWithInvalidCookieIs401(app, users):
    client = TestClient(app)
    client.cookies.set(COOKIE, "forged-token-value")
    assert client.get("/auth/me").json()["code"] == "NOT_AUTHENTICATED"

# An expired session is a 401.
def testExpiredSessionIs401(users, loggedIn, execute):
    client = loggedIn(EMAIL)
    execute("UPDATE session SET expires_at = now() - interval '1 second'")
    assert client.get("/auth/me").status_code == 401

# Logout returns 204, expires the cookie, and revokes the session server-side.
def testLogoutRevokesAndClearsCookie(app, users, loggedIn):
    client = loggedIn(EMAIL)
    stolen = client.cookies.get(COOKIE)
    response = client.post("/auth/logout", headers=STATE_HEADERS)
    assert (response.status_code, response.content) == (204, b"")
    lowered = response.headers["set-cookie"].lower()
    assert "max-age=0" in lowered and f"{COOKIE}=" in lowered
    replay = TestClient(app)
    replay.cookies.set(COOKIE, stolen)
    assert replay.get("/auth/me").status_code == 401

# Logout without a session is a 401.
def testLogoutWithoutSessionIs401(app, users):
    response = TestClient(app).post("/auth/logout", headers=STATE_HEADERS)
    assert (response.status_code, response.json()["code"]) == (401, "NOT_AUTHENTICATED")

# A reset answers the same generic message for known and unknown emails and revokes sessions.
def testResetIsGenericAndRevokesSessions(app, users, loggedIn):
    client = loggedIn(EMAIL)
    known = postReset(app, {"email": EMAIL, "newPassword": NEW_PASSWORD})
    unknown = postReset(app, {"email": "nobody@example.com", "newPassword": NEW_PASSWORD})
    assert (known.status_code, known.json()) == (200, RESET_BODY)
    assert (unknown.status_code, unknown.json()) == (200, RESET_BODY)
    assert client.get("/auth/me").status_code == 401
    loggedIn(EMAIL, NEW_PASSWORD)
    assert postLogin(app, EMAIL).status_code == 401

# A weak new password returns 422 WEAK_PASSWORD on newPassword and changes nothing.
@pytest.mark.parametrize("weak", ["short", "password123", "x" * 129])
def testResetWeakPasswordIs422(app, users, loggedIn, weak):
    client = loggedIn(EMAIL)
    response = postReset(app, {"email": EMAIL, "newPassword": weak})
    assert response.status_code == 422
    assert response.json()["code"] == "WEAK_PASSWORD"
    assert "newPassword" in response.json()["fields"]
    assert client.get("/auth/me").status_code == 200

# A reset body with an unknown field, a snake_case field, or an invalid email is rejected.
@pytest.mark.parametrize("body", [
    {"email": EMAIL, "newPassword": NEW_PASSWORD, "role": "admin"},
    {"email": "bad", "newPassword": NEW_PASSWORD},
])
def testResetRejectsUnknownFieldsAndBadEmail(app, users, body):
    response = postReset(app, body)
    assert (response.status_code, response.json()["code"]) == (422, "VALIDATION_FAILED")

# Role gates admit allowed roles, return 403 FORBIDDEN otherwise, and 401 without a session.
def testRoleGates(gatedApp, loggedIn):
    admin, technician = loggedIn(ADMIN_EMAIL), loggedIn(EMAIL)
    assert admin.get("/admin-only").json() == {"email": ADMIN_EMAIL}
    forbidden = technician.get("/admin-only")
    assert (forbidden.status_code, forbidden.json()["code"]) == (403, "FORBIDDEN")
    assert technician.get("/staff").json() == {"role": "technician"}
    assert TestClient(gatedApp).get("/admin-only").status_code == 401

# A role change takes effect on the next request because the role is read from the database.
def testRoleChangeAppliesToNextRequest(gatedApp, users, loggedIn, execute):
    technician = loggedIn(EMAIL)
    assert technician.get("/admin-only").status_code == 403
    execute('UPDATE "user" SET role_id = (SELECT role_id FROM role WHERE role_code = \'admin\') WHERE user_id = :u', u=users["technician"])
    assert technician.get("/admin-only").status_code == 200

# One user's cookie never yields another user's identity.
def testCookieBelongsToItsUser(users, loggedIn):
    first, second = loggedIn(EMAIL), loggedIn(ADMIN_EMAIL)
    assert first.get("/auth/me").json()["user"]["userId"] == str(users["technician"])
    assert second.get("/auth/me").json()["user"]["userId"] == str(users["admin"])

# Neither the submitted passwords nor the issued token appear in captured log output.
def testLogsNeverContainSecrets(app, users, loggedIn, caplog):
    probes = ["log-probe-password-1", "log-probe-new-password-2"]
    with caplog.at_level(logging.DEBUG):
        token = loggedIn(EMAIL).cookies.get(COOKIE)
        postLogin(app, EMAIL, probes[0])
        postReset(app, {"email": EMAIL, "newPassword": probes[1]})
    output = "\n".join(record.getMessage() for record in caplog.records)
    for secret in [*probes, STRONG_PASSWORD, token, "argon2"]:
        assert secret not in output
    assert "login_succeeded" in output

# The cookie value is never written to the database, only its hash.
def testTokenNotStoredRaw(users, loggedIn, scalar):
    token = loggedIn(EMAIL).cookies.get(COOKIE)
    stored = scalar("SELECT token_hash FROM session WHERE user_id = :u", u=users["technician"])
    assert stored != token and len(stored) == 64

# The health route answers ok when the database is reachable.
def testHealthReportsDatabaseUp(app, appDb):
    response = TestClient(app).get("/health")
    assert (response.status_code, response.json()) == (200, {"status": "ok", "checks": {"db": "ok"}})

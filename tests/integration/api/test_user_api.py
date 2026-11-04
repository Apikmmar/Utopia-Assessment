import pytest
from fastapi.testclient import TestClient
from tests.support import MISSING_ID, STATE_HEADERS, STRONG_PASSWORD

ADMIN_EMAIL = "admin.users.test@example.com"
TECH_EMAIL = "tech.api@example.com"
USER_FIELDS = {"userId", "name", "email", "phone", "age", "roleCode", "createdAt"}


# Seeds an admin and a technician and returns their ids.
@pytest.fixture
def ids(seedUser):
    return {"admin": seedUser(ADMIN_EMAIL, "admin", name="Admin"), "tech": seedUser(TECH_EMAIL, "technician", phone="12345678", name="Tech")}

# A client logged in as the admin.
@pytest.fixture
def admin(ids, loggedIn):
    return loggedIn(ADMIN_EMAIL)

# A client logged in as the technician.
@pytest.fixture
def tech(ids, loggedIn):
    return loggedIn(TECH_EMAIL)

# Returns the camelCase payload for a valid user creation, with overrides.
def userPayload(**overrides):
    payload = {"name": "New Person", "email": "new.person@example.com", "phone": None, "age": 30, "roleCode": "manager", "password": STRONG_PASSWORD}
    payload.update(overrides)
    return payload

# Sends one request with the origin header and returns the response.
def send(client, method, path, body=None):
    return client.request(method, path, json=body, headers=STATE_HEADERS)

# Every route is 401 without a session and 403 for a technician.
def testEveryRouteRejectsAnonymousAndNonAdmin(app, ids, tech):
    routes = [("POST", "/users", userPayload()), ("GET", "/users", None), ("GET", f"/users/{ids['tech']}", None), ("PATCH", f"/users/{ids['tech']}", {"name": "X"})]
    anonymous = TestClient(app)
    for method, path, body in routes:
        assert send(anonymous, method, path, body).status_code == 401, (method, path)
        assert send(tech, method, path, body).status_code == 403, (method, path)

# Creating a user returns 201 with the camelCase public fields and no credential.
def testCreateUserReturns201WithoutHash(admin):
    response = send(admin, "POST", "/users", userPayload(phone="+44 7700-900123"))
    assert response.status_code == 201, response.text
    body = response.json()
    assert set(body) == USER_FIELDS
    assert (body["phone"], body["roleCode"]) == ("447700900123", "manager")
    assert "password" not in response.text.lower()

# The new user can log in with the password they were given.
def testCreatedUserCanLogIn(admin, loggedIn):
    send(admin, "POST", "/users", userPayload())
    loggedIn("new.person@example.com")

# Validation failures use the shared body with a camelCase fields map.
@pytest.mark.parametrize("overrides,field,code", [
    ({"name": ""}, "name", "VALIDATION_FAILED"),
    ({"email": "bad"}, "email", "VALIDATION_FAILED"),
    ({"phone": "123"}, "phone", "VALIDATION_FAILED"),
    ({"age": 15}, "age", "VALIDATION_FAILED"),
    ({"age": 101}, "age", "VALIDATION_FAILED"),
    ({"password": "short"}, "password", "VALIDATION_FAILED"),
    ({"roleCode": "nobody"}, "roleCode", "INVALID_ROLE"),
    ({"roleCode": "technician", "phone": None}, "phone", "VALIDATION_FAILED"),
    ({"age": "old"}, "age", "VALIDATION_FAILED"),
    ({"isAdmin": True}, "isAdmin", "VALIDATION_FAILED"),
])
def testValidationErrorsHaveFieldsMap(admin, overrides, field, code):
    response = send(admin, "POST", "/users", userPayload(**overrides))
    assert response.status_code == 422
    assert response.json()["code"] == code
    assert field in response.json()["fields"]

# A duplicate email is 409 EMAIL_TAKEN.
def testDuplicateEmailIs409(admin):
    send(admin, "POST", "/users", userPayload())
    response = send(admin, "POST", "/users", userPayload(email="NEW.person@example.com"))
    assert (response.status_code, response.json()["code"]) == (409, "EMAIL_TAKEN")

# Search, role filter, and paging over the list route with camelCase query parameters and envelope.
def testListSearchFilterAndPaging(admin, seedUser):
    for index in range(4):
        seedUser(f"zeta{index}@example.com", "manager", name=f"Zeta {index}")
    page = admin.get("/users", params={"search": "zeta", "pageSize": 3}).json()
    assert (page["total"], len(page["items"]), page["page"], page["pageSize"]) == (4, 3, 1, 3)
    assert set(page["items"][0]) == USER_FIELDS
    second = admin.get("/users", params={"search": "zeta", "pageSize": 3, "page": 2}).json()
    assert len(second["items"]) == 1
    techs = admin.get("/users", params={"roleCode": "technician"}).json()
    assert [item["email"] for item in techs["items"]] == [TECH_EMAIL]

# The list order is created_at then user_id, stable across calls.
def testListOrderIsStable(admin):
    first = [item["userId"] for item in admin.get("/users").json()["items"]]
    assert first == [item["userId"] for item in admin.get("/users").json()["items"]]

# A page size above 100, a page below 1, or a non-integer page is 422 on its camelCase name.
@pytest.mark.parametrize("params,field", [({"pageSize": 101}, "pageSize"), ({"page": 0}, "page"), ({"page": "x"}, "page")])
def testPagingBounds(admin, params, field):
    response = admin.get("/users", params=params)
    assert (response.status_code, response.json()["code"]) == (422, "VALIDATION_FAILED")
    assert field in response.json()["fields"]
    assert admin.get("/users", params={"pageSize": 100}).status_code == 200

# No list or get response carries a password hash.
def testNoPasswordHashInResponses(admin, ids):
    for path in ("/users", f"/users/{ids['tech']}"):
        text = admin.get(path).text
        assert "password" not in text.lower() and "argon2" not in text

# A missing user is 404 USER_NOT_FOUND and a malformed id is 422.
def testGetMissingAndMalformedId(admin):
    missing = admin.get(f"/users/{MISSING_ID}")
    assert (missing.status_code, missing.json()["code"]) == (404, "USER_NOT_FOUND")
    assert admin.get("/users/not-a-uuid").status_code == 422

# Patching details updates only those fields.
def testPatchDetails(admin, ids):
    response = send(admin, "PATCH", f"/users/{ids['tech']}", {"name": "Renamed", "age": 33})
    assert response.status_code == 200, response.text
    assert (response.json()["name"], response.json()["age"], response.json()["email"]) == ("Renamed", 33, TECH_EMAIL)

# Email and password cannot be edited.
@pytest.mark.parametrize("body", [{"email": "x@example.com"}, {"password": STRONG_PASSWORD}])
def testPatchRejectsEmailAndPassword(admin, ids, body):
    assert send(admin, "PATCH", f"/users/{ids['tech']}", body).status_code == 422

# Changing a role revokes that user's session so the old cookie gets 401.
def testRoleChangeRevokesSessions(admin, tech, ids):
    assert tech.get("/auth/me").status_code == 200
    response = send(admin, "PATCH", f"/users/{ids['tech']}", {"roleCode": "manager"})
    assert (response.status_code, response.json()["roleCode"]) == (200, "manager")
    assert tech.get("/auth/me").status_code == 401
    assert admin.get("/auth/me").status_code == 200

# An admin changing their own role gets 409 SELF_DEMOTE.
def testOwnRoleChangeIs409(admin, ids):
    response = send(admin, "PATCH", f"/users/{ids['admin']}", {"roleCode": "manager"})
    assert (response.status_code, response.json()["code"]) == (409, "SELF_DEMOTE")

# A role change to an unknown role is 422 INVALID_ROLE and a missing user is 404.
def testPatchUnknownRoleAndMissingUser(admin, ids):
    unknown = send(admin, "PATCH", f"/users/{ids['tech']}", {"roleCode": "nobody"})
    assert (unknown.status_code, unknown.json()["code"]) == (422, "INVALID_ROLE")
    assert send(admin, "PATCH", f"/users/{MISSING_ID}", {"name": "X"}).status_code == 404

# No delete route exists on the collection or an item, so users are never deleted.
def testNoDeleteRoute(admin, ids):
    assert send(admin, "DELETE", f"/users/{ids['tech']}").status_code == 405
    assert send(admin, "DELETE", "/users").status_code == 405

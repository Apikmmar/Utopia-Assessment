from unittest.mock import patch
from uuid import uuid4
import pytest
from core.auth import AuthUser
from core.error import SELF_DEMOTE_CODE, VALIDATION_FAILED_CODE
from modules.user import service
from tests.support import STRONG_PASSWORD

ACTOR = AuthUser(userId=uuid4(), name="Admin", email="admin@example.com", roleCode="admin")


class NoRepository:
    # Fails the test the moment any repository function is reached.
    def __getattr__(self, name):
        raise AssertionError(f"repository.{name} must not be reached")

# Calls createUser with valid defaults and the given overrides, with the repository out of reach.
def createWith(**overrides):
    values = {"name": "New Person", "email": "new@example.com", "phone": None, "age": 30, "roleCode": "manager", "password": STRONG_PASSWORD}
    values.update(overrides)
    with patch.object(service, "repository", NoRepository()):
        return service.createUser(ACTOR, **values)

# Phones are stripped of spaces, dashes, and a leading plus; blank means none.
@pytest.mark.parametrize("raw,expected", [("+971 50-123 4567", "971501234567"), ("12345678", "12345678"), ("   ", None), (None, None)])
def testPhoneNormalization(raw, expected):
    fields = {}
    assert service.checkPhone(raw, fields) == expected
    assert fields == {}

# Phones of 8 and 15 digits are accepted and 7 and 16 digits are rejected.
@pytest.mark.parametrize("raw,valid", [("1234567", False), ("12345678", True), ("123456789012345", True), ("1234567890123456", False), ("12ab5678", False)])
def testPhoneLengthBoundaries(raw, valid):
    fields = {}
    service.checkPhone(raw, fields)
    assert ("phone" not in fields) is valid

# Ages 16 and 100 are accepted and 15 and 101 are rejected.
@pytest.mark.parametrize("age,valid", [(15, False), (16, True), (100, True), (101, False), (None, True)])
def testAgeBoundaries(age, valid):
    fields = {}
    service.checkAge(age, fields)
    assert ("age" not in fields) is valid

# Names are trimmed and must be 1 to 100 characters; emails are trimmed, lowercased, and checked.
def testNameAndEmailRules():
    fields = {}
    assert service.checkName("  Ann  ", fields) == "Ann"
    assert service.checkEmail("  Ann@Example.COM ", fields) == "ann@example.com"
    assert fields == {}
    service.checkName("   ", fields)
    service.checkEmail("not-an-email", fields)
    assert set(fields) == {"name", "email"}
    longName = {}
    service.checkName("x" * 101, longName)
    assert "name" in longName

# Each bad field is reported under its camelCase API name before the database is touched.
@pytest.mark.parametrize("overrides,field", [
    ({"name": "   "}, "name"),
    ({"email": "not-an-email"}, "email"),
    ({"phone": "12345"}, "phone"),
    ({"age": 15}, "age"),
    ({"password": "short"}, "password"),
    ({"roleCode": "technician", "phone": None}, "phone"),
])
def testCreateRejectsBadFieldsWithoutDatabase(overrides, field):
    user, error = createWith(**overrides)
    assert user is None
    assert error["code"] == VALIDATION_FAILED_CODE
    assert field in error["fields"]

# A role change on the actor's own account is refused before any lookup.
def testOwnRoleChangeRefusedWithoutDatabase():
    with patch.object(service, "repository", NoRepository()):
        user, error = service.updateUser(ACTOR, ACTOR.userId, {"role_code": "manager"})
    assert (user, error["code"]) == (None, SELF_DEMOTE_CODE)

# An explicit null role is a validation error on roleCode.
def testNullRoleRefused():
    with patch.object(service, "repository", NoRepository()):
        user, error = service.updateUser(ACTOR, uuid4(), {"role_code": None})
    assert (error["code"], list(error["fields"])) == (VALIDATION_FAILED_CODE, ["roleCode"])

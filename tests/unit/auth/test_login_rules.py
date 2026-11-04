from unittest.mock import patch
import pytest
from core.crypto import dummyHash
from core.error import WEAK_PASSWORD_CODE
from modules.auth import service

KNOWN_USER = {"user_id": "u1", "name": "Known", "email": "known@example.com", "password_hash": "stored-hash", "role_code": "technician"}


class NoDatabase:
    # Fails the test the moment anything tries to open a transaction.
    def __call__(self):
        raise AssertionError("no transaction may be opened")

# An unknown email and a wrong password give the same refusal, and each runs exactly one hash check.
def testUnknownUserAndWrongPasswordMatch():
    with patch.object(service.repository, "userByEmail", side_effect=[None, KNOWN_USER]), \
            patch.object(service, "verifyPassword", return_value=False) as verify, \
            patch.object(service, "transaction", NoDatabase()):
        unknown = service.login("nobody@example.com", "pw-value-123", None, None)
        wrong = service.login("known@example.com", "pw-value-123", None, None)
    assert unknown == wrong == (None, service.INVALID_CREDENTIALS)
    assert verify.call_count == 2
    assert verify.call_args_list[0].args[1] == dummyHash()

# A user without a stored hash is checked against the dummy hash and refused like any other failure.
def testUserWithoutHashUsesDummyHash():
    noHash = {**KNOWN_USER, "password_hash": None}
    with patch.object(service.repository, "userByEmail", return_value=noHash), \
            patch.object(service, "verifyPassword", return_value=True) as verify, \
            patch.object(service, "transaction", NoDatabase()):
        assert service.login("known@example.com", "pw-value-123", None, None) == (None, service.INVALID_CREDENTIALS)
    assert verify.call_args.args[1] == dummyHash()

# A weak new password is refused with its reason on newPassword before any hashing or database work.
@pytest.mark.parametrize("weak,reason", [("short", "too_short"), ("password123", "too_common"), ("x" * 129, "too_long")])
def testWeakResetPasswordRefusedBeforeAnyWork(weak, reason):
    with patch.object(service, "hashPassword") as hashed, patch.object(service, "transaction", NoDatabase()):
        done, error = service.resetPassword("known@example.com", weak)
    assert done is None
    assert (error["code"], error["fields"]) == (WEAK_PASSWORD_CODE, {"newPassword": reason})
    hashed.assert_not_called()

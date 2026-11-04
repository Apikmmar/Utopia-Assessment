import pytest
from argon2 import PasswordHasher
from core import crypto

CONFIGURED_PREFIX = "$argon2id$v=19$m=19456,t=2,p=1$"
PLAIN = "correct-horse-battery"

# Hash then verify succeeds with the right password and fails quietly with a wrong one.
def testVerifyMatchesOnlyTheRightPassword():
    encoded = crypto.hashPassword(PLAIN)
    assert crypto.verifyPassword(PLAIN, encoded)
    assert not crypto.verifyPassword("wrong-horse-battery", encoded)

# The encoded hash is Argon2id with the configured memory, iterations, and parallelism of one.
def testHashUsesConfiguredArgon2idParameters():
    assert crypto.hashPassword(PLAIN).startswith(CONFIGURED_PREFIX)

# A malformed or missing stored hash verifies as False instead of raising.
@pytest.mark.parametrize("stored", ["not-a-hash", "", None])
def testMalformedOrMissingHashIsNotAMatch(stored):
    assert not crypto.verifyPassword("whatever-password", stored)

# Hashing the same password twice produces different salts.
def testHashesAreSalted():
    assert crypto.hashPassword(PLAIN) != crypto.hashPassword(PLAIN)

# A hash made with weaker parameters needs a rehash, a current one does not, and a malformed one is left alone.
def testNeedsRehashAfterParametersChange():
    weak = PasswordHasher(time_cost=1, memory_cost=8, parallelism=1).hash(PLAIN)
    assert crypto.needsRehash(weak)
    assert not crypto.needsRehash(crypto.hashPassword(PLAIN))
    assert not crypto.needsRehash("not-a-hash")

# Raising the configured cost makes an existing hash outdated.
def testNeedsRehashWhenConfiguredCostRises(monkeypatch):
    encoded = crypto.hashPassword(PLAIN)
    monkeypatch.setenv("AUTH_ARGON2_ITERATIONS", "3")
    assert crypto.needsRehash(encoded)

# The dummy hash is computed once, uses the current cost, and never matches.
def testDummyHashIsStableAndEqualCost():
    first = crypto.dummyHash()
    assert first is crypto.dummyHash()
    assert not crypto.needsRehash(first)
    assert first.startswith(CONFIGURED_PREFIX)
    assert not crypto.verifyPassword("any-password-here", first)

# Nine characters are too short and ten are accepted.
def testMinimumLengthBoundary():
    assert crypto.validatePassword("a1b2c3d4e") == crypto.PASSWORD_TOO_SHORT
    assert crypto.validatePassword("a1b2c3d4e5") is None

# One hundred twenty-eight characters are accepted and one hundred twenty-nine are too long.
def testMaximumLengthBoundary():
    assert crypto.validatePassword("x" * 128) is None
    assert crypto.validatePassword("x" * 129) == crypto.PASSWORD_TOO_LONG

# A common password is rejected regardless of case.
@pytest.mark.parametrize("common", ["password123", "QWERTYUIOP"])
def testCommonPasswordRejected(common):
    assert crypto.validatePassword(common) == crypto.PASSWORD_TOO_COMMON

# An empty password is too short.
def testEmptyPasswordRejected():
    assert crypto.validatePassword("") == crypto.PASSWORD_TOO_SHORT

# Passwords without composition rules, such as all lowercase words, are accepted.
def testNoCompositionRules():
    assert crypto.validatePassword("correcthorsebattery") is None

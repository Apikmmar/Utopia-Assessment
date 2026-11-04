from argon2 import PasswordHasher, Type
from argon2.exceptions import InvalidHashError, VerificationError
from core import config

PASSWORD_PARALLELISM = 1
PASSWORD_MIN_LENGTH = 10
PASSWORD_MAX_LENGTH = 128
PASSWORD_TOO_SHORT = "too_short"
PASSWORD_TOO_LONG = "too_long"
PASSWORD_TOO_COMMON = "too_common"
DUMMY_PASSWORD = "dummy-password-never-valid"
COMMON_PASSWORDS = frozenset({
    "password", "password1", "password12", "password123", "password1234", "passw0rd123",
    "1234567890", "12345678910", "123456789012", "0123456789", "qwertyuiop", "qwerty12345",
    "qwerty123456", "1q2w3e4r5t", "abcdefghij", "abcd123456", "iloveyou123", "letmein1234",
    "welcome123", "welcome1234", "administrator", "admin12345", "admin123456", "changeme123",
    "trustno1234", "monkey12345", "dragon12345", "football123", "baseball123", "superman123",
})

_dummyHash = None

# Builds an Argon2id hasher from the configured cost, with explicit parallelism.
def buildHasher():
    return PasswordHasher(
        time_cost=config.authArgon2Iterations(),
        memory_cost=config.authArgon2MemoryKib(),
        parallelism=PASSWORD_PARALLELISM,
        type=Type.ID,
    )

# Returns the full encoded Argon2id hash of a plain password.
def hashPassword(plain):
    return buildHasher().hash(plain)

# Returns whether the password matches the encoded hash; a missing, mismatched, or malformed hash is False.
def verifyPassword(plain, hashed):
    if not hashed:
        return False
    try:
        return buildHasher().verify(hashed, plain)
    except (VerificationError, InvalidHashError):
        return False

# Returns whether a verified hash uses outdated cost parameters; a malformed hash is never rehashed.
def needsRehash(hashed):
    try:
        return buildHasher().check_needs_rehash(hashed)
    except InvalidHashError:
        return False

# Returns a reason code when the password breaks the policy, else None.
def validatePassword(plain):
    if len(plain) < PASSWORD_MIN_LENGTH:
        return PASSWORD_TOO_SHORT
    if len(plain) > PASSWORD_MAX_LENGTH:
        return PASSWORD_TOO_LONG
    if plain.lower() in COMMON_PASSWORDS:
        return PASSWORD_TOO_COMMON
    return None

# Returns a hash of a throwaway password, computed once, so a missing user costs the same as a real one.
def dummyHash():
    global _dummyHash
    if _dummyHash is None:
        _dummyHash = hashPassword(DUMMY_PASSWORD)
    return _dummyHash


__all__ = [
    "COMMON_PASSWORDS",
    "PASSWORD_MAX_LENGTH",
    "PASSWORD_MIN_LENGTH",
    "PASSWORD_TOO_COMMON",
    "PASSWORD_TOO_LONG",
    "PASSWORD_TOO_SHORT",
    "buildHasher",
    "dummyHash",
    "hashPassword",
    "needsRehash",
    "validatePassword",
    "verifyPassword",
]

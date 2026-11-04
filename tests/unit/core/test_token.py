import re
from core.token import hashToken, newToken

# A token is 43 characters of URL-safe text.
def testTokenIs43UrlSafeCharacters():
    assert re.fullmatch(r"[A-Za-z0-9_-]{43}", newToken())

# Generated tokens do not repeat.
def testTokensAreUnique():
    assert len({newToken() for _ in range(100)}) == 100

# The hash is a stable 64-character hex string that differs from the token.
def testHashIsStableHexAndDiffersFromToken():
    token = newToken()
    digest = hashToken(token)
    assert digest == hashToken(token)
    assert re.fullmatch(r"[0-9a-f]{64}", digest)
    assert digest != token

# The hash matches the published SHA-256 vector for "abc".
def testHashMatchesSha256Vector():
    assert hashToken("abc") == "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad"

# Different tokens hash to different digests.
def testDifferentTokensHashDifferently():
    assert hashToken("a") != hashToken("b")

import hashlib
import secrets

TOKEN_BYTES = 32

# Returns a new URL-safe random session token.
def newToken():
    return secrets.token_urlsafe(TOKEN_BYTES)

# Returns the SHA-256 hex digest that is stored in place of the token.
def hashToken(token):
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


__all__ = ["TOKEN_BYTES", "hashToken", "newToken"]

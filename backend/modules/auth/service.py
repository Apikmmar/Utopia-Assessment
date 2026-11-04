from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from core import config
from core.auth import AuthUser, authUserFromRow
from core.crypto import dummyHash, hashPassword, needsRehash, validatePassword, verifyPassword
from core.db import transaction
from core.error import INVALID_CREDENTIALS_CODE, WEAK_PASSWORD_CODE, serviceError
from core.logger import getLogger
from core.repository import session as sessionRepository
from core.token import hashToken, newToken
from core.useraccount import normalizeEmail
from modules.auth import repository

log = getLogger(__name__)

INVALID_CREDENTIALS = serviceError(INVALID_CREDENTIALS_CODE, "Invalid email or password.")
WEAK_PASSWORD_MESSAGE = "Choose a stronger password."
RESET_DONE_MESSAGE = "If the account exists, the password was updated."


@dataclass(frozen=True)
class LoginResult:
    token: str
    user: AuthUser

# Returns the current time as an aware UTC datetime.
def utcNow():
    return datetime.now(timezone.utc)

# Returns the WEAK_PASSWORD refusal carrying the policy reason on the given field.
def weakPasswordError(field, reason):
    return serviceError(WEAK_PASSWORD_CODE, WEAK_PASSWORD_MESSAGE, {field: reason})

# Verifies the credentials and opens a session, returning (result, error). Hashing runs with no
# connection held, and an unknown email still verifies against the dummy hash so every failure costs the same.
def login(email, password, ip, userAgent, now=utcNow):
    row = repository.userByEmail(normalizeEmail(email))
    storedHash = row["password_hash"] if row is not None else None
    verified = verifyPassword(password, storedHash or dummyHash())
    if row is None or not storedHash or not verified:
        log.info("login_failed")
        return None, INVALID_CREDENTIALS
    upgradedHash = hashPassword(password) if needsRehash(storedHash) else None
    current = now()
    token = newToken()
    expiresAt = current + timedelta(hours=config.authSessionHours())
    with transaction() as conn:
        if upgradedHash is not None:
            repository.updatePasswordHash(row["user_id"], upgradedHash, conn=conn)
        repository.insertSession(row["user_id"], hashToken(token), expiresAt, ip, userAgent, conn=conn)
        repository.updateLastLogin(row["user_id"], current, conn=conn)
    log.info("login_succeeded user_id=%s", row["user_id"])
    return LoginResult(token=token, user=authUserFromRow(row)), None

# Revokes the session behind this token; repeating it changes nothing.
def logout(token):
    repository.revokeSessionByTokenHash(hashToken(token))
    log.info("logout")

# Sets a new password and revokes the user's sessions, returning (done, error). The hash is computed
# before the short write transaction, and an unknown email costs the same and changes nothing.
def resetPassword(email, newPassword, now=utcNow):
    reason = validatePassword(newPassword)
    if reason is not None:
        return None, weakPasswordError("newPassword", reason)
    newHash = hashPassword(newPassword)
    with transaction() as conn:
        row = repository.userByEmail(normalizeEmail(email), conn=conn)
        if row is None:
            return True, None
        repository.updatePassword(row["user_id"], newHash, now(), conn=conn)
        sessionRepository.revokeUserSessions(row["user_id"], conn=conn)
    log.info("password_reset user_id=%s", row["user_id"])
    return True, None


__all__ = ["INVALID_CREDENTIALS", "RESET_DONE_MESSAGE", "LoginResult", "login", "logout", "resetPassword", "utcNow", "weakPasswordError"]

from dataclasses import dataclass
from uuid import UUID
from fastapi import Depends, Request
from core import config
from core.db import transaction
from core.error import FORBIDDEN_CODE, NOT_AUTHENTICATED_CODE, ApiError
from core.repository import session as sessionRepository
from core.token import hashToken

ROLE_ADMIN = "admin"
ROLE_TECHNICIAN = "technician"
ROLE_MANAGER = "manager"
ROLE_CODES = (ROLE_ADMIN, ROLE_TECHNICIAN, ROLE_MANAGER)
SESSION_TOUCH_MINUTES = 5
NOT_AUTHENTICATED_MESSAGE = "Authentication required."
FORBIDDEN_MESSAGE = "You do not have access to this resource."


@dataclass(frozen=True)
class AuthUser:
    userId: UUID
    name: str
    email: str
    roleCode: str

# Builds the authenticated user value from a row holding the user and role columns.
def authUserFromRow(row):
    return AuthUser(userId=row["user_id"], name=row["name"], email=row["email"], roleCode=row["role_code"])

# Returns the raw session token from the request cookie, or None.
def sessionToken(request: Request):
    return request.cookies.get(config.authCookieName())

# Returns the user of a live session token, or None, refreshing last_used_at at most every few minutes.
def resolveSession(token):
    with transaction() as conn:
        row = sessionRepository.sessionByTokenHash(hashToken(token), conn=conn)
        if row is None:
            return None
        sessionRepository.touchSession(row["session_id"], SESSION_TOUCH_MINUTES, conn=conn)
    return authUserFromRow(row)

# Resolves the session cookie to the authenticated user, or raises 401 NOT_AUTHENTICATED.
def currentUser(request: Request):
    token = sessionToken(request)
    user = resolveSession(token) if token else None
    if user is None:
        raise ApiError(401, NOT_AUTHENTICATED_CODE, NOT_AUTHENTICATED_MESSAGE)
    return user

# Returns a dependency that admits only the listed role codes, else raises 403 FORBIDDEN.
def requireRole(*roleCodes):
    return RoleGate(frozenset(roleCodes))


class RoleGate:
    # Keeps the role codes this gate admits.
    def __init__(self, allowed):
        self.allowed = allowed

    # Checks the authenticated user's role against the allowed codes and returns the user.
    def __call__(self, user: AuthUser = Depends(currentUser)):
        if user.roleCode not in self.allowed:
            raise ApiError(403, FORBIDDEN_CODE, FORBIDDEN_MESSAGE)
        return user


__all__ = [
    "ROLE_ADMIN",
    "ROLE_CODES",
    "ROLE_MANAGER",
    "ROLE_TECHNICIAN",
    "AuthUser",
    "authUserFromRow",
    "currentUser",
    "requireRole",
    "resolveSession",
    "sessionToken",
]

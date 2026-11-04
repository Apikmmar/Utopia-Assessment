from datetime import timedelta
from sqlalchemy import func, select, update
from core.db import readOne, roleTable, runWrite, sessionTable, userTable

SESSION_JOIN = sessionTable.join(userTable, userTable.c.user_id == sessionTable.c.user_id).join(
    roleTable, roleTable.c.role_id == userTable.c.role_id
)

# Returns the live session joined with its user and role code, or None when absent, revoked, or expired.
def sessionByTokenHash(tokenHash, conn=None):
    query = (
        select(sessionTable.c.session_id, userTable.c.user_id, userTable.c.name, userTable.c.email, roleTable.c.role_code)
        .select_from(SESSION_JOIN)
        .where(sessionTable.c.token_hash == tokenHash, sessionTable.c.revoked_at.is_(None), sessionTable.c.expires_at > func.now())
    )
    return readOne(query, conn)

# Refreshes last_used_at only when it is older than the touch interval, so most requests write nothing.
def touchSession(sessionId, touchMinutes, conn=None):
    statement = (
        update(sessionTable)
        .where(sessionTable.c.session_id == sessionId, sessionTable.c.last_used_at < func.now() - timedelta(minutes=touchMinutes))
        .values(last_used_at=func.now())
    )
    return runWrite(statement, conn)

# Revokes every live session of one user and returns how many were revoked.
def revokeUserSessions(userId, conn=None):
    statement = (
        update(sessionTable)
        .where(sessionTable.c.user_id == userId, sessionTable.c.revoked_at.is_(None))
        .values(revoked_at=func.now(), updated_at=func.now())
    )
    return runWrite(statement, conn)


__all__ = ["revokeUserSessions", "sessionByTokenHash", "touchSession"]

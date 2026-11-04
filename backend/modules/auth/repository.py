from sqlalchemy import func, select, update
from core.db import readOne, roleTable, runWrite, sessionTable, userTable

# Returns the user with credentials and role code for a normalized email, or None.
def userByEmail(email, conn=None):
    query = (
        select(userTable.c.user_id, userTable.c.name, userTable.c.email, userTable.c.password_hash, roleTable.c.role_code)
        .select_from(userTable.join(roleTable, roleTable.c.role_id == userTable.c.role_id))
        .where(userTable.c.email == email)
    )
    return readOne(query, conn)

# Stores one session row holding only the token hash.
def insertSession(userId, tokenHash, expiresAt, ip, userAgent, conn=None):
    statement = sessionTable.insert().values(user_id=userId, token_hash=tokenHash, expires_at=expiresAt, ip=ip, user_agent=userAgent)
    return runWrite(statement, conn)

# Revokes the session with this token hash when it is not already revoked.
def revokeSessionByTokenHash(tokenHash, conn=None):
    statement = (
        update(sessionTable)
        .where(sessionTable.c.token_hash == tokenHash, sessionTable.c.revoked_at.is_(None))
        .values(revoked_at=func.now(), updated_at=func.now())
    )
    return runWrite(statement, conn)

# Replaces the password hash and records when the password changed.
def updatePassword(userId, passwordHash, changedAt, conn=None):
    statement = (
        update(userTable).where(userTable.c.user_id == userId)
        .values(password_hash=passwordHash, password_changed_at=changedAt, updated_at=func.now())
    )
    return runWrite(statement, conn)

# Replaces only the password hash, used when the cost parameters are upgraded at login.
def updatePasswordHash(userId, passwordHash, conn=None):
    statement = update(userTable).where(userTable.c.user_id == userId).values(password_hash=passwordHash, updated_at=func.now())
    return runWrite(statement, conn)

# Records the time of a successful login.
def updateLastLogin(userId, loggedInAt, conn=None):
    statement = update(userTable).where(userTable.c.user_id == userId).values(last_login_at=loggedInAt, updated_at=func.now())
    return runWrite(statement, conn)


__all__ = [
    "insertSession",
    "revokeSessionByTokenHash",
    "updateLastLogin",
    "updatePassword",
    "updatePasswordHash",
    "userByEmail",
]

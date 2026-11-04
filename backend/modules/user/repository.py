from sqlalchemy import func, or_, select, update
from core.db import LIKE_ESCAPE, containsPattern, readAll, readOne, readScalar, roleTable, runUniqueWrite, runWrite, userTable

CONFLICT_EMAIL = "email"
USER_CONFLICTS = {"user_email_key": CONFLICT_EMAIL}
USER_COLUMNS = (
    userTable.c.user_id, userTable.c.name, userTable.c.email, userTable.c.phone,
    userTable.c.age, roleTable.c.role_code, userTable.c.created_at,
)
USER_JOIN = userTable.join(roleTable, roleTable.c.role_id == userTable.c.role_id)

# Returns the active role with this code, or None.
def findActiveRole(roleCode, conn=None):
    query = select(roleTable.c.role_id, roleTable.c.role_code).where(roleTable.c.role_code == roleCode, roleTable.c.is_active.is_(True))
    return readOne(query, conn)

# Inserts one user and returns (userId, conflict), where conflict names a taken unique field.
def insertUser(values, conn=None):
    return runUniqueWrite(userTable.insert().values(**values).returning(userTable.c.user_id), USER_CONFLICTS, conn)

# Returns one user without credentials, or None.
def getUserById(userId, conn=None):
    return readOne(select(*USER_COLUMNS).select_from(USER_JOIN).where(userTable.c.user_id == userId), conn)

# Returns one page of users and the total match count, in stable created_at then user_id order.
def listUsers(search, roleCode, offset, limit, conn=None):
    conditions = []
    if search:
        pattern = containsPattern(search)
        conditions.append(or_(userTable.c.name.ilike(pattern, escape=LIKE_ESCAPE), userTable.c.email.ilike(pattern, escape=LIKE_ESCAPE)))
    if roleCode:
        conditions.append(roleTable.c.role_code == roleCode)
    total = readScalar(select(func.count()).select_from(USER_JOIN).where(*conditions), conn)
    query = (
        select(*USER_COLUMNS).select_from(USER_JOIN).where(*conditions)
        .order_by(userTable.c.created_at, userTable.c.user_id)
        .limit(limit).offset(offset)
    )
    return readAll(query, conn), total

# Updates name, phone, or age and the audit columns for one user.
def updateDetails(userId, values, updatedBy, conn=None):
    statement = update(userTable).where(userTable.c.user_id == userId).values(**values, updated_at=func.now(), updated_by=updatedBy)
    return runWrite(statement, conn)

# Points one user at a new role and stamps the audit columns.
def updateRole(userId, roleId, updatedBy, conn=None):
    statement = update(userTable).where(userTable.c.user_id == userId).values(role_id=roleId, updated_at=func.now(), updated_by=updatedBy)
    return runWrite(statement, conn)


__all__ = [
    "CONFLICT_EMAIL",
    "findActiveRole",
    "getUserById",
    "insertUser",
    "listUsers",
    "updateDetails",
    "updateRole",
]

import re
from core.auth import ROLE_TECHNICIAN
from core.crypto import hashPassword, validatePassword
from core.db import transaction
from core.error import EMAIL_TAKEN_CODE, INVALID_ROLE_CODE, SELF_DEMOTE_CODE, USER_NOT_FOUND_CODE, VALIDATION_FAILED_CODE, serviceError
from core.logger import getLogger
from core.repository import session as sessionRepository
from core.useraccount import EMAIL_MAX_LENGTH, isValidEmail, normalizeEmail
from modules.user import repository
from modules.user.constants import AGE_MAX, AGE_MIN, NAME_MAX_LENGTH, PHONE_MAX_DIGITS, PHONE_MIN_DIGITS

log = getLogger(__name__)

PHONE_DIGITS = re.compile(rf"[0-9]{{{PHONE_MIN_DIGITS},{PHONE_MAX_DIGITS}}}")
PHONE_SEPARATORS = re.compile(r"[ -]")
EMAIL_TAKEN = serviceError(EMAIL_TAKEN_CODE, "A user with this email already exists.")
USER_NOT_FOUND = serviceError(USER_NOT_FOUND_CODE, "User not found.")
SELF_DEMOTE = serviceError(SELF_DEMOTE_CODE, "You cannot change your own role.")
INVALID_ROLE = serviceError(INVALID_ROLE_CODE, "Unknown or inactive role.", {"roleCode": "Unknown or inactive role."})
INVALID_FIELDS_MESSAGE = "One or more fields are invalid."

# Returns the VALIDATION_FAILED refusal for a field-to-message map.
def invalidFields(fields):
    return serviceError(VALIDATION_FAILED_CODE, INVALID_FIELDS_MESSAGE, fields)

# Returns the trimmed name, recording why it is invalid in fields.
def checkName(value, fields):
    name = (value or "").strip()
    if not name or len(name) > NAME_MAX_LENGTH:
        fields["name"] = f"Name must be 1 to {NAME_MAX_LENGTH} characters."
    return name

# Returns the trimmed lowercase email, recording why it is invalid in fields.
def checkEmail(value, fields):
    email = normalizeEmail(value)
    if not isValidEmail(email):
        fields["email"] = f"Email must be a valid address of at most {EMAIL_MAX_LENGTH} characters."
    return email

# Returns the digits-only phone, None when blank, recording why it is invalid in fields.
def checkPhone(value, fields):
    stripped = PHONE_SEPARATORS.sub("", (value or "").strip())
    if stripped.startswith("+"):
        stripped = stripped[1:]
    if not stripped:
        return None
    if not PHONE_DIGITS.fullmatch(stripped):
        fields["phone"] = f"Phone must be {PHONE_MIN_DIGITS} to {PHONE_MAX_DIGITS} digits."
    return stripped

# Returns the age, recording why it is outside the allowed range in fields.
def checkAge(value, fields):
    if value is not None and not AGE_MIN <= value <= AGE_MAX:
        fields["age"] = f"Age must be between {AGE_MIN} and {AGE_MAX}."
    return value

# Records the missing-phone error when a technician would be left without a phone.
def requireTechnicianPhone(roleCode, phone, fields):
    if roleCode == ROLE_TECHNICIAN and not phone:
        fields["phone"] = "Phone is required for a technician."

# Returns whether the actor is the user being changed.
def isSelf(actor, userId):
    return str(actor.userId) == str(userId)

# Returns the stored user as (user, error).
def getUser(actor, userId):
    row = repository.getUserById(userId)
    if row is None:
        return None, USER_NOT_FOUND
    return row, None

# Returns {user_id, name, phone} for an existing technician, or None when the user is unknown or has another role;
# the order module uses it inside its own transaction.
def technician(conn, userId):
    row = repository.getUserById(userId, conn) if userId is not None else None
    if row is None or row["role_code"] != ROLE_TECHNICIAN:
        return None
    return {"user_id": row["user_id"], "name": row["name"], "phone": row["phone"]}

# Validates the data, inserts the user as the actor, and returns (user, error). The password is
# hashed with no connection held, and a duplicate email answers EMAIL_TAKEN.
def createUser(actor, name, email, phone, age, roleCode, password):
    fields = {}
    cleanName = checkName(name, fields)
    cleanEmail = checkEmail(email, fields)
    cleanPhone = checkPhone(phone, fields)
    cleanAge = checkAge(age, fields)
    reason = validatePassword(password)
    if reason:
        fields["password"] = reason
    cleanRoleCode = (roleCode or "").strip()
    requireTechnicianPhone(cleanRoleCode, cleanPhone, fields)
    if fields:
        return None, invalidFields(fields)
    role = repository.findActiveRole(cleanRoleCode)
    if role is None:
        return None, INVALID_ROLE
    values = {
        "name": cleanName, "email": cleanEmail, "phone": cleanPhone, "age": cleanAge, "role_id": role["role_id"],
        "password_hash": hashPassword(password), "created_by": actor.email, "updated_by": actor.email,
    }
    userId, conflict = repository.insertUser(values)
    if conflict:
        return None, EMAIL_TAKEN
    log.info("user_created actor_id=%s user_id=%s role_code=%s", actor.userId, userId, role["role_code"])
    return repository.getUserById(userId), None

# Returns one page of users and the total match count as (rows, total).
def listUsers(actor, search, roleCode, paging):
    return repository.listUsers((search or "").strip(), (roleCode or "").strip(), paging.offset, paging.pageSize)

# Applies a PATCH of name, phone, age, and role after validating every part, returning (user, error).
# A role change refuses the actor's own account and revokes the target's sessions in the same transaction.
def updateUser(actor, userId, changes):
    changingRole = "role_code" in changes
    if changingRole and changes["role_code"] is None:
        return None, invalidFields({"roleCode": "Role must not be empty."})
    if changingRole and isSelf(actor, userId):
        return None, SELF_DEMOTE
    current, error = getUser(actor, userId)
    if error:
        return None, error
    fields = {}
    values = {}
    if "name" in changes:
        values["name"] = checkName(changes["name"], fields)
    if "phone" in changes:
        values["phone"] = checkPhone(changes["phone"], fields)
    if "age" in changes:
        values["age"] = checkAge(changes["age"], fields)
    if fields:
        return None, invalidFields(fields)
    role = repository.findActiveRole(changes["role_code"].strip()) if changingRole else None
    if changingRole and role is None:
        return None, INVALID_ROLE
    requireTechnicianPhone(role["role_code"] if role else current["role_code"], values.get("phone", current["phone"]), fields)
    if fields:
        return None, invalidFields(fields)
    with transaction() as conn:
        if values:
            repository.updateDetails(userId, values, actor.email, conn=conn)
        if role is not None:
            repository.updateRole(userId, role["role_id"], actor.email, conn=conn)
            sessionRepository.revokeUserSessions(userId, conn=conn)
    if role is not None:
        log.info("role_changed actor_id=%s user_id=%s from=%s to=%s", actor.userId, userId, current["role_code"], role["role_code"])
    return repository.getUserById(userId), None


__all__ = [
    "EMAIL_TAKEN",
    "INVALID_ROLE",
    "SELF_DEMOTE",
    "USER_NOT_FOUND",
    "checkAge",
    "checkEmail",
    "checkName",
    "checkPhone",
    "createUser",
    "getUser",
    "listUsers",
    "technician",
    "updateUser",
]

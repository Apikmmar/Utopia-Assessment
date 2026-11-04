import pytest
from core import crypto
from core.auth import AuthUser
from core.pagination import PageRequest
from modules.user import repository as userRepository, service
from tests.support import MISSING_ID, STRONG_PASSWORD

ADMIN_EMAIL = "admin.users.test@example.com"


# Seeds the acting admin and returns it as the authenticated user value services receive.
@pytest.fixture
def actor(seedUser):
    return AuthUser(userId=seedUser(ADMIN_EMAIL, "admin", name="Admin"), name="Admin", email=ADMIN_EMAIL, roleCode="admin")

# Creates a user with valid defaults and the given overrides, returning (user, error).
def create(actor, **overrides):
    values = {"name": "  New Person ", "email": "  New.Person@Example.COM ", "phone": None, "age": 30, "roleCode": "manager", "password": STRONG_PASSWORD}
    values.update(overrides)
    return service.createUser(actor, **values)

# Returns the live session count of one user.
def liveSessions(scalar, userId):
    return scalar("SELECT count(*) FROM session WHERE user_id = :u AND revoked_at IS NULL", u=userId)

# Creating a user trims, lowercases, normalizes the phone, and stores only an Argon2 hash with the actor as creator.
def testCreateNormalizesAndStoresWithoutPlainPassword(actor, appDb):
    user, error = create(actor, phone="+971 50-123 4567")
    assert error is None
    assert (user["email"], user["name"], user["phone"]) == ("new.person@example.com", "New Person", "971501234567")
    with appDb.connect() as conn:
        stored = conn.exec_driver_sql('SELECT password_hash, created_by FROM "user" WHERE user_id = %s', (user["user_id"],)).one()
    assert stored.password_hash.startswith("$argon2id$")
    assert STRONG_PASSWORD not in stored.password_hash
    assert stored.created_by == ADMIN_EMAIL

# Ages 16 and 100 and phones of 8 and 15 digits are stored.
def testBoundaryValuesAreStored(actor):
    assert create(actor, email="a@example.com", age=16)[0]["age"] == 16
    assert create(actor, email="b@example.com", age=100)[0]["age"] == 100
    assert create(actor, email="c@example.com", phone="12345678")[0]["phone"] == "12345678"
    assert create(actor, email="d@example.com", phone="123456789012345")[0]["phone"] == "123456789012345"

# A duplicate email in any case answers EMAIL_TAKEN and stores nothing more.
def testDuplicateEmailIsEmailTaken(actor, scalar):
    create(actor)
    assert create(actor, email="NEW.PERSON@example.com") == (None, service.EMAIL_TAKEN)
    assert scalar('SELECT count(*) FROM "user"') == 2

# A duplicate inside the caller's transaction is reported as a conflict and leaves that transaction usable.
def testConflictInsideTransactionKeepsItAlive(actor, appDb, scalar):
    role = userRepository.findActiveRole("manager")
    values = {"name": "X", "email": ADMIN_EMAIL, "role_id": role["role_id"], "created_by": "t", "updated_by": "t"}
    with appDb.begin() as conn:
        assert userRepository.insertUser(values, conn=conn) == (None, userRepository.CONFLICT_EMAIL)
        userId, conflict = userRepository.insertUser({**values, "email": "fresh@example.com"}, conn=conn)
    assert conflict is None and userId is not None
    assert scalar('SELECT count(*) FROM "user"') == 2

# An unknown or inactive role code answers INVALID_ROLE on roleCode.
def testUnknownAndInactiveRolesAreInvalid(actor, execute):
    assert create(actor, roleCode="nobody") == (None, service.INVALID_ROLE)
    execute("UPDATE role SET is_active = false WHERE role_code = 'manager'")
    assert create(actor) == (None, service.INVALID_ROLE)

# A technician needs a phone on create and is stored once one is given.
def testTechnicianRequiresPhone(actor):
    user, error = create(actor, roleCode="technician")
    assert user is None and "phone" in error["fields"]
    assert create(actor, roleCode="technician", phone="12345678")[0]["role_code"] == "technician"

# Creating a user hashes the password with no pooled connection checked out.
def testCreateHoldsNoConnectionWhileHashing(actor, appDb, monkeypatch):
    checkedOut = []
    monkeypatch.setattr(service, "hashPassword", lambda plain: checkedOut.append(appDb.pool.checkedout()) or crypto.hashPassword(plain))
    create(actor)
    assert checkedOut == [0]

# List search, role filter, paging, and literal wildcard matching.
def testListFiltersOrdersAndPages(actor, seedUser):
    for index in range(5):
        seedUser(f"list{index}@example.com", "manager", name=f"Lister {index}")
    seedUser("tech@example.com", "technician", name="Fixer", phone="12345678")
    rows, total = service.listUsers(actor, "lister", None, PageRequest(page=1, pageSize=3))
    assert (len(rows), total) == (3, 5)
    secondRows, _ = service.listUsers(actor, "lister", None, PageRequest(page=2, pageSize=3))
    assert len(secondRows) == 2
    assert not {row["user_id"] for row in rows} & {row["user_id"] for row in secondRows}
    techs, techTotal = service.listUsers(actor, None, "technician", PageRequest(page=1, pageSize=20))
    assert (techTotal, techs[0]["email"]) == (1, "tech@example.com")
    assert service.listUsers(actor, "%", None, PageRequest(page=1, pageSize=20))[1] == 0
    assert "password_hash" not in rows[0]

# A missing user answers USER_NOT_FOUND.
def testGetMissingUserIsNotFound(actor):
    assert service.getUser(actor, MISSING_ID) == (None, service.USER_NOT_FOUND)
    assert service.updateUser(actor, MISSING_ID, {"name": "X"}) == (None, service.USER_NOT_FOUND)

# Editing details never touches the email or the role, and the actor is stored as updater.
def testUpdateDetailsLeavesEmailAndRole(actor, seedUser, scalar):
    userId = seedUser("edit@example.com", "manager", name="Before")
    user, error = service.updateUser(actor, userId, {"name": " After ", "age": 40})
    assert error is None
    assert (user["name"], user["age"], user["email"], user["role_code"]) == ("After", 40, "edit@example.com", "manager")
    assert scalar('SELECT updated_by FROM "user" WHERE user_id = :u', u=userId) == ADMIN_EMAIL

# A technician cannot have the phone cleared.
def testTechnicianCannotClearPhone(actor, seedUser):
    userId = seedUser("tech@example.com", "technician", phone="12345678")
    user, error = service.updateUser(actor, userId, {"phone": ""})
    assert user is None and "phone" in error["fields"]

# A role change leaves the user with no live session and other users' sessions untouched.
def testChangeRoleRevokesSessionsInSameTransaction(actor, seedUser, execute, scalar):
    userId = seedUser("target@example.com", "manager", phone="12345678")
    for index, owner in enumerate((userId, userId, actor.userId)):
        execute("INSERT INTO session (user_id, token_hash, expires_at) VALUES (:u, :t, now() + interval '1 hour')", u=owner, t=str(index) * 64)
    user, error = service.updateUser(actor, userId, {"role_code": "technician"})
    assert (error, user["role_code"]) == (None, "technician")
    assert liveSessions(scalar, userId) == 0
    assert liveSessions(scalar, actor.userId) == 1

# A failed role change leaves the role, details, and sessions as they were.
def testRefusedRoleChangeWritesNothing(actor, seedUser, execute, scalar):
    userId = seedUser("nophone@example.com", "manager", name="Same")
    execute("INSERT INTO session (user_id, token_hash, expires_at) VALUES (:u, :t, now() + interval '1 hour')", u=userId, t="a" * 64)
    user, error = service.updateUser(actor, userId, {"role_code": "technician", "name": "Changed"})
    assert user is None and "phone" in error["fields"]
    assert scalar('SELECT name FROM "user" WHERE user_id = :u', u=userId) == "Same"
    assert liveSessions(scalar, userId) == 1

# An actor changing their own role answers SELF_DEMOTE.
def testChangeOwnRoleIsRefused(actor):
    assert service.updateUser(actor, actor.userId, {"role_code": "manager"}) == (None, service.SELF_DEMOTE)

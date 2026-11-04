import pytest
from sqlalchemy import text
from core.crypto import verifyPassword
from script import seed_user


# One transaction on the migrated throwaway schema, rolled back afterwards.
@pytest.fixture
def conn(appDb):
    connection = appDb.connect()
    outer = connection.begin()
    try:
        yield connection
    finally:
        outer.rollback()
        connection.close()

# Returns each seeded user's email, role code, phone, and password hash.
def seededRows(conn):
    query = text('SELECT u.email, r.role_code, u.phone, u.password_hash FROM "user" u JOIN role r USING (role_id) ORDER BY u.email')
    return conn.execute(query).all()

# The seed creates one admin, one manager, and two technicians who all log in with the mock password.
def testSeedsFourUsersWithRoles(conn):
    created, skipped = seed_user.seedUsers(conn)
    rows = seededRows(conn)
    assert sorted(created) == ["admin@utopia.com", "ali@utopia.com", "bala@utopia.com", "manager@utopia.com"]
    assert skipped == []
    assert sorted(row.role_code for row in rows) == ["admin", "manager", "technician", "technician"]
    assert all(row.phone for row in rows if row.role_code == "technician")
    assert all(verifyPassword("P@ssword123", row.password_hash) for row in rows)

# Running the seed twice skips every existing user instead of failing or duplicating.
def testSeedIsRepeatable(conn):
    seed_user.seedUsers(conn)
    created, skipped = seed_user.seedUsers(conn)
    assert created == []
    assert len(skipped) == 4
    assert len(seededRows(conn)) == 4

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

# The seed creates one admin, one manager, and three technicians from the JSON file, who all log in with the mock
# password.
def testSeedsFiveUsersWithRoles(conn):
    created, skipped = seed_user.seedUsers(conn, seed_user.loadData())
    rows = seededRows(conn)
    assert sorted(created) == ["admin@utopia.com", "ali@utopia.com", "bala@utopia.com", "chong@utopia.com", "manager@utopia.com"]
    assert skipped == []
    assert sorted(row.role_code for row in rows) == ["admin", "manager", "technician", "technician", "technician"]
    assert all(row.phone for row in rows if row.role_code == "technician")
    assert all(verifyPassword("P@ssword123", row.password_hash) for row in rows)

# Running the seed twice skips every existing user instead of failing or duplicating.
def testSeedIsRepeatable(conn):
    data = seed_user.loadData()
    seed_user.seedUsers(conn, data)
    created, skipped = seed_user.seedUsers(conn, data)
    assert created == []
    assert len(skipped) == 5
    assert len(seededRows(conn)) == 5

# Removing deletes the seeded users and their sessions but keeps a user that orders still name and any user the seed
# did not create.
def testRemoveKeepsReferencedAndOtherUsers(conn):
    seed_user.seedUsers(conn, seed_user.loadData())
    seed_user.seedUsers(conn, {"users": [{"name": "Real", "email": "real@utopia.com", "phone": None, "role": "admin"}]})
    conn.execute(text("""UPDATE "user" SET created_by = 'someone' WHERE email = 'real@utopia.com'"""))
    conn.execute(text(
        "INSERT INTO session (user_id, token_hash, expires_at) SELECT user_id, 'hash', now() + interval '1 hour' FROM \"user\" WHERE email = 'bala@utopia.com'"
    ))
    conn.execute(text(
        "INSERT INTO service_order (customer_name, customer_phone, address, problem_description, service_type_id, quoted_price, "
        "assigned_technician_id, status, created_by_id) SELECT 'Real', '60123456789', 'Addr', 'Problem', service_type_id, 100, "
        "(SELECT user_id FROM \"user\" WHERE email = 'ali@utopia.com'), 'assigned', (SELECT user_id FROM \"user\" WHERE email = 'admin@utopia.com') "
        "FROM service_type WHERE service_type_code = 'repair'"
    ))
    removed, kept = seed_user.removeUsers(conn)
    assert removed == ["bala@utopia.com", "chong@utopia.com", "manager@utopia.com"]
    assert kept == ["admin@utopia.com", "ali@utopia.com"]
    assert [row.email for row in seededRows(conn)] == ["admin@utopia.com", "ali@utopia.com", "real@utopia.com"]

# Without --yes nothing is written and the command fails.
def testRefusesWithoutYes(monkeypatch, capsys):
    monkeypatch.setattr(seed_user, "targetHost", lambda: "db.example.test")
    assert seed_user.main([]) == seed_user.EXIT_FAILED
    assert "--yes" in capsys.readouterr().err

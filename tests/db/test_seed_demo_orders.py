from datetime import date
import pytest
from sqlalchemy import text
from core.auth import AuthUser
from modules.kpi import service as kpiService
from script import seed_demo_orders, seed_user

DEMO_ORDERS = 130
DEMO_COMPLETIONS = 123
DEMO_POSTPONEMENTS = 41

# One transaction on the migrated throwaway schema with the mock users seeded, rolled back afterwards.
@pytest.fixture
def conn(appDb):
    connection = appDb.connect()
    outer = connection.begin()
    seed_user.seedUsers(connection)
    try:
        yield connection
    finally:
        outer.rollback()
        connection.close()

# Returns one count from the connection.
def count(conn, sql):
    return conn.execute(text(sql)).scalar_one()

# The first run loads every order, completion, and postponement from the JSON file, adds the two extra technicians,
# and a second run adds nothing.
def testSeedLoadsJsonOnce(conn):
    data = seed_demo_orders.loadData()
    assert seed_demo_orders.seedOrders(conn, data) == DEMO_ORDERS
    assert count(conn, "SELECT count(*) FROM service_order WHERE created_by = 'demo-seed'") == DEMO_ORDERS
    assert count(conn, "SELECT count(*) FROM order_completion WHERE created_by = 'demo-seed'") == DEMO_COMPLETIONS
    assert count(conn, "SELECT count(*) FROM order_event WHERE event_type = 'postponed'") == DEMO_POSTPONEMENTS
    assert count(conn, """SELECT count(*) FROM "user" WHERE email IN ('chong@utopia.com', 'devi@utopia.com')""") == 2
    assert count(conn, "SELECT min(completed_at AT TIME ZONE 'Asia/Kuala_Lumpur')::date FROM order_completion") == date(2026, 9, 28)
    assert seed_demo_orders.seedOrders(conn, data) == 0
    assert count(conn, "SELECT count(*) FROM service_order") == DEMO_ORDERS

# The dashboard for 26 Oct to 1 Nov 2026 matches figures worked out from the JSON file by hand.
def testDashboardMatchesHandCountedWeek(appDb):
    with appDb.begin() as conn:
        seed_user.seedUsers(conn)
        seed_demo_orders.seedOrders(conn, seed_demo_orders.loadData())
    manager = AuthUser(userId=None, name="Manager", email="manager@utopia.com", roleCode="manager")
    result, error = kpiService.teamDashboard(manager, date(2026, 10, 28), date(2026, 11, 5))
    assert error is None
    figures = [(row["rank"], row["technician"]["name"], row["jobs_completed"], row["total_amount"], row["postponed"]) for row in result["leaderboard"]]
    assert figures == [(1, "Ali", 10, "2260.00", 3), (2, "Bala", 6, "1050.00", 2), (3, "Chong", 5, "1670.00", 1), (4, "Devi", 4, "1080.00", 0)]
    assert result["team"] == {"jobs_completed": 25, "total_amount": "6060.00", "postponed": 6}

# Removing deletes only the demo orders, their rows, and the technicians the seed created, leaving other orders and
# users alone.
def testRemoveDeletesOnlyDemoRows(conn):
    seed_demo_orders.seedOrders(conn, seed_demo_orders.loadData())
    adminId = count(conn, """SELECT user_id FROM "user" WHERE email = 'admin@utopia.com'""")
    techId = count(conn, """SELECT user_id FROM "user" WHERE email = 'ali@utopia.com'""")
    conn.execute(text(
        "INSERT INTO service_order (customer_name, customer_phone, address, problem_description, service_type_id, quoted_price, "
        "assigned_technician_id, status, created_by_id) SELECT 'Real', '60123456789', 'Addr', 'Problem', service_type_id, 100, :techId, "
        "'assigned', :adminId FROM service_type WHERE service_type_code = 'repair'"
    ), {"techId": techId, "adminId": adminId})
    assert seed_demo_orders.removeOrders(conn) == DEMO_ORDERS
    assert count(conn, "SELECT count(*) FROM service_order") == 1
    assert count(conn, "SELECT count(*) FROM order_completion") == 0
    assert count(conn, "SELECT count(*) FROM order_event") == 0
    assert count(conn, """SELECT count(*) FROM "user" WHERE created_by = 'demo-seed'""") == 0
    assert count(conn, """SELECT count(*) FROM "user" WHERE email = 'ali@utopia.com'""") == 1

# Without --yes nothing is written and the command fails.
def testRefusesWithoutYes(monkeypatch, capsys):
    monkeypatch.setattr(seed_demo_orders, "targetHost", lambda: "db.example.test")
    assert seed_demo_orders.main([]) == seed_demo_orders.EXIT_FAILED
    assert "--yes" in capsys.readouterr().err

import json
from datetime import date
import pytest
from sqlalchemy import text
from core.auth import AuthUser
from core.db import ConflictError
from db.migration import applyPending, rollbackLatest
from modules.kpi import service as kpiService
from tests.order_support import insertOrder
from tests.support import schemaMigrations

TODAY = date(2026, 11, 5)
POSTPONED_MIGRATION = "0016_order_event_postponed.sql"
CONSTRAINT_QUERY = (
    "SELECT pg_get_constraintdef(c.oid) FROM pg_constraint c JOIN pg_namespace n ON n.oid = c.connamespace "
    "WHERE n.nspname = :schema AND c.conname = 'order_event_event_type_check'"
)
INSERT_USER = (
    """INSERT INTO "user" (name, email, phone, role_id) SELECT 'User', :email, '60111111111', role_id FROM role WHERE role_code = :roleCode """
    "RETURNING user_id"
)
INDEX_QUERY = "SELECT to_regclass(:name)"
INSERT_COMPLETION = (
    "INSERT INTO order_completion (service_order_id, technician_id, work_done, quoted_price, extra_charges, final_amount, completed_at) "
    "VALUES (:orderId, :technicianId, 'Done', :amount, 0, :amount, :completedAt)"
)
INSERT_POSTPONED = (
    "INSERT INTO order_event (service_order_id, event_type, from_status, to_status, actor_id, detail, created_at) "
    "VALUES (:orderId, 'postponed', 'assigned', 'assigned', :actorId, CAST(:detail AS jsonb), :createdAt)"
)

# Inserts one user with the role and no password, bypassing the application, and returns its id.
def insertUser(engine, email, roleCode):
    with engine.begin() as conn:
        return conn.execute(text(INSERT_USER), {"email": email, "roleCode": roleCode}).scalar_one()

# Admin, manager, and three technicians; Chong never works.
@pytest.fixture
def people(appDb, seedUser):
    return {
        "admin": seedUser("admin.kpi@example.com", "admin", password=None, name="Ada Admin"),
        "ali": seedUser("ali.kpi@example.com", "technician", password=None, name="Ali", phone="60111111111"),
        "bala": seedUser("bala.kpi@example.com", "technician", password=None, name="Bala", phone="60122222222"),
        "chong": seedUser("chong.kpi@example.com", "technician", password=None, name="Chong", phone="60133333333"),
    }

# Inserts one finished order completed by the technician at the given time with the given final amount.
def completeAt(engine, people, technician, amount, completedAt):
    orderId, _ = insertOrder(engine, people["admin"], people[technician], status="job_done")
    with engine.begin() as conn:
        conn.execute(text(INSERT_COMPLETION), {"orderId": orderId, "technicianId": people[technician], "amount": amount, "completedAt": completedAt})

# Inserts one postponed event crediting the technician at the given time.
def postponeAt(engine, people, technician, createdAt):
    orderId, _ = insertOrder(engine, people["admin"], people[technician], status="assigned")
    detail = json.dumps({"reasonCode": "weather", "newDate": None, "technicianId": str(people[technician])})
    with engine.begin() as conn:
        conn.execute(text(INSERT_POSTPONED), {"orderId": orderId, "actorId": people[technician], "detail": detail, "createdAt": createdAt})

# Inserts one event of the given type whose detail names a technician id that is not a UUID, as only a direct
# database write could.
def malformedAt(engine, people, eventType, createdAt):
    orderId, _ = insertOrder(engine, people["admin"], people["ali"], status="assigned")
    with engine.begin() as conn:
        conn.execute(text(INSERT_POSTPONED.replace("'postponed'", ":eventType")), {
            "orderId": orderId, "actorId": people["admin"], "detail": '{"technicianId": "not-a-uuid"}', "createdAt": createdAt, "eventType": eventType,
        })

# The week of 2 to 8 Nov 2026 runs from 2026-11-01 16:00 UTC to 2026-11-08 16:00 UTC. Rows one second either side of
# both bounds show which are counted, and events with a malformed technician id are skipped instead of failing the
# query; the expected figures are worked out by hand.
def testWeekFiguresPerTechnician(appDb, people):
    completeAt(appDb, people, "ali", "999.00", "2026-11-01T15:59:59Z")
    completeAt(appDb, people, "ali", "150.00", "2026-11-01T16:00:00Z")
    completeAt(appDb, people, "ali", "220.50", "2026-11-05T03:00:00Z")
    completeAt(appDb, people, "bala", "180.00", "2026-11-08T15:59:59Z")
    completeAt(appDb, people, "bala", "500.00", "2026-11-08T16:00:00Z")
    postponeAt(appDb, people, "ali", "2026-11-03T02:00:00Z")
    postponeAt(appDb, people, "bala", "2026-11-01T15:00:00Z")
    postponeAt(appDb, people, "bala", "2026-11-06T09:00:00Z")
    postponeAt(appDb, people, "bala", "2026-11-07T09:00:00Z")
    malformedAt(appDb, people, "postponed", "2026-11-04T09:00:00Z")
    malformedAt(appDb, people, "assigned", "2026-11-04T09:00:00Z")
    manager = AuthUser(userId=people["admin"], name="Ada", email="admin.kpi@example.com", roleCode="manager")
    result, error = kpiService.teamDashboard(manager, date(2026, 11, 4), TODAY)
    assert error is None
    assert result["team"] == {"jobs_completed": 3, "total_amount": "550.50", "postponed": 3}
    figures = [(row["rank"], row["technician"]["name"], row["jobs_completed"], row["total_amount"], row["postponed"]) for row in result["leaderboard"]]
    assert figures == [(1, "Ali", 2, "370.50", 1), (2, "Bala", 1, "180.00", 2), (3, "Chong", 0, "0.00", 0)]

# Up, down, up keeps the named check and partial index; postponed rows are accepted after up and block the down.
def testPostponedMigrationRollsBack(testEngine, testSchema):
    migrations = schemaMigrations(testSchema)
    with testEngine.connect() as conn, conn.begin():
        applyPending(conn, migrations, schema=testSchema)
        assert "'postponed'" in conn.execute(text(CONSTRAINT_QUERY), {"schema": testSchema}).scalar_one()
        assert rollbackLatest(conn, migrations, schema=testSchema) == [POSTPONED_MIGRATION]
        assert "'postponed'" not in conn.execute(text(CONSTRAINT_QUERY), {"schema": testSchema}).scalar_one()
        assert conn.execute(text(INDEX_QUERY), {"name": f"{testSchema}.order_event_postponed_created_at_idx"}).scalar() is None
        assert applyPending(conn, migrations, schema=testSchema) == [POSTPONED_MIGRATION]
        assert applyPending(conn, migrations, schema=testSchema) == []
        assert conn.execute(text(INDEX_QUERY), {"name": f"{testSchema}.order_event_postponed_created_at_idx"}).scalar() is not None
    adminId = insertUser(testEngine, "admin.mig@example.com", "admin")
    techId = insertUser(testEngine, "tech.mig@example.com", "technician")
    orderId, _ = insertOrder(testEngine, adminId, techId, status="assigned")
    with testEngine.begin() as conn:
        conn.execute(text("INSERT INTO order_event (service_order_id, event_type, actor_id) VALUES (:orderId, 'postponed', :actorId)"), {"orderId": orderId, "actorId": techId})
    with pytest.raises(ConflictError):
        with testEngine.connect() as conn, conn.begin():
            rollbackLatest(conn, migrations, schema=testSchema)
    with testEngine.connect() as conn:
        assert conn.execute(text("SELECT count(*) FROM order_event WHERE event_type = 'postponed'")).scalar_one() == 1

# An unknown event type is still refused after the migration.
def testUnknownEventStillRefused(appDb, people, execute):
    orderId, _ = insertOrder(appDb, people["admin"], people["ali"], status="assigned")
    with pytest.raises(ConflictError):
        execute("INSERT INTO order_event (service_order_id, event_type, actor_id) VALUES (:orderId, 'paused', :actorId)", orderId=orderId, actorId=people["ali"])

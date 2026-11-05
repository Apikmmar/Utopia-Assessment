import re
from concurrent.futures import ThreadPoolExecutor
import pytest
from sqlalchemy import text
from sqlalchemy.dialects import postgresql
from core.db import ConflictError, meta
from db.migration import applyPending, getHistory, rollbackLatest, runSql
from tests.support import schemaMigrations

ORDER_MIGRATIONS = (
    "0010_service_type.sql", "0011_service_order.sql", "0012_order_attachment.sql",
    "0013_order_completion.sql", "0014_order_event.sql", "0015_notification.sql",
)
LATER_MIGRATIONS = ("0016_order_event_postponed.sql",)
ORDER_TABLES = ("service_type", "service_order", "order_attachment", "order_completion", "order_event", "notification")
SEEDED_SERVICE_TYPES = ["cleaning", "repair", "gas_refill", "installation", "general_servicing"]
CONCURRENT_ORDERS = 16
CONCURRENT_WORKERS = 8
ORDER_NO_PATTERN = re.compile(r"^ORD-\d{6,}$")
COLUMN_QUERY = (
    "SELECT a.attname, format_type(a.atttypid, a.atttypmod), a.attnotnull FROM pg_attribute a "
    "WHERE a.attrelid = to_regclass(:name) AND a.attnum > 0 AND NOT a.attisdropped ORDER BY a.attnum"
)
INSERT_ORDER = (
    "INSERT INTO service_order (customer_name, customer_phone, address, problem_description, service_type_id, "
    "quoted_price, assigned_technician_id, status, created_by_id) "
    "VALUES ('Customer', '60123456789', 'Address', 'Problem', :serviceTypeId, 150, :technicianId, :status, :adminId) "
    "RETURNING service_order_id, order_no"
)

# Returns the Postgres spelling of a SQLAlchemy column type, as format_type reports it.
def postgresType(column):
    compiled = column.type.compile(dialect=postgresql.dialect()).lower().replace(", ", ",")
    compiled = compiled.replace("varchar(", "character varying(")
    return re.sub(r"^char\(", "character(", compiled)

# Inserts one order with the given status and technician and returns its id and number.
def insertOrder(engine, ids, status="new", technicianId=None):
    with engine.begin() as conn:
        row = conn.execute(text(INSERT_ORDER), {
            "serviceTypeId": ids["serviceTypeId"], "technicianId": technicianId, "status": status, "adminId": ids["adminId"],
        }).one()
    return row.service_order_id, row.order_no

# Seeded admin, technician, and service type ids for the order tables.
@pytest.fixture
def ids(appDb, seedUser, scalar):
    return {
        "adminId": seedUser("admin@example.com", roleCode="admin", password=None),
        "technicianId": seedUser("tech@example.com", roleCode="technician", password=None, phone="60123456789"),
        "serviceTypeId": scalar("SELECT service_type_id FROM service_type WHERE service_type_code = 'repair'"),
    }

# One order in progress with its technician assigned.
@pytest.fixture
def orderId(appDb, ids):
    return insertOrder(appDb, ids, status="in_progress", technicianId=ids["technicianId"])[0]

# Every order Table definition matches its migrated table column for column, including type and nullability.
@pytest.mark.parametrize("table", ORDER_TABLES)
def testTableDefinitionsMatchMigrations(appDb, testSchema, table):
    with appDb.connect() as conn:
        actual = [tuple(row) for row in conn.execute(text(COLUMN_QUERY), {"name": f'{testSchema}."{table}"'})]
    expected = [(column.name, postgresType(column), not column.nullable) for column in meta.tables[table].columns]
    assert actual == expected

# The five service types are seeded once in order, and running the migration again adds none.
def testServiceTypesSeededOnce(appDb, testSchema):
    serviceTypeMigration = next(migration for migration in schemaMigrations(testSchema) if migration.name == ORDER_MIGRATIONS[0])
    with appDb.begin() as conn:
        runSql(conn, serviceTypeMigration.up)
    with appDb.connect() as conn:
        codes = conn.execute(text("SELECT service_type_code FROM service_type ORDER BY sort_order")).scalars().all()
    assert codes == SEEDED_SERVICE_TYPES

# Concurrent inserts each get a distinct, well formed order number.
def testConcurrentOrdersGetDistinctNumbers(appDb, ids):
    with ThreadPoolExecutor(max_workers=CONCURRENT_WORKERS) as pool:
        numbers = list(pool.map(lambda _: insertOrder(appDb, ids)[1], range(CONCURRENT_ORDERS)))
    assert len(set(numbers)) == CONCURRENT_ORDERS
    assert all(ORDER_NO_PATTERN.match(number) for number in numbers)

# Order numbers are padded to six digits and grow past 999999 instead of being truncated.
def testOrderNumberIsNotTruncatedPastSixDigits(appDb, ids, execute):
    assert insertOrder(appDb, ids)[1] == "ORD-000001"
    execute("SELECT setval('service_order_no_seq', 999999)")
    assert insertOrder(appDb, ids)[1] == "ORD-1000000"

# Status and assignment must agree: a new order has no technician and every later status has one.
@pytest.mark.parametrize("status,withTechnician", [("new", True), ("assigned", False), ("in_progress", False)])
def testStatusMustMatchAssignment(appDb, ids, status, withTechnician):
    with pytest.raises(ConflictError):
        insertOrder(appDb, ids, status=status, technicianId=ids["technicianId"] if withTechnician else None)

# A customer phone that is not 8 to 15 digits is refused.
@pytest.mark.parametrize("phone", ["0123", "+60123456789", "6012345678901234"])
def testCustomerPhoneMustBeDigits(appDb, ids, execute, phone):
    with pytest.raises(ConflictError):
        execute(INSERT_ORDER.replace("'60123456789'", ":phone"), phone=phone, serviceTypeId=ids["serviceTypeId"], technicianId=None, status="new", adminId=ids["adminId"])

# Completion rows enforce the final amount, the payment pair, the receipt rule, and one completion per order.
@pytest.mark.parametrize("columns,values", [
    ("final_amount", "999"),
    ("final_amount, payment_amount", "170, 170"),
    ("final_amount, payment_method", "170, 'cash'"),
    ("final_amount, receipt_attachment_id", "170, :attachmentId"),
])
def testCompletionChecks(appDb, ids, orderId, execute, columns, values):
    attachmentId = insertAttachment(appDb, ids, orderId, "receipt")
    with pytest.raises(ConflictError):
        execute(
            f"INSERT INTO order_completion (service_order_id, technician_id, work_done, quoted_price, extra_charges, {columns}) "
            f"VALUES (:orderId, :technicianId, 'Done', 150, 20, {values})",
            orderId=orderId, technicianId=ids["technicianId"], attachmentId=attachmentId,
        )

# A second completion for the same order is refused by the unique key.
def testOneCompletionPerOrder(appDb, ids, orderId, execute):
    completion = (
        "INSERT INTO order_completion (service_order_id, technician_id, work_done, quoted_price, extra_charges, final_amount) "
        "VALUES (:orderId, :technicianId, 'Done', 150, 20, 170)"
    )
    execute(completion, orderId=orderId, technicianId=ids["technicianId"])
    with pytest.raises(ConflictError):
        execute(completion, orderId=orderId, technicianId=ids["technicianId"])

# Inserts one pending attachment of the given kind and returns its id.
def insertAttachment(engine, ids, orderId, kind):
    with engine.begin() as conn:
        return conn.execute(text(
            "INSERT INTO order_attachment (service_order_id, kind, storage_path, file_name, content_type, size_bytes, uploaded_by_id) "
            "VALUES (:orderId, :kind, 'orders/' || gen_random_uuid() || '.jpg', 'photo.jpg', 'image/jpeg', 100, :technicianId) "
            "RETURNING order_attachment_id"
        ), {"orderId": orderId, "kind": kind, "technicianId": ids["technicianId"]}).scalar_one()

# Attachments refuse an unknown kind, an unknown status, an empty file, and a reused storage path.
def testAttachmentChecks(appDb, ids, orderId, execute):
    base = (
        "INSERT INTO order_attachment (service_order_id, kind, storage_path, file_name, content_type, size_bytes, status, uploaded_by_id) "
        "VALUES (:orderId, :kind, :path, 'photo.jpg', 'image/jpeg', :size, :status, :technicianId)"
    )
    params = {"orderId": orderId, "technicianId": ids["technicianId"], "kind": "completion", "path": "orders/a.jpg", "size": 100, "status": "pending"}
    execute(base, **params)
    for change in ({"kind": "invoice", "path": "orders/b.jpg"}, {"status": "deleted", "path": "orders/c.jpg"}, {"size": 0, "path": "orders/d.jpg"}, {}):
        with pytest.raises(ConflictError):
            execute(base, **{**params, **change})

# Order events refuse an unknown event type.
def testOrderEventRejectsUnknownType(appDb, ids, orderId, execute):
    event = "INSERT INTO order_event (service_order_id, event_type, actor_id) VALUES (:orderId, :eventType, :actorId)"
    execute(event, orderId=orderId, eventType="created", actorId=ids["adminId"])
    with pytest.raises(ConflictError):
        execute(event, orderId=orderId, eventType="deleted", actorId=ids["adminId"])

# Notifications need a link once ready, and a recipient user id only for technician recipients.
@pytest.mark.parametrize("recipientType,withUser,status,withLink", [
    ("customer", False, "ready", False),
    ("customer", True, "queued", False),
    ("technician", False, "queued", False),
])
def testNotificationChecks(appDb, ids, orderId, execute, recipientType, withUser, status, withLink):
    with pytest.raises(ConflictError):
        execute(
            "INSERT INTO notification (service_order_id, notification_type, recipient_type, recipient_user_id, recipient_name, "
            "recipient_phone, order_no, template_data, status, message, deep_link) "
            "VALUES (:orderId, 'job_done', :recipientType, :userId, 'Customer', '60123456789', 'ORD-000001', '{}', :status, :message, :link)",
            orderId=orderId, recipientType=recipientType, userId=ids["technicianId"] if withUser else None, status=status,
            message="Hi" if withLink else None, link="https://wa.me/60123456789" if withLink else None,
        )

# Valid customer and technician notifications are accepted, queued without a link and ready with one.
def testNotificationAcceptsValidRows(appDb, ids, orderId, execute, scalar):
    insert = (
        "INSERT INTO notification (service_order_id, notification_type, recipient_type, recipient_user_id, recipient_name, "
        "recipient_phone, order_no, template_data, status, message, deep_link) "
        "VALUES (:orderId, :type, :recipientType, :userId, 'Name', '60123456789', 'ORD-000001', '{}', :status, :message, :link)"
    )
    execute(insert, orderId=orderId, type="job_assigned", recipientType="technician", userId=ids["technicianId"], status="queued", message=None, link=None)
    execute(insert, orderId=orderId, type="job_done", recipientType="customer", userId=None, status="ready", message="Hi", link="https://wa.me/60123456789")
    assert scalar("SELECT count(*) FROM notification") == 2

# Rolling back the order migrations and the later ones that alter them removes their tables, the order number function, and its sequence, then they reapply.
def testOrderMigrationsRollBackCleanly(testEngine, testSchema):
    migrations = schemaMigrations(testSchema)
    with testEngine.connect() as conn, conn.begin():
        applyPending(conn, migrations, schema=testSchema)
        rolledBack = []
        for _ in ORDER_MIGRATIONS + LATER_MIGRATIONS:
            rolledBack.extend(rollbackLatest(conn, migrations, schema=testSchema))
        assert rolledBack == list((ORDER_MIGRATIONS + LATER_MIGRATIONS)[::-1])
        assert all(conn.execute(text("SELECT to_regclass(:name)"), {"name": f"{testSchema}.{table}"}).scalar() is None for table in ORDER_TABLES)
        assert conn.execute(text("SELECT to_regclass(:name)"), {"name": f"{testSchema}.service_order_no_seq"}).scalar() is None
        assert conn.execute(text("SELECT to_regprocedure(:name)"), {"name": f"{testSchema}.next_service_order_no()"}).scalar() is None
        assert getHistory(conn, testSchema)[-1][0] == "0009_auth.sql"
        assert applyPending(conn, migrations, schema=testSchema) == list(ORDER_MIGRATIONS + LATER_MIGRATIONS)

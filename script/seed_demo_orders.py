import argparse
import json
import sys
from datetime import datetime, timedelta
from decimal import Decimal
from pathlib import Path
from urllib.parse import urlsplit

BACKEND_DIRECTORY = str(Path(__file__).resolve().parents[1] / "backend")
if BACKEND_DIRECTORY not in sys.path:
    sys.path.insert(0, BACKEND_DIRECTORY)

from sqlalchemy import delete, exists, func, insert, select
from core import config
from core.auth import ROLE_TECHNICIAN
from core.crypto import hashPassword
from core.db import (
    DatabaseError, notificationTable, orderAttachmentTable, orderCompletionTable, orderEventTable, serviceOrderTable, serviceTypeTable,
    sessionTable, transaction, userTable,
)
from modules.user import repository as userRepository

DATA_FILE = Path(__file__).resolve().parent / "data" / "demo_orders.json"
DEMO_ACTOR = "demo-seed"
MOCK_PASSWORD = "P@ssword123"
EXIT_OK = 0
EXIT_FAILED = 1
STATUS_STEPS = (
    ("startedAt", "started", "assigned", "in_progress"),
    ("completedAt", "completed", "in_progress", "job_done"),
    ("reviewedAt", "reviewed", "job_done", "reviewed"),
    ("closedAt", "closed", "reviewed", "closed"),
)


class SeedError(Exception):
    pass


# Returns the database host from DATABASE_URL, without the user or password, so the target can be shown safely.
def targetHost():
    return urlsplit(config.databaseUrl()).hostname or "unknown host"

# Loads the demo data file.
def loadData(path=DATA_FILE):
    return json.loads(path.read_text(encoding="utf-8"))

# Returns the user id for an email, or raises when the user is missing.
def requireUser(conn, email):
    userId = conn.execute(select(userTable.c.user_id).where(userTable.c.email == email)).scalar()
    if userId is None:
        raise SeedError(f"User {email} is missing; run script/seed_user.py first.")
    return userId

# Returns the technician ids by email, creating any demo technician that does not exist yet.
def ensureTechnicians(conn, technicians):
    role = userRepository.findActiveRole(ROLE_TECHNICIAN, conn=conn)
    if role is None:
        raise SeedError("The technician role is missing; apply the migrations first.")
    ids = {}
    passwordHash = None
    for technician in technicians:
        userId = conn.execute(select(userTable.c.user_id).where(userTable.c.email == technician["email"])).scalar()
        if userId is None:
            passwordHash = passwordHash or hashPassword(MOCK_PASSWORD)
            userId = conn.execute(insert(userTable).values(
                name=technician["name"], email=technician["email"], phone=technician["phone"], role_id=role["role_id"],
                password_hash=passwordHash, created_by=DEMO_ACTOR, updated_by=DEMO_ACTOR,
            ).returning(userTable.c.user_id)).scalar_one()
        ids[technician["email"]] = userId
    return ids

# Returns the service type ids by code.
def serviceTypeIds(conn):
    return dict(conn.execute(select(serviceTypeTable.c.service_type_code, serviceTypeTable.c.service_type_id)).all())

# Returns the timestamp an order's status last changed: its latest step, or its creation.
def lastChange(order):
    steps = [order.get("closedAt"), order.get("reviewedAt"), (order.get("completion") or {}).get("completedAt"), order.get("startedAt"), order["createdAt"]]
    return datetime.fromisoformat(next(value for value in steps if value))

# Returns the events of one order, oldest first, as (type, from, to, actor, detail, time).
def orderEvents(order, adminId, managerId, technicianId):
    created = datetime.fromisoformat(order["createdAt"])
    events = [
        ("created", None, "assigned", adminId, {}, created),
        ("assigned", "new", "assigned", adminId, {"technicianId": str(technicianId)}, created + timedelta(seconds=1)),
    ]
    times = {"startedAt": order.get("startedAt"), "completedAt": (order.get("completion") or {}).get("completedAt"),
             "reviewedAt": order.get("reviewedAt"), "closedAt": order.get("closedAt")}
    for postponement in order["postponements"]:
        at = datetime.fromisoformat(postponement["at"])
        status = "in_progress" if times["startedAt"] and datetime.fromisoformat(times["startedAt"]) <= at else "assigned"
        detail = {"reasonCode": postponement["reasonCode"], "newDate": postponement["newDate"], "technicianId": str(technicianId)}
        events.append(("postponed", status, status, technicianId, detail, at))
    for key, eventType, fromStatus, toStatus in STATUS_STEPS:
        if times[key]:
            actor = managerId if eventType in ("reviewed", "closed") else technicianId
            events.append((eventType, fromStatus, toStatus, actor, {}, datetime.fromisoformat(times[key])))
    return sorted(events, key=lambda event: event[5])

# Inserts one demo order, then its events in one batch, then its completion.
def insertDemoOrder(conn, order, adminId, managerId, technicianIds, typeIds):
    technicianId = technicianIds[order["technician"]]
    completion = order.get("completion")
    orderId = conn.execute(insert(serviceOrderTable).values(
        customer_name=order["customerName"], customer_phone=order["customerPhone"], address=order["address"],
        problem_description=order["problemDescription"], service_type_id=typeIds[order["serviceType"]], quoted_price=Decimal(order["quotedPrice"]),
        assigned_technician_id=technicianId, status=order["status"], status_changed_at=lastChange(order),
        started_at=order.get("startedAt"), job_done_at=completion["completedAt"] if completion else None,
        reviewed_at=order.get("reviewedAt"), reviewed_by_id=managerId if order.get("reviewedAt") else None,
        closed_at=order.get("closedAt"), closed_by_id=managerId if order.get("closedAt") else None,
        created_by_id=adminId, created_at=order["createdAt"], created_by=DEMO_ACTOR, updated_at=lastChange(order), updated_by=DEMO_ACTOR,
    ).returning(serviceOrderTable.c.service_order_id)).scalar_one()
    events = [
        {"service_order_id": orderId, "event_type": eventType, "from_status": fromStatus, "to_status": toStatus, "actor_id": actorId,
         "request_id": DEMO_ACTOR, "detail": detail, "created_at": at, "created_by": DEMO_ACTOR}
        for eventType, fromStatus, toStatus, actorId, detail, at in orderEvents(order, adminId, managerId, technicianId)
    ]
    conn.execute(insert(orderEventTable), events)
    if completion:
        quoted, extra = Decimal(order["quotedPrice"]), Decimal(completion["extraCharges"])
        payment = completion.get("payment")
        conn.execute(insert(orderCompletionTable).values(
            service_order_id=orderId, technician_id=technicianId, work_done=completion["workDone"], quoted_price=quoted, extra_charges=extra,
            final_amount=quoted + extra, remarks=completion.get("remarks"),
            payment_amount=Decimal(payment["amount"]) if payment else None, payment_method=payment["method"] if payment else None,
            completed_at=completion["completedAt"], created_at=completion["completedAt"], created_by=DEMO_ACTOR, updated_by=DEMO_ACTOR,
        ))

# Returns the ids of the orders this script created.
def demoOrderIds(conn):
    return select(serviceOrderTable.c.service_order_id).where(serviceOrderTable.c.created_by == DEMO_ACTOR).scalar_subquery()

# Seeds every demo order unless demo orders already exist; returns how many orders were created.
def seedOrders(conn, data):
    if conn.execute(select(func.count()).select_from(serviceOrderTable).where(serviceOrderTable.c.created_by == DEMO_ACTOR)).scalar_one():
        return 0
    adminId = requireUser(conn, data["admin"])
    managerId = requireUser(conn, data["manager"])
    technicianIds = ensureTechnicians(conn, data["technicians"])
    typeIds = serviceTypeIds(conn)
    for order in data["orders"]:
        insertDemoOrder(conn, order, adminId, managerId, technicianIds, typeIds)
    return len(data["orders"])

# Deletes the technicians this script created, with their sessions, unless real orders or events still name them.
def removeDemoUsers(conn):
    used = (
        exists().where(serviceOrderTable.c.assigned_technician_id == userTable.c.user_id)
        | exists().where(orderEventTable.c.actor_id == userTable.c.user_id)
        | exists().where(orderCompletionTable.c.technician_id == userTable.c.user_id)
    )
    demoUsers = select(userTable.c.user_id).where(userTable.c.created_by == DEMO_ACTOR, ~used).scalar_subquery()
    conn.execute(delete(sessionTable).where(sessionTable.c.user_id.in_(demoUsers)))
    return conn.execute(delete(userTable).where(userTable.c.created_by == DEMO_ACTOR, ~used)).rowcount

# Deletes every demo order with its events, completion, files, and notifications, then the demo technicians; returns
# how many orders went. Stored files of demo orders are not deleted, since the demo data has none.
def removeOrders(conn):
    ids = demoOrderIds(conn)
    for table in (orderEventTable, orderCompletionTable, notificationTable, orderAttachmentTable):
        conn.execute(delete(table).where(table.c.service_order_id.in_(ids)))
    removed = conn.execute(delete(serviceOrderTable).where(serviceOrderTable.c.created_by == DEMO_ACTOR)).rowcount
    removeDemoUsers(conn)
    return removed

# Seeds or removes the demo orders from the command line and returns the process exit code.
def main(argv=None):
    parser = argparse.ArgumentParser(description="Load demo service orders for the KPI dashboard from script/data/demo_orders.json.")
    parser.add_argument("--yes", action="store_true", help="Confirm writing to the database named by DATABASE_URL.")
    parser.add_argument("--remove", action="store_true", help="Delete the demo orders instead of creating them.")
    args = parser.parse_args(argv)
    try:
        host = targetHost()
        print(f"Target database host: {host}")
        if not args.yes:
            print("Nothing written. Run again with --yes to confirm this is a development database.", file=sys.stderr)
            return EXIT_FAILED
        with transaction() as conn:
            count = removeOrders(conn) if args.remove else seedOrders(conn, loadData())
    except SeedError as error:
        print(f"Error: {error}", file=sys.stderr)
        return EXIT_FAILED
    except (DatabaseError, RuntimeError) as error:
        print(f"Error: could not write the demo orders ({type(error).__name__}).", file=sys.stderr)
        return EXIT_FAILED
    if args.remove:
        print(f"Removed {count} demo orders.")
    else:
        print(f"Created {count} demo orders." if count else "Skipped: demo orders already exist. Use --remove first to reload them.")
    return EXIT_OK


if __name__ == "__main__":
    sys.exit(main())

__all__ = ["DEMO_ACTOR", "loadData", "main", "orderEvents", "removeOrders", "seedOrders"]

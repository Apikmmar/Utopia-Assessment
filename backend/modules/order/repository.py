from sqlalchemy import case, func, insert, or_, select, update
from core.db import (
    LIKE_ESCAPE, containsPattern, orderEventTable, readAll, readOne, readScalar, runRead, serviceOrderTable, serviceTypeTable, userTable,
)

technicianUser = userTable.alias("technician_user")
actorUser = userTable.alias("actor_user")
ORDER_JOIN = (
    serviceOrderTable
    .join(serviceTypeTable, serviceTypeTable.c.service_type_id == serviceOrderTable.c.service_type_id)
    .outerjoin(technicianUser, technicianUser.c.user_id == serviceOrderTable.c.assigned_technician_id)
)
ORDER_COLUMNS = (
    *serviceOrderTable.c,
    serviceTypeTable.c.service_type_code, serviceTypeTable.c.service_type_name,
    technicianUser.c.name.label("technician_name"), technicianUser.c.phone.label("technician_phone"),
)
LIST_COLUMNS = (
    serviceOrderTable.c.service_order_id, serviceOrderTable.c.order_no, serviceOrderTable.c.customer_name, serviceOrderTable.c.address,
    serviceOrderTable.c.service_type_id, serviceTypeTable.c.service_type_code, serviceTypeTable.c.service_type_name,
    serviceOrderTable.c.quoted_price, serviceOrderTable.c.assigned_technician_id, technicianUser.c.name.label("technician_name"),
    serviceOrderTable.c.status, serviceOrderTable.c.created_at,
)

# Returns the ILIKE pattern matching values that start with a search term, with its wildcards taken literally.
def prefixPattern(search):
    escaped = search.replace(LIKE_ESCAPE, LIKE_ESCAPE * 2).replace("%", LIKE_ESCAPE + "%").replace("_", LIKE_ESCAPE + "_")
    return f"{escaped}%"

# Inserts one order and returns its id.
def insertOrder(values, conn):
    return conn.execute(insert(serviceOrderTable).values(**values).returning(serviceOrderTable.c.service_order_id)).scalar_one()

# Returns one order with its service type and technician, or None.
def getOrder(orderId, conn=None):
    return readOne(select(*ORDER_COLUMNS).select_from(ORDER_JOIN).where(serviceOrderTable.c.service_order_id == orderId), conn)

# Locks one order row in the caller's transaction and returns whether it exists.
def lockOrder(orderId, conn):
    query = select(serviceOrderTable.c.service_order_id).where(serviceOrderTable.c.service_order_id == orderId).with_for_update()
    return runRead(query, conn).first() is not None

# Returns the filter conditions for an order list.
def listConditions(search, statuses, technicianId):
    conditions = []
    if search:
        conditions.append(or_(
            serviceOrderTable.c.order_no.ilike(prefixPattern(search), escape=LIKE_ESCAPE),
            serviceOrderTable.c.customer_name.ilike(containsPattern(search), escape=LIKE_ESCAPE),
        ))
    if statuses:
        conditions.append(serviceOrderTable.c.status.in_(statuses))
    if technicianId is not None:
        conditions.append(serviceOrderTable.c.assigned_technician_id == technicianId)
    return conditions

# Returns one page of orders and the total match count, newest or oldest first with the id as a tie breaker.
def listOrders(conditions, newestFirst, offset, limit, conn=None):
    total = readScalar(select(func.count()).select_from(serviceOrderTable).where(*conditions), conn)
    order = (serviceOrderTable.c.created_at.desc(), serviceOrderTable.c.service_order_id.desc()) if newestFirst else (
        serviceOrderTable.c.created_at, serviceOrderTable.c.service_order_id)
    query = select(*LIST_COLUMNS).select_from(ORDER_JOIN).where(*conditions).order_by(*order).limit(limit).offset(offset)
    return readAll(query, conn), total

# Updates editable fields while the order is in one of the allowed statuses and returns the rows changed.
def updateFields(orderId, values, statuses, actor, conn):
    statement = (
        update(serviceOrderTable)
        .where(serviceOrderTable.c.service_order_id == orderId, serviceOrderTable.c.status.in_(statuses))
        .values(**values, updated_at=func.now(), updated_by=actor)
    )
    return conn.execute(statement).rowcount

# Points an order at a technician while it is assignable, moving a new order to assigned, and returns the rows changed.
def assignTechnician(orderId, technicianId, statuses, actor, conn):
    isNew = serviceOrderTable.c.status == "new"
    statement = (
        update(serviceOrderTable)
        .where(serviceOrderTable.c.service_order_id == orderId, serviceOrderTable.c.status.in_(statuses))
        .values(
            assigned_technician_id=technicianId,
            status=case((isNew, "assigned"), else_=serviceOrderTable.c.status),
            status_changed_at=case((isNew, func.now()), else_=serviceOrderTable.c.status_changed_at),
            updated_at=func.now(), updated_by=actor,
        )
    )
    return conn.execute(statement).rowcount

# Moves an order from one status to the next only if it is still in the first one, and for the given technician
# when set; returns the rows changed, so zero means the order changed underneath.
def transition(orderId, fromStatus, toStatus, extraValues, technicianId, actor, conn):
    conditions = [serviceOrderTable.c.service_order_id == orderId, serviceOrderTable.c.status == fromStatus]
    if technicianId is not None:
        conditions.append(serviceOrderTable.c.assigned_technician_id == technicianId)
    statement = (
        update(serviceOrderTable).where(*conditions)
        .values(status=toStatus, status_changed_at=func.now(), updated_at=func.now(), updated_by=actor, **extraValues)
    )
    return conn.execute(statement).rowcount

# Appends one order event in the caller's transaction.
def insertEvent(values, conn):
    conn.execute(insert(orderEventTable).values(**values))

# Returns an order's events oldest first, with each actor's name.
def listEvents(orderId, conn=None):
    query = (
        select(*orderEventTable.c, actorUser.c.name.label("actor_name"))
        .select_from(orderEventTable.join(actorUser, actorUser.c.user_id == orderEventTable.c.actor_id))
        .where(orderEventTable.c.service_order_id == orderId)
        .order_by(orderEventTable.c.created_at, orderEventTable.c.order_event_id)
    )
    return readAll(query, conn)


__all__ = [
    "assignTechnician",
    "getOrder",
    "insertEvent",
    "insertOrder",
    "listConditions",
    "listEvents",
    "listOrders",
    "lockOrder",
    "transition",
    "updateFields",
]

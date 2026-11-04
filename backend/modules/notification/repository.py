from sqlalchemy import func, or_, select, update
from core.db import LIKE_ESCAPE, notificationTable, readAll, readOne, readScalar, runRead, userTable

openedByUser = userTable.alias("opened_by_user")
NOTIFICATION_JOIN = notificationTable.outerjoin(openedByUser, openedByUser.c.user_id == notificationTable.c.opened_by_id)
NOTIFICATION_COLUMNS = (
    notificationTable.c.notification_id, notificationTable.c.service_order_id, notificationTable.c.order_no,
    notificationTable.c.notification_type, notificationTable.c.channel, notificationTable.c.provider,
    notificationTable.c.recipient_type, notificationTable.c.recipient_user_id, notificationTable.c.recipient_name,
    notificationTable.c.recipient_phone, notificationTable.c.sender_user_id, notificationTable.c.message,
    notificationTable.c.deep_link, notificationTable.c.status, notificationTable.c.job_id, notificationTable.c.ready_at,
    notificationTable.c.opened_at, notificationTable.c.opened_by_id, openedByUser.c.name.label("opened_by_name"),
    notificationTable.c.created_at,
)

# Returns the ILIKE pattern matching values that start with a search term, with its wildcards taken literally.
def prefixPattern(search):
    escaped = search.replace(LIKE_ESCAPE, LIKE_ESCAPE * 2).replace("%", LIKE_ESCAPE + "%").replace("_", LIKE_ESCAPE + "_")
    return f"{escaped}%"

# Inserts one queued notification and returns its id.
def insertNotification(values, conn):
    return conn.execute(notificationTable.insert().values(**values).returning(notificationTable.c.notification_id)).scalar_one()

# Points a notification at the job that delivers it.
def setJob(notificationId, jobId, conn):
    conn.execute(update(notificationTable).where(notificationTable.c.notification_id == notificationId).values(job_id=jobId))

# Returns one notification with the name of whoever opened it, or None.
def getNotification(notificationId, conn=None):
    return readOne(select(*NOTIFICATION_COLUMNS).select_from(NOTIFICATION_JOIN).where(notificationTable.c.notification_id == notificationId), conn)

# Locks one notification row for an update in the caller's transaction and returns it, or None.
def lockNotification(notificationId, conn):
    query = select(notificationTable).where(notificationTable.c.notification_id == notificationId).with_for_update(of=notificationTable)
    row = runRead(query, conn).mappings().first()
    return dict(row) if row is not None else None

# Stores the rendered message and link and marks the notification ready, only while it is still queued.
def markReady(notificationId, message, deepLink, providerMessageId, status, actor, conn):
    statement = (
        update(notificationTable)
        .where(notificationTable.c.notification_id == notificationId, notificationTable.c.status == "queued")
        .values(
            message=message, deep_link=deepLink, provider_message_id=providerMessageId, status=status, ready_at=func.now(),
            error_message=None, updated_at=func.now(), updated_by=actor,
        )
    )
    return conn.execute(statement).rowcount

# Marks a still-queued notification failed with a short reason.
def markFailed(notificationId, reason, actor, conn):
    statement = (
        update(notificationTable)
        .where(notificationTable.c.notification_id == notificationId, notificationTable.c.status == "queued")
        .values(status="failed", error_message=reason, updated_at=func.now(), updated_by=actor)
    )
    return conn.execute(statement).rowcount

# Marks a ready or opened notification opened, keeping the first opening time and user.
def markOpened(notificationId, openableStatuses, actorId, actor, conn):
    statement = (
        update(notificationTable)
        .where(notificationTable.c.notification_id == notificationId, notificationTable.c.status.in_(openableStatuses))
        .values(
            status="opened", opened_at=func.coalesce(notificationTable.c.opened_at, func.now()),
            opened_by_id=func.coalesce(notificationTable.c.opened_by_id, actorId), updated_at=func.now(), updated_by=actor,
        )
    )
    return conn.execute(statement).rowcount

# Returns a failed notification to queued with its error cleared and its new job attached.
def requeue(notificationId, jobId, actor, conn):
    statement = (
        update(notificationTable)
        .where(notificationTable.c.notification_id == notificationId, notificationTable.c.status == "failed")
        .values(status="queued", job_id=jobId, error_message=None, updated_at=func.now(), updated_by=actor)
    )
    return conn.execute(statement).rowcount

# Returns the visibility and filter conditions for a notifications query.
def listConditions(visibleToUserId, statuses, orderId, notificationType, search, senderUserId):
    conditions = []
    if visibleToUserId is not None:
        conditions.append(or_(notificationTable.c.sender_user_id == visibleToUserId, notificationTable.c.recipient_user_id == visibleToUserId))
    if senderUserId is not None:
        conditions.append(notificationTable.c.sender_user_id == senderUserId)
    if statuses:
        conditions.append(notificationTable.c.status.in_(statuses))
    if orderId is not None:
        conditions.append(notificationTable.c.service_order_id == orderId)
    if notificationType:
        conditions.append(notificationTable.c.notification_type == notificationType)
    if search:
        conditions.append(or_(
            notificationTable.c.order_no.ilike(prefixPattern(search), escape=LIKE_ESCAPE),
            notificationTable.c.recipient_name.ilike("%" + prefixPattern(search), escape=LIKE_ESCAPE),
        ))
    return conditions

# Returns one page of notifications, newest first, and the total match count.
def listNotifications(conditions, offset, limit, conn=None):
    total = readScalar(select(func.count()).select_from(notificationTable).where(*conditions), conn)
    query = (
        select(*NOTIFICATION_COLUMNS).select_from(NOTIFICATION_JOIN).where(*conditions)
        .order_by(notificationTable.c.created_at.desc(), notificationTable.c.notification_id.desc())
        .limit(limit).offset(offset)
    )
    return readAll(query, conn), total


__all__ = [
    "getNotification",
    "insertNotification",
    "listConditions",
    "listNotifications",
    "lockNotification",
    "markFailed",
    "markOpened",
    "markReady",
    "requeue",
    "setJob",
]

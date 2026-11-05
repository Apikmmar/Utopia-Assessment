from datetime import datetime
from decimal import Decimal
from uuid import UUID
from zoneinfo import ZoneInfo
from core.auth import ROLE_ADMIN, ROLE_MANAGER, ROLE_TECHNICIAN
from core.db import transaction
from core.error import FORBIDDEN_CODE, NOTIFICATION_NOT_FAILED_CODE, NOTIFICATION_NOT_FOUND_CODE, NOTIFICATION_NOT_READY_CODE, serviceError
from core.logger import getLogger
from modules.notification import repository
from modules.notification.constants import (
    CANNOT_SEND_MESSAGE, DISPLAY_TIMEZONE, ERROR_MESSAGE_MAX_LENGTH, JOB_ASSIGNED_GREETING, JOB_ASSIGNED_LINES,
    JOB_ASSIGNED_NOTES_LABEL, JOB_DONE_TEMPLATE, MESSAGE_MAX_LENGTH, NOT_FAILED_MESSAGE, NOT_FOUND_MESSAGE,
    NOT_READY_MESSAGE, OPENABLE_STATUSES, STATE_PENDING, STATUS_FAILED, STATUSES_BY_STATE, TYPE_JOB_ASSIGNED,
    TYPE_JOB_DONE,
)
from modules.notification.provider import providerFor

log = getLogger(__name__)

MONTH_NAMES = ("Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec")
displayZone = ZoneInfo(DISPLAY_TIMEZONE)

# Returns a value converted to something JSON can hold: times as ISO text, ids and amounts as strings.
def jsonValue(value):
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, (UUID, Decimal)):
        return str(value)
    return value

# Formats an ISO timestamp in Malaysian time, for example "4 Nov 2026, 3:45 PM".
def formatLocalTime(isoText):
    local = datetime.fromisoformat(isoText).astimezone(displayZone)
    hour = local.hour % 12 or 12
    meridiem = "AM" if local.hour < 12 else "PM"
    return f"{local.day} {MONTH_NAMES[local.month - 1]} {local.year}, {hour}:{local.minute:02d} {meridiem}"

# Renders the message text for a notification type from its stored template data.
def renderMessage(notificationType, data):
    if notificationType == TYPE_JOB_DONE:
        return JOB_DONE_TEMPLATE.format(
            customerName=data["customerName"], orderNo=data["orderNo"], technicianName=data["technicianName"],
            time=formatLocalTime(data["completedAt"]),
        )
    if notificationType == TYPE_JOB_ASSIGNED:
        lines = [JOB_ASSIGNED_GREETING.format(technicianName=data["technicianName"], orderNo=data["orderNo"])]
        lines.extend(f"{label}: {template.format(**data)}" for label, template in JOB_ASSIGNED_LINES)
        notes = (data.get("adminNotes") or "").strip()
        if notes:
            lines.append(f"{JOB_ASSIGNED_NOTES_LABEL}: {notes}")
        return "\n".join(lines)
    raise LookupError("UnknownNotificationType")

# Returns whether the user may open a notification in WhatsApp now: admins any, a technician only one they are to send.
def canSend(actor, row):
    if row["status"] not in OPENABLE_STATUSES:
        return False
    return mayOpen(actor, row)

# Returns whether the user's role and relation let them open a notification, whatever its status.
def mayOpen(actor, row):
    if actor.roleCode == ROLE_ADMIN:
        return True
    return actor.roleCode == ROLE_TECHNICIAN and row["sender_user_id"] == actor.userId

# Returns whether the user may see a notification: admins and managers all, a technician only as sender or recipient.
def mayView(actor, row):
    if actor.roleCode in (ROLE_ADMIN, ROLE_MANAGER):
        return True
    return actor.roleCode == ROLE_TECHNICIAN and actor.userId in (row["sender_user_id"], row["recipient_user_id"])

# Returns the response shape of one notification row for this user.
def present(actor, row):
    openedBy = {"user_id": row["opened_by_id"], "name": row["opened_by_name"]} if row["opened_by_id"] else None
    return {
        "notification_id": row["notification_id"], "order_id": row["service_order_id"], "order_no": row["order_no"],
        "notification_type": row["notification_type"], "channel": row["channel"], "recipient_type": row["recipient_type"],
        "recipient_name": row["recipient_name"], "recipient_phone": row["recipient_phone"], "message": row["message"],
        "deep_link": row["deep_link"], "status": row["status"], "ready_at": row["ready_at"], "opened_at": row["opened_at"],
        "opened_by": openedBy, "can_send": canSend(actor, row), "created_at": row["created_at"],
    }

# Stores a notification and prepares its message inside the caller's transaction, returning the stored row.
# The recipient is {type, name, phone, userId}; templateData is the snapshot the message is rendered from.
def create(conn, orderId, orderNo, notificationType, recipient, senderUserId, templateData, requestId, actor):
    notificationId = repository.insertNotification({
        "service_order_id": orderId, "order_no": orderNo, "notification_type": notificationType,
        "recipient_type": recipient["type"], "recipient_user_id": recipient.get("userId"), "recipient_name": recipient["name"],
        "recipient_phone": recipient["phone"], "sender_user_id": senderUserId,
        "template_data": {key: jsonValue(value) for key, value in templateData.items()},
        "request_id": requestId, "created_by": actor, "updated_by": actor,
    }, conn)
    prepare(conn, repository.lockNotification(notificationId, conn), actor)
    return repository.getNotification(notificationId, conn)

# Renders a queued notification's message and link in the caller's transaction and marks it ready; a rendering or
# provider failure marks it failed with the error type, which holds no personal data, so the caller's change still commits.
def prepare(conn, row, actor):
    notificationId = row["notification_id"]
    try:
        message = renderMessage(row["notification_type"], row["template_data"])
        if len(message) > MESSAGE_MAX_LENGTH:
            raise ValueError("MessageTooLong")
        result = providerFor(row["provider"]).deliver(row, message)
    except Exception as error:
        reason = type(error).__name__[:ERROR_MESSAGE_MAX_LENGTH]
        repository.markFailed(notificationId, reason, actor, conn)
        log.error("notification_failed notification_id=%s reason=%s", notificationId, reason)
        return
    repository.markReady(notificationId, message, result.deepLink, result.providerMessageId, result.status, actor, conn)
    log.info("notification_ready notification_id=%s notification_type=%s", notificationId, row["notification_type"])

# Lists notifications for the page and the order panel: technicians only see their own, and sendable keeps only those
# the user is expected to send while they are pending.
def listNotifications(actor, filters, paging):
    statuses = STATUSES_BY_STATE.get(filters.get("state"))
    senderUserId = None
    if filters.get("sendable"):
        if actor.roleCode == ROLE_MANAGER:
            return [], 0
        statuses = statuses or STATUSES_BY_STATE[STATE_PENDING]
        senderUserId = actor.userId if actor.roleCode == ROLE_TECHNICIAN else None
    visibleTo = actor.userId if actor.roleCode == ROLE_TECHNICIAN else None
    conditions = repository.listConditions(visibleTo, statuses, filters.get("orderId"), filters.get("notificationType"), (filters.get("search") or "").strip(), senderUserId)
    rows, total = repository.listNotifications(conditions, paging.offset, paging.pageSize)
    return [present(actor, row) for row in rows], total

# Records that a user opened a ready notification in WhatsApp and returns (notification, error); opening again is allowed.
def markOpened(actor, notificationId):
    with transaction() as conn:
        row = repository.lockNotification(notificationId, conn)
        if row is None or not mayView(actor, row):
            return None, serviceError(NOTIFICATION_NOT_FOUND_CODE, NOT_FOUND_MESSAGE)
        if not mayOpen(actor, row):
            return None, serviceError(FORBIDDEN_CODE, CANNOT_SEND_MESSAGE)
        if row["status"] not in OPENABLE_STATUSES:
            return None, serviceError(NOTIFICATION_NOT_READY_CODE, NOT_READY_MESSAGE)
        repository.markOpened(notificationId, OPENABLE_STATUSES, actor.userId, actor.email, conn)
        opened = repository.getNotification(notificationId, conn)
    log.info("notification_opened notification_id=%s actor_id=%s", notificationId, actor.userId)
    return present(actor, opened), None

# Prepares a failed notification again, admin only, and returns (notification, error); it ends ready or failed.
def retry(actor, notificationId, requestId):
    if actor.roleCode != ROLE_ADMIN:
        return None, serviceError(FORBIDDEN_CODE, CANNOT_SEND_MESSAGE)
    with transaction() as conn:
        row = repository.lockNotification(notificationId, conn)
        if row is None:
            return None, serviceError(NOTIFICATION_NOT_FOUND_CODE, NOT_FOUND_MESSAGE)
        if row["status"] != STATUS_FAILED:
            return None, serviceError(NOTIFICATION_NOT_FAILED_CODE, NOT_FAILED_MESSAGE)
        repository.requeue(notificationId, actor.email, conn)
        prepare(conn, repository.lockNotification(notificationId, conn), actor.email)
        retried = repository.getNotification(notificationId, conn)
    log.info("notification_retried notification_id=%s actor_id=%s request_id=%s", notificationId, actor.userId, requestId)
    return present(actor, retried), None


__all__ = [
    "canSend",
    "create",
    "formatLocalTime",
    "listNotifications",
    "markOpened",
    "prepare",
    "present",
    "renderMessage",
    "retry",
]

from datetime import timedelta
from sqlalchemy import func
from core.auth import ROLE_ADMIN, ROLE_MANAGER, ROLE_TECHNICIAN
from core.businesstime import businessToday
from core.db import transaction
from core.error import (
    FORBIDDEN_CODE, INVALID_TECHNICIAN_CODE, INVALID_TRANSITION_CODE, ORDER_LOCKED_CODE, ORDER_NOT_FOUND_CODE, VALIDATION_FAILED_CODE,
    serviceError,
)
from core.logger import getLogger
from core.money import INVALID_AMOUNT_MESSAGE, formatAmount, parseAmount
from core.phone import INVALID_PHONE_MESSAGE, normaliseCustomerPhone
from modules.notification import service as notificationService
from modules.notification.constants import RECIPIENT_TECHNICIAN, TYPE_JOB_ASSIGNED
from modules.order import repository
from modules.order.constants import (
    ADDRESS_MAX_LENGTH, ADMIN_NOTES_MAX_LENGTH, ASSIGNABLE_STATUSES, CUSTOMER_NAME_MAX_LENGTH, EDITABLE_FIELDS, EDITABLE_STATUSES,
    EVENT_ASSIGNED, EVENT_BY_STATUS, EVENT_CREATED, EVENT_EDITED, EVENT_NOTIFICATION_QUEUED, EVENT_POSTPONED, EVENT_REASSIGNED,
    INVALID_FIELDS_MESSAGE, INVALID_TECHNICIAN_MESSAGE, ORDER_LOCKED_MESSAGE, ORDER_NOT_FOUND_MESSAGE, POSTPONABLE_STATUSES,
    POSTPONE_FAR_DATE_MESSAGE, POSTPONE_MAX_DAYS_AHEAD, POSTPONE_PAST_DATE_MESSAGE, POSTPONE_REASON_MESSAGE, POSTPONE_REASONS,
    PROBLEM_MAX_LENGTH, SORT_NEWEST, STATUS_ASSIGNED,
    STATUS_CLOSED, STATUS_IN_PROGRESS, STATUS_JOB_DONE, STATUS_MESSAGE, STATUS_NEW, STATUS_REVIEWED, STEP_ACTOR_COLUMNS,
    STEP_TIMESTAMPS, TRANSITIONS,
)
from modules.service_type import service as serviceTypeService
from modules.user import service as userService

log = getLogger(__name__)

ORDER_NOT_FOUND = serviceError(ORDER_NOT_FOUND_CODE, ORDER_NOT_FOUND_MESSAGE)
ORDER_LOCKED = serviceError(ORDER_LOCKED_CODE, ORDER_LOCKED_MESSAGE)
INVALID_TECHNICIAN = serviceError(INVALID_TECHNICIAN_CODE, INVALID_TECHNICIAN_MESSAGE, {"technicianId": INVALID_TECHNICIAN_MESSAGE})
NOT_ALLOWED = serviceError(FORBIDDEN_CODE, "You cannot change this order.")
TEXT_LIMITS = {
    "customer_name": CUSTOMER_NAME_MAX_LENGTH,
    "address": ADDRESS_MAX_LENGTH,
    "problem_description": PROBLEM_MAX_LENGTH,
}
REQUIRED_MESSAGES = {
    "customer_name": "Enter the customer's name.",
    "address": "Enter the service address.",
    "problem_description": "Describe the problem.",
}

# Returns whether the actor may move an order between two statuses: the pair must be in the table, the role must
# match, and a technician must be the one assigned.
def canTransition(fromStatus, toStatus, actor, order):
    role = TRANSITIONS.get((fromStatus, toStatus))
    if role is None or actor.roleCode != role:
        return False
    return role != ROLE_TECHNICIAN or order["assigned_technician_id"] == actor.userId

# Returns whether a user may see an order: admins and managers all, a technician only their own.
def mayView(actor, order):
    if actor.roleCode in (ROLE_ADMIN, ROLE_MANAGER):
        return True
    return actor.roleCode == ROLE_TECHNICIAN and order["assigned_technician_id"] == actor.userId

# Returns the VALIDATION_FAILED refusal for a field-to-message map.
def invalidFields(fields):
    return serviceError(VALIDATION_FAILED_CODE, INVALID_FIELDS_MESSAGE, fields)

# Returns the INVALID_TRANSITION refusal naming the order's current status.
def invalidTransition(status):
    return serviceError(INVALID_TRANSITION_CODE, STATUS_MESSAGE.format(status=status))

# Validates and cleans the given order fields, recording each problem in fields under its camelCase name.
def cleanFields(data, fields):
    values = {}
    for column, limit in TEXT_LIMITS.items():
        if column in data:
            text = (data[column] or "").strip()
            if not text:
                fields[EDITABLE_FIELDS[column]] = REQUIRED_MESSAGES[column]
            elif len(text) > limit:
                fields[EDITABLE_FIELDS[column]] = f"Use at most {limit} characters."
            values[column] = text
    if "customer_phone" in data:
        values["customer_phone"] = normaliseCustomerPhone(data["customer_phone"])
        if values["customer_phone"] is None:
            fields["customerPhone"] = INVALID_PHONE_MESSAGE
    if "quoted_price" in data:
        values["quoted_price"] = parseAmount(data["quoted_price"])
        if values["quoted_price"] is None:
            fields["quotedPrice"] = INVALID_AMOUNT_MESSAGE
    if "admin_notes" in data:
        notes = (data["admin_notes"] or "").strip()
        if len(notes) > ADMIN_NOTES_MAX_LENGTH:
            fields["adminNotes"] = f"Use at most {ADMIN_NOTES_MAX_LENGTH} characters."
        values["admin_notes"] = notes or None
    if "service_type_id" in data:
        values["service_type_id"] = data["service_type_id"]
    return values

# Returns the response shape of one order row.
def presentOrder(row):
    technician = None
    if row["assigned_technician_id"] is not None:
        technician = {"user_id": row["assigned_technician_id"], "name": row["technician_name"], "phone": row["technician_phone"]}
    return {
        "order_id": row["service_order_id"], "order_no": row["order_no"], "customer_name": row["customer_name"],
        "customer_phone": row["customer_phone"], "address": row["address"], "problem_description": row["problem_description"],
        "service_type": {"service_type_id": row["service_type_id"], "code": row["service_type_code"], "name": row["service_type_name"]},
        "quoted_price": formatAmount(row["quoted_price"]), "technician": technician, "admin_notes": row["admin_notes"],
        "status": row["status"], "status_changed_at": row["status_changed_at"], "started_at": row["started_at"],
        "job_done_at": row["job_done_at"], "reviewed_at": row["reviewed_at"], "closed_at": row["closed_at"], "created_at": row["created_at"],
    }

# Returns the response shape of one order list row.
def presentListItem(row):
    technician = {"user_id": row["assigned_technician_id"], "name": row["technician_name"]} if row["assigned_technician_id"] else None
    return {
        "order_id": row["service_order_id"], "order_no": row["order_no"], "customer_name": row["customer_name"], "address": row["address"],
        "service_type": {"service_type_id": row["service_type_id"], "code": row["service_type_code"], "name": row["service_type_name"]},
        "quoted_price": formatAmount(row["quoted_price"]), "technician": technician, "status": row["status"], "created_at": row["created_at"],
    }

# Returns the response shape of one order event.
def presentEvent(row):
    return {
        "event_type": row["event_type"], "from_status": row["from_status"], "to_status": row["to_status"],
        "actor": {"user_id": row["actor_id"], "name": row["actor_name"]}, "detail": row["detail"], "created_at": row["created_at"],
    }

# Appends one event for the order in the caller's transaction, timestamped by the clock so events in one
# transaction keep their order.
def recordEvent(conn, orderId, eventType, actor, requestId, fromStatus=None, toStatus=None, detail=None):
    repository.insertEvent({
        "service_order_id": orderId, "event_type": eventType, "from_status": fromStatus, "to_status": toStatus,
        "actor_id": actor.userId, "request_id": requestId, "detail": detail or {}, "created_at": func.clock_timestamp(),
        "created_by": actor.email,
    }, conn)

# Prepares the job_assigned WhatsApp notification to the order's technician and records it; returns the row, or None
# when the technician has no phone to message.
def queueAssignedNotification(conn, actor, order, requestId):
    if not order["technician_phone"]:
        return None
    notification = notificationService.create(
        conn, order["service_order_id"], order["order_no"], TYPE_JOB_ASSIGNED,
        {"type": RECIPIENT_TECHNICIAN, "name": order["technician_name"], "phone": order["technician_phone"], "userId": order["assigned_technician_id"]},
        None,
        {
            "orderNo": order["order_no"], "technicianName": order["technician_name"], "customerName": order["customer_name"],
            "customerPhone": order["customer_phone"], "address": order["address"], "serviceTypeName": order["service_type_name"],
            "adminNotes": order["admin_notes"],
        },
        requestId, actor.email,
    )
    recordNotificationQueued(conn, actor, order["service_order_id"], notification, requestId)
    return notification

# Records on the order's timeline that a notification was queued, in the caller's transaction; other modules that
# queue a notification for an order call this instead of writing order events themselves.
def recordNotificationQueued(conn, actor, orderId, notification, requestId):
    recordEvent(conn, orderId, EVENT_NOTIFICATION_QUEUED, actor, requestId,
                detail={"notificationId": str(notification["notification_id"]), "notificationType": notification["notification_type"]})

# Returns the notification response for a queued row, or None.
def presentNotification(actor, row):
    return notificationService.present(actor, row) if row is not None else None

# Shared access check for other modules: returns (order, error) using the same per-role rule as getOrder, locking the
# row first when asked.
def accessibleOrder(conn, actor, orderId, lock=False):
    if lock and not repository.lockOrder(orderId, conn):
        return None, ORDER_NOT_FOUND
    order = repository.getOrder(orderId, conn)
    if order is None or not mayView(actor, order):
        return None, ORDER_NOT_FOUND
    return order, None

# Creates an order as the admin, assigning a technician and queueing their WhatsApp notification when one is given;
# returns ({order, notification}, error).
def createOrder(actor, data, requestId):
    if actor.roleCode != ROLE_ADMIN:
        return None, NOT_ALLOWED
    fields = {}
    values = cleanFields({column: data.get(column) for column in EDITABLE_FIELDS}, fields)
    if fields:
        return None, invalidFields(fields)
    technicianId = data.get("technician_id")
    with transaction() as conn:
        _, error = serviceTypeService.activeServiceType(conn, values["service_type_id"])
        if error:
            return None, error
        if technicianId is not None and userService.technician(conn, technicianId) is None:
            return None, INVALID_TECHNICIAN
        status = STATUS_ASSIGNED if technicianId is not None else STATUS_NEW
        orderId = repository.insertOrder({
            **values, "assigned_technician_id": technicianId, "status": status, "created_by_id": actor.userId,
            "created_by": actor.email, "updated_by": actor.email,
        }, conn)
        recordEvent(conn, orderId, EVENT_CREATED, actor, requestId, toStatus=status)
        order = repository.getOrder(orderId, conn)
        notification = None
        if technicianId is not None:
            recordEvent(conn, orderId, EVENT_ASSIGNED, actor, requestId, STATUS_NEW, STATUS_ASSIGNED, {"technicianId": str(technicianId)})
            notification = queueAssignedNotification(conn, actor, order, requestId)
    log.info("order_created order_id=%s status=%s actor_id=%s", orderId, status, actor.userId)
    return {"order": presentOrder(order), "notification": presentNotification(actor, notification)}, None

# Lists orders for the user: admins and managers see all, a technician only their own whatever filters they send.
def listOrders(actor, filters, paging):
    technicianId = actor.userId if actor.roleCode == ROLE_TECHNICIAN else filters.get("technicianId")
    conditions = repository.listConditions((filters.get("search") or "").strip(), filters.get("status") or [], technicianId)
    rows, total = repository.listOrders(conditions, filters.get("sort", SORT_NEWEST) == SORT_NEWEST, paging.offset, paging.pageSize)
    return [presentListItem(row) for row in rows], total

# Returns ({order, events}, error); a technician asking for another technician's order gets ORDER_NOT_FOUND.
def getOrder(actor, orderId):
    order = repository.getOrder(orderId)
    if order is None or not mayView(actor, order):
        return None, ORDER_NOT_FOUND
    return {"order": presentOrder(order), "events": [presentEvent(row) for row in repository.listEvents(orderId)]}, None

# Edits an order's details while it is new or assigned, admin only, recording the changed field names; returns
# ({order}, error). Technician changes go through assignTechnician.
def updateOrder(actor, orderId, changes, requestId):
    if actor.roleCode != ROLE_ADMIN:
        return None, NOT_ALLOWED
    fields = {}
    values = cleanFields(changes, fields)
    if fields:
        return None, invalidFields(fields)
    with transaction() as conn:
        current, error = accessibleOrder(conn, actor, orderId, lock=True)
        if error:
            return None, error
        if current["status"] not in EDITABLE_STATUSES:
            return None, ORDER_LOCKED
        if "service_type_id" in values:
            _, error = serviceTypeService.activeServiceType(conn, values["service_type_id"])
            if error:
                return None, error
        changed = {column: value for column, value in values.items() if current[column] != value}
        if changed:
            repository.updateFields(orderId, changed, EDITABLE_STATUSES, actor.email, conn)
            recordEvent(conn, orderId, EVENT_EDITED, actor, requestId, detail={"fields": sorted(EDITABLE_FIELDS[column] for column in changed)})
        order = repository.getOrder(orderId, conn)
    if changed:
        log.info("order_edited order_id=%s actor_id=%s", orderId, actor.userId)
    return {"order": presentOrder(order)}, None

# Assigns or reassigns the technician while the order is new or assigned, admin only, queueing the new technician's
# WhatsApp notification; assigning the same technician again changes nothing. Returns ({order, notification}, error).
def assignTechnician(actor, orderId, technicianId, requestId):
    if actor.roleCode != ROLE_ADMIN:
        return None, NOT_ALLOWED
    with transaction() as conn:
        current, error = accessibleOrder(conn, actor, orderId, lock=True)
        if error:
            return None, error
        if current["status"] not in ASSIGNABLE_STATUSES:
            return None, ORDER_LOCKED
        if userService.technician(conn, technicianId) is None:
            return None, INVALID_TECHNICIAN
        if current["assigned_technician_id"] == technicianId:
            return {"order": presentOrder(current), "notification": None}, None
        repository.assignTechnician(orderId, technicianId, ASSIGNABLE_STATUSES, actor.email, conn)
        previous = current["assigned_technician_id"]
        eventType = EVENT_REASSIGNED if previous is not None else EVENT_ASSIGNED
        detail = {"technicianId": str(technicianId), **({"previousTechnicianId": str(previous)} if previous else {})}
        recordEvent(conn, orderId, eventType, actor, requestId, current["status"], STATUS_ASSIGNED, detail)
        order = repository.getOrder(orderId, conn)
        notification = queueAssignedNotification(conn, actor, order, requestId)
    log.info("order_assigned order_id=%s actor_id=%s", orderId, actor.userId)
    return {"order": presentOrder(order), "notification": presentNotification(actor, notification)}, None

# Applies one status step as a guarded update in the caller's transaction and returns (orderRow, error); when the
# update matches nothing, the order is reloaded to answer 404 or 409 with its current status.
def applyTransition(conn, actor, orderId, fromStatus, toStatus, requestId):
    current, error = accessibleOrder(conn, actor, orderId)
    if error:
        return None, error
    if not canTransition(fromStatus, toStatus, actor, current):
        if current["status"] != fromStatus:
            return None, invalidTransition(current["status"])
        return None, NOT_ALLOWED
    extra = {STEP_TIMESTAMPS[toStatus]: func.now()}
    if toStatus in STEP_ACTOR_COLUMNS:
        extra[STEP_ACTOR_COLUMNS[toStatus]] = actor.userId
    technicianId = actor.userId if actor.roleCode == ROLE_TECHNICIAN else None
    if repository.transition(orderId, fromStatus, toStatus, extra, technicianId, actor.email, conn) == 0:
        latest, error = accessibleOrder(conn, actor, orderId)
        return None, error or invalidTransition(latest["status"])
    recordEvent(conn, orderId, EVENT_BY_STATUS[toStatus], actor, requestId, fromStatus, toStatus)
    log.info("order_status_changed order_id=%s from=%s to=%s actor_id=%s", orderId, fromStatus, toStatus, actor.userId)
    return repository.getOrder(orderId, conn), None

# Runs one status step in its own transaction and returns ({order}, error).
def runTransition(actor, orderId, fromStatus, toStatus, requestId):
    with transaction() as conn:
        order, error = applyTransition(conn, actor, orderId, fromStatus, toStatus, requestId)
    if error:
        return None, error
    return {"order": presentOrder(order)}, None

# The assigned technician starts the job: assigned to in_progress.
def startJob(actor, orderId, requestId):
    return runTransition(actor, orderId, STATUS_ASSIGNED, STATUS_IN_PROGRESS, requestId)

# Called by the completion module inside its transaction: in_progress to job_done. Returns (orderRow, error).
def markJobDone(conn, actor, order, requestId):
    return applyTransition(conn, actor, order["service_order_id"], STATUS_IN_PROGRESS, STATUS_JOB_DONE, requestId)

# A manager reviews a finished job: job_done to reviewed.
def reviewOrder(actor, orderId, requestId):
    return runTransition(actor, orderId, STATUS_JOB_DONE, STATUS_REVIEWED, requestId)

# A manager closes a reviewed order: reviewed to closed.
def closeOrder(actor, orderId, requestId):
    return runTransition(actor, orderId, STATUS_REVIEWED, STATUS_CLOSED, requestId)

# Returns the field errors of a postponement: the reason must be a known code, and the optional new date must be from
# today to the limit ahead, in business time.
def checkPostpone(reasonCode, newDate, today):
    fields = {}
    if reasonCode not in POSTPONE_REASONS:
        fields["reasonCode"] = POSTPONE_REASON_MESSAGE
    if newDate is not None and newDate < today:
        fields["newDate"] = POSTPONE_PAST_DATE_MESSAGE
    elif newDate is not None and newDate > today + timedelta(days=POSTPONE_MAX_DAYS_AHEAD):
        fields["newDate"] = POSTPONE_FAR_DATE_MESSAGE
    return fields

# Records a postponed visit by the assigned technician or an admin while the order is assigned or in progress,
# crediting the order's technician; the status does not change. Returns ({order}, error).
def postponeOrder(actor, orderId, reasonCode, newDate, requestId, today=None):
    if actor.roleCode not in (ROLE_ADMIN, ROLE_TECHNICIAN):
        return None, NOT_ALLOWED
    fields = checkPostpone(reasonCode, newDate, today or businessToday())
    if fields:
        return None, invalidFields(fields)
    with transaction() as conn:
        current, error = accessibleOrder(conn, actor, orderId, lock=True)
        if error:
            return None, error
        status = current["status"]
        if status not in POSTPONABLE_STATUSES:
            return None, invalidTransition(status)
        detail = {
            "reasonCode": reasonCode, "newDate": newDate.isoformat() if newDate else None,
            "technicianId": str(current["assigned_technician_id"]),
        }
        recordEvent(conn, orderId, EVENT_POSTPONED, actor, requestId, status, status, detail)
        order = repository.getOrder(orderId, conn)
    log.info("order_postponed order_id=%s actor_id=%s reason_code=%s", orderId, actor.userId, reasonCode)
    return {"order": presentOrder(order)}, None


__all__ = [
    "accessibleOrder",
    "assignTechnician",
    "canTransition",
    "checkPostpone",
    "closeOrder",
    "createOrder",
    "getOrder",
    "invalidTransition",
    "listOrders",
    "markJobDone",
    "postponeOrder",
    "presentOrder",
    "recordNotificationQueued",
    "reviewOrder",
    "startJob",
    "updateOrder",
]

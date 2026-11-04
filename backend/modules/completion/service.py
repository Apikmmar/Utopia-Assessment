from core.auth import ROLE_TECHNICIAN
from core.db import connection, transaction
from core.error import COMPLETION_EXISTS_CODE, COMPLETION_NOT_FOUND_CODE, FORBIDDEN_CODE, VALIDATION_FAILED_CODE, serviceError
from core.logger import getLogger
from core.money import INVALID_AMOUNT_MESSAGE, formatAmount, parseAmount
from modules.attachment import service as attachmentService
from modules.completion import repository
from modules.completion.constants import (
    COMPLETION_EXISTS_MESSAGE, COMPLETION_NOT_FOUND_MESSAGE, INVALID_FIELDS_MESSAGE, NOT_ALLOWED_MESSAGE, REMARKS_MAX_LENGTH,
    TEXT_TOO_LONG_MESSAGE, WORK_DONE_MAX_LENGTH, WORK_DONE_REQUIRED_MESSAGE,
)
from modules.notification import service as notificationService
from modules.notification.constants import RECIPIENT_CUSTOMER, TYPE_JOB_DONE
from modules.order import service as orderService

log = getLogger(__name__)

STATUS_IN_PROGRESS = "in_progress"
STATUS_JOB_DONE = "job_done"
COMPLETION_EXISTS = serviceError(COMPLETION_EXISTS_CODE, COMPLETION_EXISTS_MESSAGE)
COMPLETION_NOT_FOUND = serviceError(COMPLETION_NOT_FOUND_CODE, COMPLETION_NOT_FOUND_MESSAGE)
NOT_ALLOWED = serviceError(FORBIDDEN_CODE, NOT_ALLOWED_MESSAGE)


class Refused(Exception):
    # Carries a service refusal out of a transaction so every write in it rolls back.
    def __init__(self, error):
        super().__init__(error["code"])
        self.error = error


# Validates and cleans the completion fields, recording each problem in fields under its camelCase name.
def cleanCompletion(data, fields):
    workDone = (data.get("work_done") or "").strip()
    if not workDone:
        fields["workDone"] = WORK_DONE_REQUIRED_MESSAGE
    elif len(workDone) > WORK_DONE_MAX_LENGTH:
        fields["workDone"] = TEXT_TOO_LONG_MESSAGE.format(limit=WORK_DONE_MAX_LENGTH)
    remarks = (data.get("remarks") or "").strip()
    if len(remarks) > REMARKS_MAX_LENGTH:
        fields["remarks"] = TEXT_TOO_LONG_MESSAGE.format(limit=REMARKS_MAX_LENGTH)
    rawExtra = data.get("extra_charges")
    extraCharges = parseAmount(0 if rawExtra is None or rawExtra == "" else rawExtra)
    if extraCharges is None:
        fields["extraCharges"] = INVALID_AMOUNT_MESSAGE
    values = {"work_done": workDone, "remarks": remarks or None, "extra_charges": extraCharges,
              "payment_amount": None, "payment_method": None, "receipt_attachment_id": None}
    payment = data.get("payment")
    if payment is not None:
        values["payment_amount"] = parseAmount(payment.get("amount"))
        if values["payment_amount"] is None:
            fields["payment.amount"] = INVALID_AMOUNT_MESSAGE
        values["payment_method"] = payment.get("method")
        values["receipt_attachment_id"] = payment.get("receipt_attachment_id")
    return values

# Returns the response shape of one completion row.
def present(row):
    payment = None
    if row["payment_amount"] is not None:
        payment = {"amount": formatAmount(row["payment_amount"]), "method": row["payment_method"],
                   "receipt_attachment_id": row["receipt_attachment_id"]}
    return {
        "completion_id": row["order_completion_id"], "order_id": row["service_order_id"],
        "technician": {"user_id": row["technician_id"], "name": row["technician_name"]}, "work_done": row["work_done"],
        "quoted_price": formatAmount(row["quoted_price"]), "extra_charges": formatAmount(row["extra_charges"]),
        "final_amount": formatAmount(row["final_amount"]), "remarks": row["remarks"], "payment": payment,
        "completed_at": row["completed_at"],
    }

# Returns (order, error) for an order the technician may complete now: theirs, and still in progress.
def completableOrder(conn, actor, orderId, lock=False):
    order, error = orderService.accessibleOrder(conn, actor, orderId, lock=lock)
    if error:
        return None, error
    if order["status"] != STATUS_IN_PROGRESS:
        return None, orderService.invalidTransition(order["status"])
    if not orderService.canTransition(STATUS_IN_PROGRESS, STATUS_JOB_DONE, actor, order):
        return None, NOT_ALLOWED
    return order, None

# Writes the completion, confirms its files, moves the order to job_done, and queues the customer's WhatsApp message,
# all in one transaction; a refusal raises Refused so nothing is kept. Returns (completionRow, orderRow, notification).
def saveCompletion(actor, orderId, values, verified, requestId):
    with transaction() as conn:
        order, error = completableOrder(conn, actor, orderId, lock=True)
        if error:
            raise Refused(error)
        completionId, conflict = repository.insertCompletion({
            **values, "service_order_id": orderId, "technician_id": actor.userId, "quoted_price": order["quoted_price"],
            "final_amount": order["quoted_price"] + values["extra_charges"], "created_by": actor.email, "updated_by": actor.email,
        }, COMPLETION_EXISTS, conn)
        if conflict:
            raise Refused(conflict)
        error = attachmentService.confirm(conn, verified, actor)
        if error:
            raise Refused(error)
        order, error = orderService.markJobDone(conn, actor, order, requestId)
        if error:
            raise Refused(error)
        completion = repository.getCompletion(orderId, conn)
        notification = notificationService.enqueue(
            conn, orderId, order["order_no"], TYPE_JOB_DONE,
            {"type": RECIPIENT_CUSTOMER, "name": order["customer_name"], "phone": order["customer_phone"]},
            actor.userId,
            {"orderNo": order["order_no"], "customerName": order["customer_name"], "technicianName": completion["technician_name"],
             "completedAt": completion["completed_at"]},
            requestId, actor.email,
        )
        orderService.recordNotificationQueued(conn, actor, orderId, notification, requestId)
    return completion, order, notification

# The assigned technician records the finished job: validate, check the order, verify the files in storage with no
# transaction open, then save everything at once. Returns ({completion, order, notification}, error).
def submitCompletion(actor, orderId, data, requestId):
    if actor.roleCode != ROLE_TECHNICIAN:
        return None, NOT_ALLOWED
    fields = {}
    values = cleanCompletion(data, fields)
    if fields:
        return None, serviceError(VALIDATION_FAILED_CODE, INVALID_FIELDS_MESSAGE, fields)
    with connection() as conn:
        order, error = completableOrder(conn, actor, orderId)
    if error:
        return None, error
    verified, error = attachmentService.verifyForCompletion(actor, order, data.get("attachment_ids") or [], values["receipt_attachment_id"])
    if error:
        return None, error
    try:
        completion, order, notification = saveCompletion(actor, orderId, values, verified, requestId)
    except Refused as refused:
        return None, refused.error
    log.info("completion_submitted order_id=%s completion_id=%s actor_id=%s", orderId, completion["order_completion_id"], actor.userId)
    return {
        "completion": present(completion), "order": orderService.presentOrder(order),
        "notification": notificationService.present(actor, notification),
    }, None

# Returns ({completion}, error) for anyone who may see the order; COMPLETION_NOT_FOUND until the job is done.
def getCompletion(actor, orderId):
    with connection() as conn:
        _, error = orderService.accessibleOrder(conn, actor, orderId)
        if error:
            return None, error
        row = repository.getCompletion(orderId, conn)
    if row is None:
        return None, COMPLETION_NOT_FOUND
    return {"completion": present(row)}, None


__all__ = ["cleanCompletion", "getCompletion", "present", "submitCompletion"]

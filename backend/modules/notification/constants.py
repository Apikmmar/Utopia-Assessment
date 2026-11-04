JOB_TYPE_DELIVER = "notification.deliver"

TYPE_JOB_ASSIGNED = "job_assigned"
TYPE_JOB_DONE = "job_done"
NOTIFICATION_TYPES = (TYPE_JOB_ASSIGNED, TYPE_JOB_DONE)

RECIPIENT_CUSTOMER = "customer"
RECIPIENT_TECHNICIAN = "technician"

STATUS_QUEUED = "queued"
STATUS_READY = "ready"
STATUS_OPENED = "opened"
STATUS_SENT = "sent"
STATUS_FAILED = "failed"
OPENABLE_STATUSES = (STATUS_READY, STATUS_OPENED)

STATE_PENDING = "pending"
STATE_SENT = "sent"
STATUSES_BY_STATE = {
    STATE_PENDING: (STATUS_QUEUED, STATUS_READY, STATUS_FAILED),
    STATE_SENT: (STATUS_OPENED, STATUS_SENT),
}

PROVIDER_DEEPLINK = "deeplink"
WHATSAPP_BASE_URL = "https://wa.me/"
DISPLAY_TIMEZONE = "Asia/Kuala_Lumpur"

MESSAGE_MAX_LENGTH = 4000
DEEP_LINK_MAX_LENGTH = 8000
ERROR_MESSAGE_MAX_LENGTH = 500
SEARCH_MAX_LENGTH = 100

JOB_DONE_TEMPLATE = (
    "Hi {customerName}, Job {orderNo} has been completed by Technician {technicianName} at {time}. "
    "Please check and leave feedback. Thank you!"
)
JOB_ASSIGNED_GREETING = "Hi {technicianName}, you have a new job: {orderNo}."
JOB_ASSIGNED_LINES = (
    ("Customer", "{customerName} ({customerPhone})"),
    ("Address", "{address}"),
    ("Service", "{serviceTypeName}"),
)
JOB_ASSIGNED_NOTES_LABEL = "Instructions"

NOT_FOUND_MESSAGE = "Notification not found."
NOT_READY_MESSAGE = "This message is still being prepared or could not be prepared, so it cannot be sent yet."
NOT_FAILED_MESSAGE = "Only a failed notification can be retried."
CANNOT_SEND_MESSAGE = "You cannot send this notification."


__all__ = [
    "DEEP_LINK_MAX_LENGTH",
    "DISPLAY_TIMEZONE",
    "ERROR_MESSAGE_MAX_LENGTH",
    "JOB_ASSIGNED_GREETING",
    "JOB_ASSIGNED_LINES",
    "JOB_ASSIGNED_NOTES_LABEL",
    "JOB_DONE_TEMPLATE",
    "JOB_TYPE_DELIVER",
    "MESSAGE_MAX_LENGTH",
    "NOTIFICATION_TYPES",
    "OPENABLE_STATUSES",
    "PROVIDER_DEEPLINK",
    "RECIPIENT_CUSTOMER",
    "RECIPIENT_TECHNICIAN",
    "SEARCH_MAX_LENGTH",
    "STATE_PENDING",
    "STATE_SENT",
    "STATUSES_BY_STATE",
    "STATUS_FAILED",
    "STATUS_OPENED",
    "STATUS_QUEUED",
    "STATUS_READY",
    "STATUS_SENT",
    "TYPE_JOB_ASSIGNED",
    "TYPE_JOB_DONE",
    "WHATSAPP_BASE_URL",
]

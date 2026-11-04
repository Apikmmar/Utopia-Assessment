PAYMENT_METHODS = ("cash", "card", "bank_transfer", "ewallet")

WORK_DONE_MAX_LENGTH = 2000
REMARKS_MAX_LENGTH = 2000
TEXT_INPUT_MAX_LENGTH = 4000
ATTACHMENT_IDS_MAX = 20

WORK_DONE_REQUIRED_MESSAGE = "Describe the work done."
TEXT_TOO_LONG_MESSAGE = "Use at most {limit} characters."
INVALID_FIELDS_MESSAGE = "One or more fields are invalid."
COMPLETION_EXISTS_MESSAGE = "This job already has a completion record."
COMPLETION_NOT_FOUND_MESSAGE = "This job has no completion record yet."
NOT_ALLOWED_MESSAGE = "Only the assigned technician can complete this job."


__all__ = [
    "ATTACHMENT_IDS_MAX",
    "COMPLETION_EXISTS_MESSAGE",
    "COMPLETION_NOT_FOUND_MESSAGE",
    "INVALID_FIELDS_MESSAGE",
    "NOT_ALLOWED_MESSAGE",
    "PAYMENT_METHODS",
    "REMARKS_MAX_LENGTH",
    "TEXT_INPUT_MAX_LENGTH",
    "TEXT_TOO_LONG_MESSAGE",
    "WORK_DONE_MAX_LENGTH",
    "WORK_DONE_REQUIRED_MESSAGE",
]

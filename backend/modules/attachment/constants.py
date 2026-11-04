MEGABYTE = 1024 * 1024

KIND_COMPLETION = "completion"
KIND_RECEIPT = "receipt"
ATTACHMENT_KINDS = (KIND_COMPLETION, KIND_RECEIPT)

STATUS_PENDING = "pending"
STATUS_UPLOADED = "uploaded"

IMAGE_TYPES = ("image/jpeg", "image/png", "image/webp", "image/heic")
VIDEO_TYPES = ("video/mp4", "video/quicktime")
DOCUMENT_TYPES = ("application/pdf",)

IMAGE_MAX_BYTES = 10 * MEGABYTE
VIDEO_MAX_BYTES = 49 * MEGABYTE

MAX_BYTES_BY_TYPE = {
    **{contentType: IMAGE_MAX_BYTES for contentType in IMAGE_TYPES + DOCUMENT_TYPES},
    **{contentType: VIDEO_MAX_BYTES for contentType in VIDEO_TYPES},
}
ATTACHMENT_LIMITS = {
    KIND_COMPLETION: {"maxCount": 6, "types": IMAGE_TYPES + VIDEO_TYPES + DOCUMENT_TYPES},
    KIND_RECEIPT: {"maxCount": 1, "types": IMAGE_TYPES + DOCUMENT_TYPES},
}
EXTENSION_BY_TYPE = {
    "image/jpeg": "jpg",
    "image/png": "png",
    "image/webp": "webp",
    "image/heic": "heic",
    "video/mp4": "mp4",
    "video/quicktime": "mov",
    "application/pdf": "pdf",
}

BUCKET_FILE_SIZE_LIMIT = VIDEO_MAX_BYTES
BUCKET_ALLOWED_TYPES = IMAGE_TYPES + VIDEO_TYPES + DOCUMENT_TYPES

SIGNATURE_BYTES = 16
STORAGE_PREFIX = "orders"
FILE_NAME_MAX_LENGTH = 255

ORDER_NOT_IN_PROGRESS_MESSAGE = "Files can be added only while the job is in progress."
LIMIT_MESSAGE = "This job already has the most files of this kind ({maxCount})."
INVALID_TYPE_MESSAGE = "This file type is not allowed. Use a photo, a short video, or a PDF."
TOO_LARGE_MESSAGE = "This file is too large. The limit is {limitMb} MB for this type."
NOT_UPLOADED_MESSAGE = "A file has not finished uploading. Upload it again or remove it."
NOT_FOUND_MESSAGE = "File not found."
LOCKED_MESSAGE = "This file is already saved with the completion and cannot be removed."
WRONG_FILE_MESSAGE = "A file does not belong to this job."
CONTENT_MISMATCH_MESSAGE = "A file's content does not match its type."


__all__ = [
    "ATTACHMENT_KINDS",
    "ATTACHMENT_LIMITS",
    "BUCKET_ALLOWED_TYPES",
    "BUCKET_FILE_SIZE_LIMIT",
    "CONTENT_MISMATCH_MESSAGE",
    "EXTENSION_BY_TYPE",
    "FILE_NAME_MAX_LENGTH",
    "IMAGE_MAX_BYTES",
    "INVALID_TYPE_MESSAGE",
    "KIND_COMPLETION",
    "KIND_RECEIPT",
    "LIMIT_MESSAGE",
    "LOCKED_MESSAGE",
    "MAX_BYTES_BY_TYPE",
    "MEGABYTE",
    "NOT_FOUND_MESSAGE",
    "NOT_UPLOADED_MESSAGE",
    "ORDER_NOT_IN_PROGRESS_MESSAGE",
    "SIGNATURE_BYTES",
    "STATUS_PENDING",
    "STATUS_UPLOADED",
    "STORAGE_PREFIX",
    "TOO_LARGE_MESSAGE",
    "VIDEO_MAX_BYTES",
    "WRONG_FILE_MESSAGE",
]

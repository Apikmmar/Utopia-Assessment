import uuid
from core import config
from core import storage as coreStorage
from core.auth import ROLE_TECHNICIAN
from core.db import transaction
from core.error import (
    ATTACHMENT_INVALID_CODE, ATTACHMENT_LIMIT_CODE, ATTACHMENT_LOCKED_CODE, ATTACHMENT_NOT_FOUND_CODE, ATTACHMENT_NOT_UPLOADED_CODE,
    FORBIDDEN_CODE, INVALID_TRANSITION_CODE, serviceError,
)
from core.logger import getLogger
from modules.attachment import repository
from modules.attachment.constants import (
    ATTACHMENT_LIMITS, CONTENT_MISMATCH_MESSAGE, EXTENSION_BY_TYPE, INVALID_TYPE_MESSAGE, KIND_COMPLETION, KIND_RECEIPT, LIMIT_MESSAGE,
    LOCKED_MESSAGE, MAX_BYTES_BY_TYPE, MEGABYTE, NOT_FOUND_MESSAGE, NOT_UPLOADED_MESSAGE, ORDER_NOT_IN_PROGRESS_MESSAGE, SIGNATURE_BYTES,
    STATUS_PENDING, STATUS_UPLOADED, STORAGE_PREFIX, TOO_LARGE_MESSAGE, WRONG_FILE_MESSAGE,
)
from modules.order import service as orderService

log = getLogger(__name__)

STATUS_IN_PROGRESS = "in_progress"
NOT_IN_PROGRESS = serviceError(INVALID_TRANSITION_CODE, ORDER_NOT_IN_PROGRESS_MESSAGE)
NOT_FOUND = serviceError(ATTACHMENT_NOT_FOUND_CODE, NOT_FOUND_MESSAGE)
LOCKED = serviceError(ATTACHMENT_LOCKED_CODE, LOCKED_MESSAGE)
NOT_UPLOADED = serviceError(ATTACHMENT_NOT_UPLOADED_CODE, NOT_UPLOADED_MESSAGE)
NOT_ALLOWED = serviceError(FORBIDDEN_CODE, "Only the assigned technician can change this job's files.")
ISO_MEDIA_BRANDS = {
    "image/heic": (b"heic", b"heix", b"hevc", b"hevx", b"mif1", b"msf1", b"heim", b"heis"),
    "video/quicktime": (b"qt  ",),
}
QUICKTIME_ATOMS = (b"moov", b"mdat", b"wide", b"free", b"skip", b"pnot")

# Returns the ATTACHMENT_INVALID refusal with one message.
def invalid(message):
    return serviceError(ATTACHMENT_INVALID_CODE, message)

# Returns a refusal when a content type or size is outside the limits for its kind, or None when it is allowed.
def checkTypeAndSize(kind, contentType, sizeBytes):
    if contentType not in ATTACHMENT_LIMITS[kind]["types"]:
        return invalid(INVALID_TYPE_MESSAGE)
    limit = MAX_BYTES_BY_TYPE[contentType]
    if sizeBytes < 1 or sizeBytes > limit:
        return invalid(TOO_LARGE_MESSAGE.format(limitMb=limit // MEGABYTE))
    return None

# Returns whether a file's first bytes match its content type, so a renamed or mislabelled file is refused.
def matchesSignature(contentType, head):
    if contentType == "image/jpeg":
        return head.startswith(b"\xff\xd8\xff")
    if contentType == "image/png":
        return head.startswith(b"\x89PNG\r\n\x1a\n")
    if contentType == "image/webp":
        return head[:4] == b"RIFF" and head[8:12] == b"WEBP"
    if contentType == "application/pdf":
        return head.startswith(b"%PDF-")
    if contentType == "image/heic":
        return head[4:8] == b"ftyp" and head[8:12] in ISO_MEDIA_BRANDS["image/heic"]
    if contentType == "video/mp4":
        return head[4:8] == b"ftyp" and head[8:12] not in ISO_MEDIA_BRANDS["image/heic"]
    if contentType == "video/quicktime":
        return (head[4:8] == b"ftyp" and head[8:12] not in ISO_MEDIA_BRANDS["image/heic"]) or head[4:8] in QUICKTIME_ATOMS
    return False

# Returns the storage path for an attachment, built from ids only and never from the user's file name.
def storagePath(orderId, attachmentId, contentType):
    return f"{STORAGE_PREFIX}/{orderId}/{attachmentId}.{EXTENSION_BY_TYPE[contentType]}"

# Returns the response shape of one attachment with its view link, or none while pending.
def present(row, viewUrl=None):
    return {
        "attachment_id": row["order_attachment_id"], "kind": row["kind"], "file_name": row["file_name"],
        "content_type": row["content_type"], "size_bytes": row["size_bytes"], "status": row["status"], "view_url": viewUrl,
    }

# Returns (order, error) for a change to this job's files: the order must be visible, assigned to the technician,
# and in progress; the row is locked when asked.
def editableOrder(conn, actor, orderId, lock):
    if actor.roleCode != ROLE_TECHNICIAN:
        return None, NOT_ALLOWED
    order, error = orderService.accessibleOrder(conn, actor, orderId, lock=lock)
    if error:
        return None, error
    if order["status"] != STATUS_IN_PROGRESS:
        return None, NOT_IN_PROGRESS
    return order, None

# Records a pending file for the assigned technician's job and returns ({attachment, uploadUrl}, error). The count
# check runs under the order row lock, and storage is asked for the signed URL only after the row is committed.
def requestUpload(actor, orderId, kind, fileName, contentType, sizeBytes):
    storage = coreStorage.getStorage()
    error = checkTypeAndSize(kind, contentType, sizeBytes)
    if error:
        return None, error
    attachmentId = uuid.uuid4()
    path = storagePath(orderId, attachmentId, contentType)
    with transaction() as conn:
        _, error = editableOrder(conn, actor, orderId, lock=True)
        if error:
            return None, error
        maxCount = ATTACHMENT_LIMITS[kind]["maxCount"]
        if repository.countByKind(orderId, kind, conn) >= maxCount:
            return None, serviceError(ATTACHMENT_LIMIT_CODE, LIMIT_MESSAGE.format(maxCount=maxCount))
        repository.insertAttachment({
            "order_attachment_id": attachmentId, "service_order_id": orderId, "kind": kind, "storage_path": path,
            "file_name": fileName.strip() or "file", "content_type": contentType, "size_bytes": sizeBytes,
            "uploaded_by_id": actor.userId, "created_by": actor.email, "updated_by": actor.email,
        }, conn)
        row = repository.getAttachment(orderId, attachmentId, conn)
    try:
        uploadUrl = storage.signUpload(path)
    except coreStorage.StorageUnavailable:
        with transaction() as conn:
            repository.deletePending(attachmentId, conn)
        raise
    log.info("attachment_requested attachment_id=%s order_id=%s kind=%s", attachmentId, orderId, kind)
    return {"attachment": present(row), "upload_url": uploadUrl}, None

# Removes one pending file of the assigned technician's job, then its stored object if it was uploaded; returns (None, error).
def deletePending(actor, orderId, attachmentId):
    with transaction() as conn:
        _, error = editableOrder(conn, actor, orderId, lock=True)
        if error:
            return None, error
        row = repository.getAttachment(orderId, attachmentId, conn)
        if row is None:
            return None, NOT_FOUND
        if row["status"] != STATUS_PENDING:
            return None, LOCKED
        repository.deletePending(attachmentId, conn)
    coreStorage.getStorage().deleteObject(row["storage_path"])
    log.info("attachment_deleted attachment_id=%s order_id=%s", attachmentId, orderId)
    return None, None

# Checks every file a completion names before its transaction: each must belong to the order, be pending and of the
# right kind, and exist in storage with an allowed size and matching content. Returns (verified, error), where
# verified maps each id to the size and type storage reported.
def verifyForCompletion(actor, order, completionIds, receiptId):
    wanted = {attachmentId: KIND_COMPLETION for attachmentId in completionIds}
    if receiptId is not None:
        wanted[receiptId] = KIND_RECEIPT
    if len(wanted) != len(completionIds) + (1 if receiptId is not None else 0):
        return None, invalid(WRONG_FILE_MESSAGE)
    if len(completionIds) > ATTACHMENT_LIMITS[KIND_COMPLETION]["maxCount"]:
        return None, serviceError(ATTACHMENT_LIMIT_CODE, LIMIT_MESSAGE.format(maxCount=ATTACHMENT_LIMITS[KIND_COMPLETION]["maxCount"]))
    rows = {row["order_attachment_id"]: row for row in repository.getAttachments(list(wanted))}
    for attachmentId, kind in wanted.items():
        row = rows.get(attachmentId)
        if row is None or row["service_order_id"] != order["service_order_id"] or row["kind"] != kind or row["status"] != STATUS_PENDING:
            return None, invalid(WRONG_FILE_MESSAGE)
    if not wanted:
        return {}, None
    storage = coreStorage.getStorage()
    verified = {}
    for attachmentId, kind in wanted.items():
        path = rows[attachmentId]["storage_path"]
        info = storage.objectInfo(path)
        if info is None:
            return None, NOT_UPLOADED
        error = checkTypeAndSize(kind, info["contentType"], info["sizeBytes"])
        if error:
            return None, error
        head = storage.readHead(path, SIGNATURE_BYTES)
        if head is None:
            return None, NOT_UPLOADED
        if not matchesSignature(info["contentType"], head):
            return None, invalid(CONTENT_MISMATCH_MESSAGE)
        verified[attachmentId] = info
    return verified, None

# Marks the verified files uploaded inside the completion transaction, with the size and type storage reported.
def confirm(conn, verified, actor):
    for attachmentId, info in verified.items():
        repository.confirm(attachmentId, info["sizeBytes"], info["contentType"], actor.email, conn)

# Lists an order's files for anyone who may see it: uploaded files with short-lived view links signed in one call,
# and for the assigned technician their pending files too, so an upload in progress survives a reload.
def listAttachments(actor, orderId):
    with transaction() as conn:
        order, error = orderService.accessibleOrder(conn, actor, orderId)
        if error:
            return None, error
        rows = repository.listForOrder(orderId, conn)
    isAssigned = actor.roleCode == ROLE_TECHNICIAN and order["assigned_technician_id"] == actor.userId
    uploaded = [row for row in rows if row["status"] == STATUS_UPLOADED]
    visible = [row for row in rows if row["status"] == STATUS_UPLOADED or isAssigned]
    viewUrls = {}
    if uploaded:
        signed = coreStorage.getStorage().signViews([row["storage_path"] for row in uploaded], config.storageViewUrlSeconds())
        viewUrls = {row["order_attachment_id"]: url for row, url in zip(uploaded, signed)}
    return [present(row, viewUrls.get(row["order_attachment_id"])) for row in visible], None


__all__ = [
    "checkTypeAndSize",
    "confirm",
    "deletePending",
    "listAttachments",
    "matchesSignature",
    "requestUpload",
    "storagePath",
    "verifyForCompletion",
]

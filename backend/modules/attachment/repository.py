from sqlalchemy import delete, func, select, update
from core.db import orderAttachmentTable, readAll, readOne, readScalar

# Returns how many files of one kind an order holds, pending and uploaded alike.
def countByKind(orderId, kind, conn):
    query = select(func.count()).select_from(orderAttachmentTable).where(
        orderAttachmentTable.c.service_order_id == orderId, orderAttachmentTable.c.kind == kind,
    )
    return readScalar(query, conn)

# Inserts one pending attachment row.
def insertAttachment(values, conn):
    conn.execute(orderAttachmentTable.insert().values(**values))

# Returns one attachment of an order, or None.
def getAttachment(orderId, attachmentId, conn=None):
    query = select(orderAttachmentTable).where(
        orderAttachmentTable.c.service_order_id == orderId, orderAttachmentTable.c.order_attachment_id == attachmentId,
    )
    return readOne(query, conn)

# Returns the attachments with the given ids, whatever order they belong to.
def getAttachments(attachmentIds, conn=None):
    if not attachmentIds:
        return []
    return readAll(select(orderAttachmentTable).where(orderAttachmentTable.c.order_attachment_id.in_(attachmentIds)), conn)

# Deletes one attachment row only while it is still pending and returns the rows removed.
def deletePending(attachmentId, conn):
    statement = delete(orderAttachmentTable).where(
        orderAttachmentTable.c.order_attachment_id == attachmentId, orderAttachmentTable.c.status == "pending",
    )
    return conn.execute(statement).rowcount

# Marks one pending attachment uploaded with the size and type storage reported.
def confirm(attachmentId, sizeBytes, contentType, actor, conn):
    statement = (
        update(orderAttachmentTable)
        .where(orderAttachmentTable.c.order_attachment_id == attachmentId, orderAttachmentTable.c.status == "pending")
        .values(status="uploaded", size_bytes=sizeBytes, content_type=contentType, confirmed_at=func.now(), updated_at=func.now(), updated_by=actor)
    )
    return conn.execute(statement).rowcount

# Returns an order's attachments in upload order.
def listForOrder(orderId, conn=None):
    query = (
        select(orderAttachmentTable)
        .where(orderAttachmentTable.c.service_order_id == orderId)
        .order_by(orderAttachmentTable.c.created_at, orderAttachmentTable.c.order_attachment_id)
    )
    return readAll(query, conn)


__all__ = ["confirm", "countByKind", "deletePending", "getAttachment", "getAttachments", "insertAttachment", "listForOrder"]

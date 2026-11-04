from sqlalchemy import insert, select
from core.db import orderCompletionTable, readOne, runUniqueWrite, userTable

UNIQUE_ORDER_CONSTRAINT = "order_completion_service_order_id_key"
COMPLETION_COLUMNS = (*orderCompletionTable.c, userTable.c.name.label("technician_name"))
COMPLETION_JOIN = orderCompletionTable.join(userTable, userTable.c.user_id == orderCompletionTable.c.technician_id)

# Inserts one completion and returns (completionId, conflict), where conflict is the given value when the order
# already has a completion; a savepoint keeps the caller's transaction usable.
def insertCompletion(values, conflict, conn):
    statement = insert(orderCompletionTable).values(**values).returning(orderCompletionTable.c.order_completion_id)
    return runUniqueWrite(statement, {UNIQUE_ORDER_CONSTRAINT: conflict}, conn)

# Returns an order's completion with the technician's name, or None.
def getCompletion(orderId, conn=None):
    query = select(*COMPLETION_COLUMNS).select_from(COMPLETION_JOIN).where(orderCompletionTable.c.service_order_id == orderId)
    return readOne(query, conn)


__all__ = ["getCompletion", "insertCompletion"]

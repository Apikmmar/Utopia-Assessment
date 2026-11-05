from sqlalchemy import Text, cast, func, select
from core.db import orderCompletionTable, orderEventTable, readAll, userTable

completion = orderCompletionTable.c
event = orderEventTable.c
POSTPONED_EVENT = "postponed"
postponedTechnicianId = event.detail["technicianId"].astext

# Returns jobs completed and the summed final amount per technician for completions in [start, end), with each
# technician's name.
def completionTotals(startUtc, endUtc, conn=None):
    query = (
        select(
            completion.technician_id, userTable.c.name,
            func.count().label("jobs_completed"), func.coalesce(func.sum(completion.final_amount), 0).label("total_amount"),
        )
        .select_from(orderCompletionTable.join(userTable, userTable.c.user_id == completion.technician_id))
        .where(completion.completed_at >= startUtc, completion.completed_at < endUtc)
        .group_by(completion.technician_id, userTable.c.name)
    )
    return readAll(query, conn)

# Returns the number of postponed events in [start, end) per technician named in the event, with each name. The id is
# compared as text, so a malformed id in one event drops that event instead of failing the query.
def postponementCounts(startUtc, endUtc, conn=None):
    query = (
        select(userTable.c.user_id.label("technician_id"), userTable.c.name, func.count().label("postponed"))
        .select_from(orderEventTable.join(userTable, cast(userTable.c.user_id, Text) == postponedTechnicianId))
        .where(event.event_type == POSTPONED_EVENT, event.created_at >= startUtc, event.created_at < endUtc)
        .group_by(userTable.c.user_id, userTable.c.name)
    )
    return readAll(query, conn)


__all__ = ["completionTotals", "postponementCounts"]

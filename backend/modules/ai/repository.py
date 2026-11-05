from sqlalchemy import func, insert, select
from sqlalchemy.dialects.postgresql import insert as upsert
from core.db import (
    llmInvocationTable, llmModelTable, orderCompletionTable, readAll, readOne, readScalar, runWrite, serviceOrderTable, serviceTypeTable,
    tokenUsageTable, userTable,
)

completion = orderCompletionTable.c
order = serviceOrderTable.c

# Returns the condition for completions inside [startUtc, endUtc).
def completedWithin(startUtc, endUtc):
    return (completion.completed_at >= startUtc) & (completion.completed_at < endUtc)

# Returns up to the limit of one technician's completions in [start, end), oldest first, each with the exact total
# count of the period in the same statement, so the total and the rows agree.
def technicianJobs(technicianId, startUtc, endUtc, limit, conn=None):
    query = (
        select(
            order.service_order_id, order.order_no, serviceTypeTable.c.service_type_name, completion.completed_at,
            func.count().over().label("total"),
        )
        .select_from(
            orderCompletionTable.join(serviceOrderTable, order.service_order_id == completion.service_order_id)
            .join(serviceTypeTable, serviceTypeTable.c.service_type_id == order.service_type_id)
        )
        .where(completion.technician_id == technicianId, completedWithin(startUtc, endUtc))
        .order_by(completion.completed_at, order.service_order_id)
        .limit(limit)
    )
    return readAll(query, conn)

# Returns up to the limit of the technicians tied for the most completions in [start, end), by name, each with the
# winning count and the exact number of tied leaders. A period without completions returns no rows.
def topTechnicians(startUtc, endUtc, limit, conn=None):
    counts = (
        select(completion.technician_id, func.count().label("jobs"))
        .where(completedWithin(startUtc, endUtc))
        .group_by(completion.technician_id)
        .cte("counts")
    )
    query = (
        select(userTable.c.user_id, userTable.c.name, counts.c.jobs, func.count().over().label("total"))
        .select_from(counts.join(userTable, userTable.c.user_id == counts.c.technician_id))
        .where(counts.c.jobs == select(func.max(counts.c.jobs)).scalar_subquery())
        .order_by(userTable.c.name, userTable.c.user_id)
        .limit(limit)
    )
    return readAll(query, conn)

# Returns how many completions fall in [start, end).
def completedCount(startUtc, endUtc, conn=None):
    return readScalar(select(func.count()).select_from(orderCompletionTable).where(completedWithin(startUtc, endUtc)), conn)

# Registers the provider's model once and returns its row, so an admin can switch it off with is_active.
def ensureModel(provider, model, conn=None):
    runWrite(upsert(llmModelTable).values(provider=provider, model=model).on_conflict_do_nothing(constraint="llm_model_provider_model_key"), conn)
    query = select(llmModelTable.c.llm_model_id, llmModelTable.c.is_active).where(llmModelTable.c.provider == provider, llmModelTable.c.model == model)
    return readOne(query, conn)

# Returns how many model calls were recorded since the instant, across every model.
def invocationsSince(startUtc, conn=None):
    return readScalar(select(func.count()).select_from(llmInvocationTable).where(llmInvocationTable.c.created_at >= startUtc), conn)

# Records one model call with its outcome and latency.
def insertInvocation(values, conn=None):
    runWrite(insert(llmInvocationTable).values(**values), conn)

# Records the tokens one model call used.
def insertTokenUsage(values, conn=None):
    runWrite(insert(tokenUsageTable).values(**values), conn)


__all__ = [
    "completedCount", "ensureModel", "insertInvocation", "insertTokenUsage", "invocationsSince", "technicianJobs", "topTechnicians",
]

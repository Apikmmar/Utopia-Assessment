from sqlalchemy import select
from core.db import readAll, readOne, serviceTypeTable

SERVICE_TYPE_COLUMNS = (
    serviceTypeTable.c.service_type_id,
    serviceTypeTable.c.service_type_code.label("code"),
    serviceTypeTable.c.service_type_name.label("name"),
)

# Returns every active service type in display order.
def listActive(conn=None):
    query = (
        select(*SERVICE_TYPE_COLUMNS)
        .where(serviceTypeTable.c.is_active.is_(True))
        .order_by(serviceTypeTable.c.sort_order, serviceTypeTable.c.service_type_name)
    )
    return readAll(query, conn)

# Returns one active service type by id, or None when it is unknown or inactive.
def findActive(serviceTypeId, conn=None):
    query = select(*SERVICE_TYPE_COLUMNS).where(
        serviceTypeTable.c.service_type_id == serviceTypeId, serviceTypeTable.c.is_active.is_(True),
    )
    return readOne(query, conn)


__all__ = ["findActive", "listActive"]

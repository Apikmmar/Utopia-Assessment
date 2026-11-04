from core.error import INVALID_SERVICE_TYPE_CODE, serviceError
from modules.service_type import repository

INVALID_SERVICE_TYPE_MESSAGE = "Choose a valid service type."
SERVICE_TYPE_FIELD = "serviceTypeId"

# Returns the active service types for any signed-in user, in display order.
def listServiceTypes(actor):
    return repository.listActive()

# Returns (serviceType, error) for the order module: the active type, or a 422 refusal naming the field.
def activeServiceType(conn, serviceTypeId):
    serviceType = repository.findActive(serviceTypeId, conn) if serviceTypeId is not None else None
    if serviceType is None:
        return None, serviceError(INVALID_SERVICE_TYPE_CODE, INVALID_SERVICE_TYPE_MESSAGE, {SERVICE_TYPE_FIELD: INVALID_SERVICE_TYPE_MESSAGE})
    return serviceType, None


__all__ = ["activeServiceType", "listServiceTypes"]

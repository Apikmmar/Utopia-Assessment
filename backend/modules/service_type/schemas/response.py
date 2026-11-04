from typing import List
from uuid import UUID
from core.schema import ResponseModel


class ServiceTypeResponse(ResponseModel):
    service_type_id: UUID
    code: str
    name: str


class ServiceTypeListResponse(ResponseModel):
    items: List[ServiceTypeResponse]


__all__ = ["ServiceTypeListResponse", "ServiceTypeResponse"]

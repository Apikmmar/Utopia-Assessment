from fastapi import APIRouter, Depends
from core.auth import AuthUser, currentUser
from modules.service_type import service
from modules.service_type.schemas.response import ServiceTypeListResponse

router = APIRouter(prefix="/service-types", tags=["service_type"])

# Lists the active service types for any signed-in user.
@router.get("", response_model=ServiceTypeListResponse)
def listServiceTypes(actor: AuthUser = Depends(currentUser)):
    return {"items": service.listServiceTypes(actor)}


__all__ = ["router"]

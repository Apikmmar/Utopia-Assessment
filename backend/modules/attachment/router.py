from uuid import UUID
from fastapi import APIRouter, Depends, Response
from core.auth import ROLE_TECHNICIAN, AuthUser, currentUser, requireRole
from core.error import raiseServiceError
from modules.attachment import service
from modules.attachment.schemas.request import UploadRequest
from modules.attachment.schemas.response import AttachmentListResponse, UploadResponse

router = APIRouter(prefix="/orders/{orderId}/attachments", tags=["attachment"])
requireTechnician = requireRole(ROLE_TECHNICIAN)

# Returns the service value, or raises the HTTP error for its refusal.
def unwrap(result):
    value, error = result
    if error:
        raiseServiceError(error)
    return value

# Records a pending file for the assigned technician's job and returns the signed URL the browser uploads it to.
@router.post("", status_code=201, response_model=UploadResponse)
def requestUpload(orderId: UUID, body: UploadRequest, actor: AuthUser = Depends(requireTechnician)):
    return unwrap(service.requestUpload(actor, orderId, body.kind, body.file_name, body.content_type, body.size_bytes))

# Removes a pending file so the technician can replace it or free its slot.
@router.delete("/{attachmentId}", status_code=204)
def deletePending(orderId: UUID, attachmentId: UUID, actor: AuthUser = Depends(requireTechnician)):
    unwrap(service.deletePending(actor, orderId, attachmentId))
    return Response(status_code=204)

# Lists an order's files with short-lived view links.
@router.get("", response_model=AttachmentListResponse)
def listAttachments(orderId: UUID, actor: AuthUser = Depends(currentUser)):
    return {"items": unwrap(service.listAttachments(actor, orderId))}


__all__ = ["router"]

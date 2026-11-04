from uuid import UUID
from fastapi import APIRouter, Depends
from core.auth import ROLE_TECHNICIAN, AuthUser, currentUser, requireRole
from core.error import raiseServiceError
from core.request_context import currentRequestId
from modules.completion import service
from modules.completion.schemas.request import SubmitCompletionRequest
from modules.completion.schemas.response import CompletionEnvelope, SubmitCompletionResponse

router = APIRouter(prefix="/orders/{orderId}/completion", tags=["completion"])
requireTechnician = requireRole(ROLE_TECHNICIAN)

# Returns the service value, or raises the HTTP error for its refusal.
def unwrap(result):
    value, error = result
    if error:
        raiseServiceError(error)
    return value

# The assigned technician records the finished job, which moves the order to job_done and queues the customer message.
@router.post("", status_code=201, response_model=SubmitCompletionResponse)
def submitCompletion(orderId: UUID, body: SubmitCompletionRequest, actor: AuthUser = Depends(requireTechnician)):
    return unwrap(service.submitCompletion(actor, orderId, body.model_dump(), currentRequestId()))

# Returns the order's completion record to anyone who may see the order.
@router.get("", response_model=CompletionEnvelope)
def getCompletion(orderId: UUID, actor: AuthUser = Depends(currentUser)):
    return unwrap(service.getCompletion(actor, orderId))


__all__ = ["router"]

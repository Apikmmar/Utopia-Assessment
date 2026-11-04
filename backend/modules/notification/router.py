from typing import Literal, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, Query
from core.auth import ROLE_ADMIN, ROLE_TECHNICIAN, AuthUser, currentUser, requireRole
from core.error import raiseServiceError
from core.pagination import PageRequest, pageQuery, paginatedResponse
from core.request_context import currentRequestId
from modules.notification import service
from modules.notification.constants import SEARCH_MAX_LENGTH
from modules.notification.schemas.response import NotificationEnvelope, NotificationListResponse

router = APIRouter(prefix="/notifications", tags=["notification"])
requireSender = requireRole(ROLE_ADMIN, ROLE_TECHNICIAN)
requireAdmin = requireRole(ROLE_ADMIN)

# Returns the service value, or raises the HTTP error for its refusal.
def unwrap(result):
    value, error = result
    if error:
        raiseServiceError(error)
    return value

# Lists notifications across orders, scoped to the user; sendable keeps only pending ones this user is to send.
@router.get("", response_model=NotificationListResponse)
def listNotifications(
    state: Optional[Literal["pending", "sent"]] = None,
    orderId: Optional[UUID] = None,
    notificationType: Optional[Literal["job_assigned", "job_done"]] = None,
    search: Optional[str] = Query(default=None, max_length=SEARCH_MAX_LENGTH),
    sendable: bool = False,
    paging: PageRequest = Depends(pageQuery),
    actor: AuthUser = Depends(currentUser),
):
    filters = {"state": state, "orderId": orderId, "notificationType": notificationType, "search": search, "sendable": sendable}
    items, total = service.listNotifications(actor, filters, paging)
    return paginatedResponse(items, total, paging)

# Records that the user opened a ready notification in WhatsApp.
@router.post("/{notificationId}/open", response_model=NotificationEnvelope)
def openNotification(notificationId: UUID, actor: AuthUser = Depends(requireSender)):
    return {"notification": unwrap(service.markOpened(actor, notificationId))}

# Queues a failed notification again, admin only.
@router.post("/{notificationId}/retry", response_model=NotificationEnvelope)
def retryNotification(notificationId: UUID, actor: AuthUser = Depends(requireAdmin)):
    return {"notification": unwrap(service.retry(actor, notificationId, currentRequestId()))}


__all__ = ["router"]

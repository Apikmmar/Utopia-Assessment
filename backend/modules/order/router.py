from typing import List, Literal, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, Query
from core.auth import ROLE_ADMIN, ROLE_MANAGER, ROLE_TECHNICIAN, AuthUser, currentUser, requireRole
from core.error import raiseServiceError
from core.pagination import PageRequest, pageQuery, paginatedResponse
from core.request_context import currentRequestId
from modules.order import service
from modules.order.constants import SEARCH_MAX_LENGTH
from modules.order.schemas.request import AssignTechnicianRequest, CreateOrderRequest, PostponeRequest, UpdateOrderRequest
from modules.order.schemas.response import OrderDetailResponse, OrderEnvelope, OrderListResponse, OrderWithNotification

router = APIRouter(prefix="/orders", tags=["order"])
requireAdmin = requireRole(ROLE_ADMIN)
requireTechnician = requireRole(ROLE_TECHNICIAN)
requireManager = requireRole(ROLE_MANAGER)
requirePostponer = requireRole(ROLE_TECHNICIAN, ROLE_ADMIN)
StatusFilter = Literal["new", "assigned", "in_progress", "job_done", "reviewed", "closed"]

# Returns the service value, or raises the HTTP error for its refusal.
def unwrap(result):
    value, error = result
    if error:
        raiseServiceError(error)
    return value

# Creates an order, optionally assigning a technician and queueing their WhatsApp notification.
@router.post("", status_code=201, response_model=OrderWithNotification)
def createOrder(body: CreateOrderRequest, actor: AuthUser = Depends(requireAdmin)):
    return unwrap(service.createOrder(actor, body.model_dump(), currentRequestId()))

# Lists orders scoped by role, with search, status, technician, and sort filters, one page at a time.
@router.get("", response_model=OrderListResponse)
def listOrders(
    search: Optional[str] = Query(default=None, max_length=SEARCH_MAX_LENGTH),
    status: Optional[List[StatusFilter]] = Query(default=None),
    technicianId: Optional[UUID] = None,
    sort: Literal["newest", "oldest"] = "newest",
    paging: PageRequest = Depends(pageQuery),
    actor: AuthUser = Depends(currentUser),
):
    filters = {"search": search, "status": status, "technicianId": technicianId, "sort": sort}
    items, total = service.listOrders(actor, filters, paging)
    return paginatedResponse(items, total, paging)

# Returns one order with its event timeline.
@router.get("/{orderId}", response_model=OrderDetailResponse)
def getOrder(orderId: UUID, actor: AuthUser = Depends(currentUser)):
    return unwrap(service.getOrder(actor, orderId))

# Edits an order's details while it is still new or assigned.
@router.patch("/{orderId}", response_model=OrderEnvelope)
def updateOrder(orderId: UUID, body: UpdateOrderRequest, actor: AuthUser = Depends(requireAdmin)):
    return unwrap(service.updateOrder(actor, orderId, body.model_dump(exclude_unset=True), currentRequestId()))

# Assigns or reassigns the technician and queues their WhatsApp notification.
@router.post("/{orderId}/assign", response_model=OrderWithNotification)
def assignTechnician(orderId: UUID, body: AssignTechnicianRequest, actor: AuthUser = Depends(requireAdmin)):
    return unwrap(service.assignTechnician(actor, orderId, body.technician_id, currentRequestId()))

# The assigned technician starts the job.
@router.post("/{orderId}/start", response_model=OrderEnvelope)
def startJob(orderId: UUID, actor: AuthUser = Depends(requireTechnician)):
    return unwrap(service.startJob(actor, orderId, currentRequestId()))

# A manager marks a finished job reviewed.
@router.post("/{orderId}/review", response_model=OrderEnvelope)
def reviewOrder(orderId: UUID, actor: AuthUser = Depends(requireManager)):
    return unwrap(service.reviewOrder(actor, orderId, currentRequestId()))

# A manager closes a reviewed order.
@router.post("/{orderId}/close", response_model=OrderEnvelope)
def closeOrder(orderId: UUID, actor: AuthUser = Depends(requireManager)):
    return unwrap(service.closeOrder(actor, orderId, currentRequestId()))

# The assigned technician or an admin records a postponed visit; the status does not change.
@router.post("/{orderId}/postpone", response_model=OrderEnvelope)
def postponeOrder(orderId: UUID, body: PostponeRequest, actor: AuthUser = Depends(requirePostponer)):
    return unwrap(service.postponeOrder(actor, orderId, body.reason_code, body.new_date, currentRequestId()))


__all__ = ["router"]

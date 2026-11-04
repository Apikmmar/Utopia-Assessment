from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID
from core.schema import ResponseModel
from modules.notification.schemas.response import NotificationResponse


class ServiceTypeRef(ResponseModel):
    service_type_id: UUID
    code: str
    name: str


class TechnicianRef(ResponseModel):
    user_id: UUID
    name: str
    phone: Optional[str]


class TechnicianListRef(ResponseModel):
    user_id: UUID
    name: str


class ActorRef(ResponseModel):
    user_id: UUID
    name: str


class OrderResponse(ResponseModel):
    order_id: UUID
    order_no: str
    customer_name: str
    customer_phone: str
    address: str
    problem_description: str
    service_type: ServiceTypeRef
    quoted_price: str
    technician: Optional[TechnicianRef]
    admin_notes: Optional[str]
    status: str
    status_changed_at: datetime
    started_at: Optional[datetime]
    job_done_at: Optional[datetime]
    reviewed_at: Optional[datetime]
    closed_at: Optional[datetime]
    created_at: datetime


class OrderListItem(ResponseModel):
    order_id: UUID
    order_no: str
    customer_name: str
    address: str
    service_type: ServiceTypeRef
    quoted_price: str
    technician: Optional[TechnicianListRef]
    status: str
    created_at: datetime


class OrderEvent(ResponseModel):
    event_type: str
    from_status: Optional[str]
    to_status: Optional[str]
    actor: ActorRef
    detail: Dict[str, Any]
    created_at: datetime


class OrderEnvelope(ResponseModel):
    order: OrderResponse


class OrderWithNotification(ResponseModel):
    order: OrderResponse
    notification: Optional[NotificationResponse]


class OrderDetailResponse(ResponseModel):
    order: OrderResponse
    events: List[OrderEvent]


class OrderListResponse(ResponseModel):
    items: List[OrderListItem]
    total: int
    page: int
    page_size: int


__all__ = [
    "OrderDetailResponse",
    "OrderEnvelope",
    "OrderEvent",
    "OrderListItem",
    "OrderListResponse",
    "OrderResponse",
    "OrderWithNotification",
]

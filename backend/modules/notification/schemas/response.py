from datetime import datetime
from typing import List, Optional
from uuid import UUID
from core.schema import ResponseModel


class OpenedByResponse(ResponseModel):
    user_id: UUID
    name: str


class NotificationResponse(ResponseModel):
    notification_id: UUID
    order_id: UUID
    order_no: str
    notification_type: str
    channel: str
    recipient_type: str
    recipient_name: str
    recipient_phone: str
    message: Optional[str]
    deep_link: Optional[str]
    status: str
    ready_at: Optional[datetime]
    opened_at: Optional[datetime]
    opened_by: Optional[OpenedByResponse]
    can_send: bool
    created_at: datetime


class NotificationEnvelope(ResponseModel):
    notification: NotificationResponse


class NotificationListResponse(ResponseModel):
    items: List[NotificationResponse]
    total: int
    page: int
    page_size: int


__all__ = ["NotificationEnvelope", "NotificationListResponse", "NotificationResponse", "OpenedByResponse"]

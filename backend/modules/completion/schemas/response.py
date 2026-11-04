from datetime import datetime
from typing import Optional
from uuid import UUID
from core.schema import ResponseModel
from modules.notification.schemas.response import NotificationResponse
from modules.order.schemas.response import ActorRef, OrderResponse


class PaymentResponse(ResponseModel):
    amount: str
    method: str
    receipt_attachment_id: Optional[UUID]


class CompletionResponse(ResponseModel):
    completion_id: UUID
    order_id: UUID
    technician: ActorRef
    work_done: str
    quoted_price: str
    extra_charges: str
    final_amount: str
    remarks: Optional[str]
    payment: Optional[PaymentResponse]
    completed_at: datetime


class CompletionEnvelope(ResponseModel):
    completion: CompletionResponse


class SubmitCompletionResponse(ResponseModel):
    completion: CompletionResponse
    order: OrderResponse
    notification: Optional[NotificationResponse]


__all__ = ["CompletionEnvelope", "CompletionResponse", "PaymentResponse", "SubmitCompletionResponse"]

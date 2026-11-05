from datetime import date
from typing import Optional, Union
from uuid import UUID
from pydantic import Field, StrictFloat, StrictInt, StrictStr
from core.schema import RequestModel
from modules.order.constants import TEXT_INPUT_MAX_LENGTH

PHONE_INPUT_MAX_LENGTH = 40
REASON_CODE_MAX_LENGTH = 40
AmountInput = Union[StrictInt, StrictFloat, StrictStr]


class CreateOrderRequest(RequestModel):
    customer_name: str = Field(max_length=TEXT_INPUT_MAX_LENGTH)
    customer_phone: str = Field(max_length=PHONE_INPUT_MAX_LENGTH)
    address: str = Field(max_length=TEXT_INPUT_MAX_LENGTH)
    problem_description: str = Field(max_length=TEXT_INPUT_MAX_LENGTH)
    service_type_id: UUID
    quoted_price: AmountInput = Field(union_mode="left_to_right")
    technician_id: Optional[UUID] = None
    admin_notes: Optional[str] = Field(default=None, max_length=TEXT_INPUT_MAX_LENGTH)


class UpdateOrderRequest(RequestModel):
    customer_name: Optional[str] = Field(default=None, max_length=TEXT_INPUT_MAX_LENGTH)
    customer_phone: Optional[str] = Field(default=None, max_length=PHONE_INPUT_MAX_LENGTH)
    address: Optional[str] = Field(default=None, max_length=TEXT_INPUT_MAX_LENGTH)
    problem_description: Optional[str] = Field(default=None, max_length=TEXT_INPUT_MAX_LENGTH)
    service_type_id: Optional[UUID] = None
    quoted_price: Optional[AmountInput] = Field(default=None, union_mode="left_to_right")
    admin_notes: Optional[str] = Field(default=None, max_length=TEXT_INPUT_MAX_LENGTH)


class AssignTechnicianRequest(RequestModel):
    technician_id: UUID


class PostponeRequest(RequestModel):
    reason_code: str = Field(max_length=REASON_CODE_MAX_LENGTH)
    new_date: Optional[date] = None


__all__ = ["AssignTechnicianRequest", "CreateOrderRequest", "PostponeRequest", "UpdateOrderRequest"]

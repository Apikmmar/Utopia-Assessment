from typing import List, Literal, Optional, Union
from uuid import UUID
from pydantic import Field, StrictFloat, StrictInt, StrictStr
from core.schema import RequestModel
from modules.completion.constants import ATTACHMENT_IDS_MAX, TEXT_INPUT_MAX_LENGTH

AmountInput = Union[StrictInt, StrictFloat, StrictStr]


class PaymentRequest(RequestModel):
    amount: AmountInput = Field(union_mode="left_to_right")
    method: Literal["cash", "card", "bank_transfer", "ewallet"]
    receipt_attachment_id: Optional[UUID] = None


class SubmitCompletionRequest(RequestModel):
    work_done: str = Field(max_length=TEXT_INPUT_MAX_LENGTH)
    extra_charges: Optional[AmountInput] = Field(default=None, union_mode="left_to_right")
    remarks: Optional[str] = Field(default=None, max_length=TEXT_INPUT_MAX_LENGTH)
    attachment_ids: List[UUID] = Field(default_factory=list, max_length=ATTACHMENT_IDS_MAX)
    payment: Optional[PaymentRequest] = None


__all__ = ["PaymentRequest", "SubmitCompletionRequest"]

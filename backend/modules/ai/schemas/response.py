from datetime import date, datetime
from typing import Annotated, Literal, Optional, Union
from uuid import UUID
from pydantic import Field
from core.schema import ResponseModel


class AiPeriod(ResponseModel):
    label: str
    start_date: date
    end_date: date


class AiTechnician(ResponseModel):
    user_id: UUID
    name: str


class AiJob(ResponseModel):
    order_id: UUID
    order_no: str
    service_type: str
    completed_at: datetime


class TechnicianJobsResult(ResponseModel):
    kind: Literal["technician_jobs"]
    technician: AiTechnician
    total: int
    items: list[AiJob]
    truncated: bool


class TopTechnicianResult(ResponseModel):
    kind: Literal["top_technician"]
    jobs_completed: int
    total: int
    items: list[AiTechnician]
    truncated: bool


class CompletedCountResult(ResponseModel):
    kind: Literal["completed_count"]
    total: int


AiResult = Annotated[Union[TechnicianJobsResult, TopTechnicianResult, CompletedCountResult], Field(discriminator="kind")]


class AiQueryResponse(ResponseModel):
    status: Literal["answered", "unsupported", "clarification_required"]
    answer: str
    summary_source: Optional[Literal["ai", "template"]]
    notice: Optional[str]
    period: Optional[AiPeriod]
    result: Optional[AiResult]


__all__ = [
    "AiJob", "AiPeriod", "AiQueryResponse", "AiResult", "AiTechnician", "CompletedCountResult", "TechnicianJobsResult", "TopTechnicianResult",
]

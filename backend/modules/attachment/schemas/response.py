from typing import List, Optional
from uuid import UUID
from core.schema import ResponseModel


class AttachmentResponse(ResponseModel):
    attachment_id: UUID
    kind: str
    file_name: str
    content_type: str
    size_bytes: int
    status: str
    view_url: Optional[str]


class UploadResponse(ResponseModel):
    attachment: AttachmentResponse
    upload_url: str


class AttachmentListResponse(ResponseModel):
    items: List[AttachmentResponse]


__all__ = ["AttachmentListResponse", "AttachmentResponse", "UploadResponse"]

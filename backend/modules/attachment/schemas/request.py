from typing import Literal
from pydantic import Field
from core.schema import RequestModel
from modules.attachment.constants import FILE_NAME_MAX_LENGTH

CONTENT_TYPE_MAX_LENGTH = 100
MAX_DECLARED_BYTES = 1024 * 1024 * 1024


class UploadRequest(RequestModel):
    kind: Literal["completion", "receipt"]
    file_name: str = Field(min_length=1, max_length=FILE_NAME_MAX_LENGTH)
    content_type: str = Field(min_length=1, max_length=CONTENT_TYPE_MAX_LENGTH)
    size_bytes: int = Field(ge=1, le=MAX_DECLARED_BYTES)


__all__ = ["UploadRequest"]

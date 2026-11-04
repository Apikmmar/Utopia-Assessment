from datetime import datetime
from typing import List, Optional
from uuid import UUID
from core.schema import ResponseModel


class UserResponse(ResponseModel):
    user_id: UUID
    name: str
    email: str
    phone: Optional[str]
    age: Optional[int]
    role_code: str
    created_at: datetime


class UserListResponse(ResponseModel):
    items: List[UserResponse]
    total: int
    page: int
    page_size: int


__all__ = ["UserListResponse", "UserResponse"]

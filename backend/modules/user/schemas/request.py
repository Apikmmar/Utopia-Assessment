from typing import Optional
from pydantic import Field
from core.schema import RequestModel

NAME_INPUT_MAX_LENGTH = 200
EMAIL_INPUT_MAX_LENGTH = 320
PHONE_INPUT_MAX_LENGTH = 40
ROLE_CODE_INPUT_MAX_LENGTH = 30
PASSWORD_INPUT_MAX_LENGTH = 1024


class CreateUserRequest(RequestModel):
    name: str = Field(max_length=NAME_INPUT_MAX_LENGTH)
    email: str = Field(max_length=EMAIL_INPUT_MAX_LENGTH)
    phone: Optional[str] = Field(default=None, max_length=PHONE_INPUT_MAX_LENGTH)
    age: Optional[int] = None
    role_code: str = Field(max_length=ROLE_CODE_INPUT_MAX_LENGTH)
    password: str = Field(max_length=PASSWORD_INPUT_MAX_LENGTH)


class UpdateUserRequest(RequestModel):
    name: Optional[str] = Field(default=None, max_length=NAME_INPUT_MAX_LENGTH)
    phone: Optional[str] = Field(default=None, max_length=PHONE_INPUT_MAX_LENGTH)
    age: Optional[int] = None
    role_code: Optional[str] = Field(default=None, max_length=ROLE_CODE_INPUT_MAX_LENGTH)


__all__ = ["CreateUserRequest", "UpdateUserRequest"]

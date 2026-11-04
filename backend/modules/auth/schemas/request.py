from pydantic import Field, field_validator
from core.schema import RequestModel
from core.useraccount import isValidEmail, normalizeEmail

FIELD_MAX_LENGTH = 1024
INVALID_EMAIL_MESSAGE = "Enter a valid email address."

# Returns the normalized email or raises when it is not a valid address.
def checkedEmail(value):
    email = normalizeEmail(value)
    if not isValidEmail(email):
        raise ValueError(INVALID_EMAIL_MESSAGE)
    return email


class LoginRequest(RequestModel):
    email: str = Field(max_length=FIELD_MAX_LENGTH)
    password: str = Field(min_length=1, max_length=FIELD_MAX_LENGTH)

    # Normalizes and validates the email field.
    @field_validator("email")
    @classmethod
    def validateEmail(cls, value):
        return checkedEmail(value)


class ResetRequest(RequestModel):
    email: str = Field(max_length=FIELD_MAX_LENGTH)
    new_password: str = Field(max_length=FIELD_MAX_LENGTH)

    # Normalizes and validates the email field.
    @field_validator("email")
    @classmethod
    def validateEmail(cls, value):
        return checkedEmail(value)


__all__ = ["LoginRequest", "ResetRequest", "checkedEmail"]

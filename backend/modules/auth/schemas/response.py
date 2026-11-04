from uuid import UUID
from core.schema import ResponseModel


class AuthUserResponse(ResponseModel):
    user_id: UUID
    name: str
    email: str
    role_code: str


class SessionResponse(ResponseModel):
    user: AuthUserResponse


class MessageResponse(ResponseModel):
    message: str

# Maps the authenticated user value to its public response shape.
def toAuthUserResponse(user):
    return AuthUserResponse(user_id=user.userId, name=user.name, email=user.email, role_code=user.roleCode)


__all__ = ["AuthUserResponse", "MessageResponse", "SessionResponse", "toAuthUserResponse"]

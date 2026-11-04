from ipaddress import ip_address
from fastapi import APIRouter, Depends, Request, Response
from core import config
from core.auth import AuthUser, currentUser, sessionToken
from core.error import raiseServiceError
from modules.auth import service
from modules.auth.schemas.request import LoginRequest, ResetRequest
from modules.auth.schemas.response import MessageResponse, SessionResponse, toAuthUserResponse

router = APIRouter(prefix="/auth", tags=["auth"])

USER_AGENT_MAX_LENGTH = 300
SECONDS_PER_HOUR = 3600

# Sets the session cookie with the fixed security attributes.
def setSessionCookie(response, token):
    response.set_cookie(
        config.authCookieName(), token, max_age=config.authSessionHours() * SECONDS_PER_HOUR, path="/",
        httponly=True, secure=config.authCookieSecure(), samesite="lax",
    )

# Expires the session cookie in the browser with the same attributes it was set with.
def clearSessionCookie(response):
    response.delete_cookie(config.authCookieName(), path="/", httponly=True, secure=config.authCookieSecure(), samesite="lax")

# Returns the socket peer address when it parses as an IP address, ignoring forwarded headers.
def readClientAddress(request):
    if request.client is None:
        return None
    try:
        return str(ip_address(request.client.host))
    except ValueError:
        return None

# Returns the caller's user agent, truncated to what the column holds.
def readUserAgent(request):
    agent = request.headers.get("user-agent")
    return agent[:USER_AGENT_MAX_LENGTH] if agent else None

# Verifies credentials, opens a session, and sets the session cookie.
@router.post("/login", response_model=SessionResponse)
def login(body: LoginRequest, request: Request, response: Response):
    result, error = service.login(body.email, body.password, readClientAddress(request), readUserAgent(request))
    if error:
        raiseServiceError(error)
    setSessionCookie(response, result.token)
    return SessionResponse(user=toAuthUserResponse(result.user))

# Revokes the current session and clears the cookie.
@router.post("/logout", status_code=204)
def logout(request: Request, user: AuthUser = Depends(currentUser)):
    service.logout(sessionToken(request))
    response = Response(status_code=204)
    clearSessionCookie(response)
    return response

# Returns the authenticated user.
@router.get("/me", response_model=SessionResponse)
def me(user: AuthUser = Depends(currentUser)):
    return SessionResponse(user=toAuthUserResponse(user))

# Sets a new password for the account with this email and always answers the same way.
@router.post("/password/reset", response_model=MessageResponse)
def resetPassword(body: ResetRequest):
    done, error = service.resetPassword(body.email, body.new_password)
    if error:
        raiseServiceError(error)
    return MessageResponse(message=service.RESET_DONE_MESSAGE)


__all__ = ["router"]

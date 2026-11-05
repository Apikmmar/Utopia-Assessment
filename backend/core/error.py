from fastapi import HTTPException
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException
from core import config
from core.db import DatabaseError
from core.logger import getLogger
from core.storage import StorageUnavailable
from core.request_context import REQUEST_ID_HEADER, bindRequestId, resetRequestId

log = getLogger(__name__)

VALIDATION_FAILED_CODE = "VALIDATION_FAILED"
INVALID_CREDENTIALS_CODE = "INVALID_CREDENTIALS"
NOT_AUTHENTICATED_CODE = "NOT_AUTHENTICATED"
FORBIDDEN_CODE = "FORBIDDEN"
BAD_ORIGIN_CODE = "BAD_ORIGIN"
WEAK_PASSWORD_CODE = "WEAK_PASSWORD"
EMAIL_TAKEN_CODE = "EMAIL_TAKEN"
SELF_DEMOTE_CODE = "SELF_DEMOTE"
USER_NOT_FOUND_CODE = "USER_NOT_FOUND"
INVALID_ROLE_CODE = "INVALID_ROLE"
NOT_FOUND_CODE = "NOT_FOUND"
METHOD_NOT_ALLOWED_CODE = "METHOD_NOT_ALLOWED"
SERVICE_UNAVAILABLE_CODE = "SERVICE_UNAVAILABLE"
INTERNAL_ERROR_CODE = "INTERNAL_ERROR"
ORDER_NOT_FOUND_CODE = "ORDER_NOT_FOUND"
INVALID_TRANSITION_CODE = "INVALID_TRANSITION"
ORDER_LOCKED_CODE = "ORDER_LOCKED"
INVALID_SERVICE_TYPE_CODE = "INVALID_SERVICE_TYPE"
INVALID_TECHNICIAN_CODE = "INVALID_TECHNICIAN"
COMPLETION_EXISTS_CODE = "COMPLETION_EXISTS"
COMPLETION_NOT_FOUND_CODE = "COMPLETION_NOT_FOUND"
ATTACHMENT_LIMIT_CODE = "ATTACHMENT_LIMIT"
ATTACHMENT_INVALID_CODE = "ATTACHMENT_INVALID"
ATTACHMENT_NOT_UPLOADED_CODE = "ATTACHMENT_NOT_UPLOADED"
ATTACHMENT_NOT_FOUND_CODE = "ATTACHMENT_NOT_FOUND"
ATTACHMENT_LOCKED_CODE = "ATTACHMENT_LOCKED"
STORAGE_UNAVAILABLE_CODE = "STORAGE_UNAVAILABLE"
NOTIFICATION_NOT_FOUND_CODE = "NOTIFICATION_NOT_FOUND"
NOTIFICATION_NOT_READY_CODE = "NOTIFICATION_NOT_READY"
NOTIFICATION_NOT_FAILED_CODE = "NOTIFICATION_NOT_FAILED"
INVALID_PERIOD_CODE = "INVALID_PERIOD"

STATUS_BY_CODE = {
    VALIDATION_FAILED_CODE: 422,
    INVALID_CREDENTIALS_CODE: 401,
    NOT_AUTHENTICATED_CODE: 401,
    FORBIDDEN_CODE: 403,
    BAD_ORIGIN_CODE: 403,
    WEAK_PASSWORD_CODE: 422,
    EMAIL_TAKEN_CODE: 409,
    SELF_DEMOTE_CODE: 409,
    USER_NOT_FOUND_CODE: 404,
    INVALID_ROLE_CODE: 422,
    NOT_FOUND_CODE: 404,
    METHOD_NOT_ALLOWED_CODE: 405,
    SERVICE_UNAVAILABLE_CODE: 503,
    INTERNAL_ERROR_CODE: 500,
    ORDER_NOT_FOUND_CODE: 404,
    INVALID_TRANSITION_CODE: 409,
    ORDER_LOCKED_CODE: 409,
    INVALID_SERVICE_TYPE_CODE: 422,
    INVALID_TECHNICIAN_CODE: 422,
    COMPLETION_EXISTS_CODE: 409,
    COMPLETION_NOT_FOUND_CODE: 404,
    ATTACHMENT_LIMIT_CODE: 409,
    ATTACHMENT_INVALID_CODE: 422,
    ATTACHMENT_NOT_UPLOADED_CODE: 422,
    ATTACHMENT_NOT_FOUND_CODE: 404,
    ATTACHMENT_LOCKED_CODE: 409,
    STORAGE_UNAVAILABLE_CODE: 503,
    NOTIFICATION_NOT_FOUND_CODE: 404,
    NOTIFICATION_NOT_READY_CODE: 409,
    NOTIFICATION_NOT_FAILED_CODE: 409,
    INVALID_PERIOD_CODE: 422,
}
CODE_BY_STATUS = {404: NOT_FOUND_CODE, 405: METHOD_NOT_ALLOWED_CODE}
DEFAULT_ERROR_STATUS = 400

VALIDATION_FAILED_MESSAGE = "Request validation failed."
SERVICE_UNAVAILABLE_MESSAGE = "Service temporarily unavailable."
STORAGE_UNAVAILABLE_MESSAGE = "File storage is temporarily unavailable."
INTERNAL_ERROR_MESSAGE = "Internal server error."


class ApiError(HTTPException):
    # Builds the HTTP error with its stable machine code and an optional field-to-message map.
    def __init__(self, statusCode, code, detail, fields=None, headers=None):
        super().__init__(status_code=statusCode, detail=detail, headers=headers)
        self.code = code
        self.fields = fields

# Returns the shared error body: the human detail, the machine code, and the fields map when present.
def errorBody(detail, code, fields=None):
    body = {"detail": detail, "code": code}
    if fields:
        body["fields"] = fields
    return body

# Returns a refusal a service hands back instead of raising: its code, message, and optional fields.
def serviceError(code, message, fields=None):
    return {"code": code, "message": message, "fields": fields}

# Returns the HTTP status one machine code answers with.
def statusForCode(code):
    return STATUS_BY_CODE.get(code, DEFAULT_ERROR_STATUS)

# Raises the HTTP error for a service refusal, so no router keeps its own code-to-status table.
def raiseServiceError(error, headers=None):
    raise ApiError(statusForCode(error["code"]), error["code"], error["message"], error.get("fields"), headers)

# Returns the request id the request id middleware stored on the scope, or None.
def scopeRequestId(request):
    return request.scope.get("state", {}).get("requestId")

# Answers an ApiError with its code, detail, and fields.
async def apiErrorHandler(request, error):
    return JSONResponse(errorBody(error.detail, error.code, error.fields), status_code=error.status_code, headers=error.headers)

# Answers a framework HTTP error, such as an unknown route, with the shared body.
async def httpErrorHandler(request, error):
    code = CODE_BY_STATUS.get(error.status_code, f"HTTP_{error.status_code}")
    return JSONResponse(errorBody(str(error.detail), code), status_code=error.status_code, headers=getattr(error, "headers", None))

# Returns the camelCase field name a validation error points at, without its location prefix.
def fieldName(location):
    parts = [str(part) for part in location]
    if parts and parts[0] in ("body", "query", "path", "header", "cookie"):
        parts = parts[1:]
    return ".".join(parts) or "body"

# Answers request validation failures with 422 and a field-to-message map that never echoes input.
async def validationErrorHandler(request, error):
    fields = {}
    for item in error.errors():
        fields.setdefault(fieldName(item["loc"]), item["msg"])
    return JSONResponse(errorBody(VALIDATION_FAILED_MESSAGE, VALIDATION_FAILED_CODE, fields), status_code=422)

# Answers a database failure with 503 and no detail.
async def databaseErrorHandler(request, error):
    log.error("database_unavailable error_type=%s", type(error).__name__)
    return JSONResponse(errorBody(SERVICE_UNAVAILABLE_MESSAGE, SERVICE_UNAVAILABLE_CODE), status_code=503)

# Answers a storage failure or missing storage settings with 503 and no detail.
async def storageErrorHandler(request, error):
    log.error("storage_unavailable reason=%s", error.reason)
    return JSONResponse(errorBody(STORAGE_UNAVAILABLE_MESSAGE, STORAGE_UNAVAILABLE_CODE), status_code=503)

# Answers anything unhandled with 500 and the request id as correlation id, logging the exception.
async def unhandledErrorHandler(request, error):
    correlationId = scopeRequestId(request)
    token = bindRequestId(correlationId)
    try:
        route = getattr(request.scope.get("route"), "path", None)
        log.error("unhandled_exception method=%s route=%s error_type=%s", request.method, route, type(error).__name__, exc_info=error)
    finally:
        resetRequestId(token)
    body = {**errorBody(INTERNAL_ERROR_MESSAGE, INTERNAL_ERROR_CODE), "correlationId": correlationId}
    response = JSONResponse(body, status_code=500)
    if correlationId:
        response.headers[REQUEST_ID_HEADER] = correlationId
    allowed = config.allowedOrigin()
    if request.headers.get("origin") == allowed:
        response.headers["Access-Control-Allow-Origin"] = allowed
        response.headers["Access-Control-Allow-Credentials"] = "true"
    return response

# Registers every shared error handler on the application.
def registerErrorHandlers(app):
    app.add_exception_handler(ApiError, apiErrorHandler)
    app.add_exception_handler(StarletteHTTPException, httpErrorHandler)
    app.add_exception_handler(RequestValidationError, validationErrorHandler)
    app.add_exception_handler(DatabaseError, databaseErrorHandler)
    app.add_exception_handler(StorageUnavailable, storageErrorHandler)
    app.add_exception_handler(Exception, unhandledErrorHandler)


__all__ = [
    "ATTACHMENT_INVALID_CODE",
    "ATTACHMENT_LIMIT_CODE",
    "ATTACHMENT_LOCKED_CODE",
    "ATTACHMENT_NOT_FOUND_CODE",
    "ATTACHMENT_NOT_UPLOADED_CODE",
    "BAD_ORIGIN_CODE",
    "COMPLETION_EXISTS_CODE",
    "COMPLETION_NOT_FOUND_CODE",
    "DEFAULT_ERROR_STATUS",
    "EMAIL_TAKEN_CODE",
    "FORBIDDEN_CODE",
    "INTERNAL_ERROR_CODE",
    "INVALID_CREDENTIALS_CODE",
    "INVALID_PERIOD_CODE",
    "INVALID_ROLE_CODE",
    "INVALID_SERVICE_TYPE_CODE",
    "INVALID_TECHNICIAN_CODE",
    "INVALID_TRANSITION_CODE",
    "METHOD_NOT_ALLOWED_CODE",
    "NOTIFICATION_NOT_FAILED_CODE",
    "NOTIFICATION_NOT_FOUND_CODE",
    "NOTIFICATION_NOT_READY_CODE",
    "NOT_AUTHENTICATED_CODE",
    "NOT_FOUND_CODE",
    "ORDER_LOCKED_CODE",
    "ORDER_NOT_FOUND_CODE",
    "SELF_DEMOTE_CODE",
    "SERVICE_UNAVAILABLE_CODE",
    "STATUS_BY_CODE",
    "STORAGE_UNAVAILABLE_CODE",
    "USER_NOT_FOUND_CODE",
    "VALIDATION_FAILED_CODE",
    "WEAK_PASSWORD_CODE",
    "ApiError",
    "errorBody",
    "raiseServiceError",
    "registerErrorHandlers",
    "serviceError",
    "statusForCode",
]

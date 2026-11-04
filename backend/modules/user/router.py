from typing import Optional
from uuid import UUID
from fastapi import APIRouter, Depends, Query
from core.auth import ROLE_ADMIN, AuthUser, requireRole
from core.error import raiseServiceError
from core.pagination import PageRequest, pageQuery, paginatedResponse
from modules.user import service
from modules.user.constants import ROLE_CODE_MAX_LENGTH, SEARCH_MAX_LENGTH
from modules.user.schemas.request import CreateUserRequest, UpdateUserRequest
from modules.user.schemas.response import UserListResponse, UserResponse

router = APIRouter(prefix="/users", tags=["user"])
requireAdmin = requireRole(ROLE_ADMIN)

# Returns the service value, or raises the HTTP error for its refusal.
def unwrap(result):
    value, error = result
    if error:
        raiseServiceError(error)
    return value

# Creates a user as the acting admin.
@router.post("", status_code=201, response_model=UserResponse)
def createUser(body: CreateUserRequest, actor: AuthUser = Depends(requireAdmin)):
    return unwrap(service.createUser(actor, body.name, body.email, body.phone, body.age, body.role_code, body.password))

# Lists users with an optional search and role filter, one page at a time.
@router.get("", response_model=UserListResponse)
def listUsers(
    search: Optional[str] = Query(default=None, max_length=SEARCH_MAX_LENGTH),
    roleCode: Optional[str] = Query(default=None, max_length=ROLE_CODE_MAX_LENGTH),
    paging: PageRequest = Depends(pageQuery),
    actor: AuthUser = Depends(requireAdmin),
):
    rows, total = service.listUsers(actor, search, roleCode, paging)
    return paginatedResponse(rows, total, paging)

# Returns one user or 404 USER_NOT_FOUND.
@router.get("/{userId}", response_model=UserResponse)
def getUser(userId: UUID, actor: AuthUser = Depends(requireAdmin)):
    return unwrap(service.getUser(actor, userId))

# Edits a user's name, phone, age, or role.
@router.patch("/{userId}", response_model=UserResponse)
def updateUser(userId: UUID, body: UpdateUserRequest, actor: AuthUser = Depends(requireAdmin)):
    return unwrap(service.updateUser(actor, userId, body.model_dump(exclude_unset=True)))


__all__ = ["router"]

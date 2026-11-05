from datetime import date
from typing import Optional
from fastapi import APIRouter, Depends, Query
from core.auth import ROLE_ADMIN, ROLE_MANAGER, AuthUser, requireRole
from core.error import raiseServiceError
from modules.kpi import service
from modules.kpi.schemas.response import DashboardResponse

router = APIRouter(prefix="/kpi", tags=["kpi"])
requireReporter = requireRole(ROLE_ADMIN, ROLE_MANAGER)

# Returns the service value, or raises the HTTP error for its refusal.
def unwrap(result):
    value, error = result
    if error:
        raiseServiceError(error)
    return value

# Returns team totals and the technician leaderboard for the business week containing the date, this week by default.
@router.get("/dashboard", response_model=DashboardResponse)
def dashboard(anchorDate: Optional[date] = Query(default=None, alias="date"), actor: AuthUser = Depends(requireReporter)):
    return unwrap(service.teamDashboard(actor, anchorDate))


__all__ = ["router"]

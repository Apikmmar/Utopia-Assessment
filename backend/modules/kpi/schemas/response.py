from datetime import date
from uuid import UUID
from core.schema import ResponseModel


class KpiWeek(ResponseModel):
    label: str
    start_date: date
    end_date: date
    is_current: bool


class KpiTeam(ResponseModel):
    jobs_completed: int
    total_amount: str
    postponed: int


class KpiTechnician(ResponseModel):
    user_id: UUID
    name: str


class LeaderboardRow(ResponseModel):
    rank: int
    technician: KpiTechnician
    jobs_completed: int
    total_amount: str
    postponed: int


class DashboardResponse(ResponseModel):
    week: KpiWeek
    team: KpiTeam
    leaderboard: list[LeaderboardRow]


__all__ = ["DashboardResponse", "KpiTeam", "KpiTechnician", "KpiWeek", "LeaderboardRow"]

from decimal import Decimal
from core.auth import ROLE_ADMIN, ROLE_MANAGER
from core.businesstime import businessToday
from core.db import connection
from core.error import FORBIDDEN_CODE, INVALID_PERIOD_CODE, serviceError
from core.money import formatAmount
from modules.kpi import repository
from modules.kpi.constants import INVALID_PERIOD_MESSAGE, NOT_ALLOWED_MESSAGE
from modules.kpi.period import resolveWeek
from modules.user import service as userService

NOT_ALLOWED = serviceError(FORBIDDEN_CODE, NOT_ALLOWED_MESSAGE)
INVALID_PERIOD = serviceError(INVALID_PERIOD_CODE, INVALID_PERIOD_MESSAGE, {"date": INVALID_PERIOD_MESSAGE})
WEEK_FIELDS = ("label", "start_date", "end_date", "is_current")

# Returns one empty leaderboard entry for a technician.
def emptyRow(userId, name):
    return {"technician": {"user_id": userId, "name": name}, "jobs_completed": 0, "total_amount": Decimal(0), "postponed": 0}

# Merges the technician list with the per-technician aggregates into one entry per person, so technicians with no
# work show zeros and people credited with work who are no longer technicians still appear.
def mergeRows(technicians, completions, postponements):
    rows = {}
    for technician in technicians:
        rows[technician["user_id"]] = emptyRow(technician["user_id"], technician["name"])
    for item in completions:
        row = rows.setdefault(item["technician_id"], emptyRow(item["technician_id"], item["name"]))
        row["jobs_completed"] = item["jobs_completed"]
        row["total_amount"] = Decimal(item["total_amount"])
    for item in postponements:
        row = rows.setdefault(item["technician_id"], emptyRow(item["technician_id"], item["name"]))
        row["postponed"] = item["postponed"]
    return list(rows.values())

# Returns the sort key: most jobs, then highest amount, then name, then id so the order is stable.
def rankKey(row):
    return (-row["jobs_completed"], -row["total_amount"], row["technician"]["name"].lower(), str(row["technician"]["user_id"]))

# Sorts the rows and numbers them so equal jobs and amounts share a rank and the next rank skips ("1, 1, 3").
def rankRows(rows):
    ranked = []
    for index, row in enumerate(sorted(rows, key=rankKey)):
        previous = ranked[-1] if ranked else None
        tied = previous is not None and (previous["jobs_completed"], previous["total_amount"]) == (row["jobs_completed"], row["total_amount"])
        ranked.append({**row, "rank": previous["rank"] if tied else index + 1})
    return ranked

# Returns the team totals over every leaderboard row.
def teamTotals(rows):
    return {
        "jobs_completed": sum(row["jobs_completed"] for row in rows),
        "total_amount": formatAmount(sum((row["total_amount"] for row in rows), Decimal(0))),
        "postponed": sum(row["postponed"] for row in rows),
    }

# Returns ({week, team, leaderboard}, error) for the business week containing the anchor date, for admins and
# managers only.
def teamDashboard(actor, anchorDate, today=None):
    if actor.roleCode not in (ROLE_ADMIN, ROLE_MANAGER):
        return None, NOT_ALLOWED
    week = resolveWeek(anchorDate, today or businessToday())
    if week is None:
        return None, INVALID_PERIOD
    with connection() as conn:
        technicians = userService.listTechnicians(conn)
        completions = repository.completionTotals(week["start_utc"], week["end_utc"], conn)
        postponements = repository.postponementCounts(week["start_utc"], week["end_utc"], conn)
    rows = rankRows(mergeRows(technicians, completions, postponements))
    leaderboard = [{**row, "total_amount": formatAmount(row["total_amount"])} for row in rows]
    return {"week": {key: week[key] for key in WEEK_FIELDS}, "team": teamTotals(rows), "leaderboard": leaderboard}, None


__all__ = ["INVALID_PERIOD", "NOT_ALLOWED", "mergeRows", "rankRows", "teamDashboard", "teamTotals"]

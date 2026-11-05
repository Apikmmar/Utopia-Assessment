import uuid
from datetime import date, datetime, timezone
from decimal import Decimal
import pytest
from core.auth import AuthUser
from modules.kpi import service
from modules.kpi.period import resolveWeek

TODAY = date(2026, 11, 5)
ALI = uuid.uuid4()
BALA = uuid.uuid4()
CHONG = uuid.uuid4()
FORMER = uuid.uuid4()

# Returns a leaderboard row with the given name and figures.
def row(userId, name, jobs, amount, postponed=0):
    return {"technician": {"user_id": userId, "name": name}, "jobs_completed": jobs, "total_amount": Decimal(amount), "postponed": postponed}

# A Monday, a Thursday, and a Sunday all resolve to the same Monday-to-Sunday week, bounded at Kuala Lumpur midnight
# (16:00 UTC the day before).
@pytest.mark.parametrize("anchor", [date(2026, 11, 2), date(2026, 11, 5), date(2026, 11, 8)])
def testWeekBoundsInKualaLumpur(anchor):
    week = resolveWeek(anchor, TODAY)
    assert (week["start_date"], week["end_date"], week["label"], week["is_current"]) == (date(2026, 11, 2), date(2026, 11, 8), "2 to 8 Nov 2026", True)
    assert week["start_utc"] == datetime(2026, 11, 1, 16, 0, tzinfo=timezone.utc)
    assert week["end_utc"] == datetime(2026, 11, 8, 16, 0, tzinfo=timezone.utc)

# No anchor means the current week; a past week is not current.
def testDefaultAndPastWeek():
    assert resolveWeek(None, TODAY)["start_date"] == date(2026, 11, 2)
    past = resolveWeek(date(2026, 10, 28), TODAY)
    assert (past["start_date"], past["label"], past["is_current"]) == (date(2026, 10, 26), "26 Oct to 1 Nov 2026", False)

# A week across the new year keeps both years in its label.
def testWeekAcrossNewYear():
    week = resolveWeek(date(2026, 1, 1), TODAY)
    assert (week["start_date"], week["end_date"], week["label"]) == (date(2025, 12, 29), date(2026, 1, 4), "29 Dec 2025 to 4 Jan 2026")

# Anchors before 2020 and in a future week are refused; a later day of the current week is allowed.
def testAnchorLimits():
    assert resolveWeek(date(2019, 12, 31), TODAY) is None
    assert resolveWeek(date(2026, 11, 9), TODAY) is None
    assert resolveWeek(date(2026, 11, 8), TODAY) is not None
    assert resolveWeek(date(2020, 1, 1), TODAY) is not None

# Equal jobs and amounts share a rank and the next rank skips; ties on jobs alone are broken by the amount.
def testRankingWithTies():
    ranked = service.rankRows([
        row(CHONG, "Chong", 2, "100.00"), row(ALI, "Ali", 3, "300.00"), row(BALA, "Bala", 3, "300.00"), row(FORMER, "Dan", 3, "100.00"),
    ])
    assert [(item["technician"]["name"], item["rank"]) for item in ranked] == [("Ali", 1), ("Bala", 1), ("Dan", 3), ("Chong", 4)]

# Technicians with no rows get zeros, and someone credited with work who is no longer a technician still appears.
def testMergeKeepsZeroRowsAndFormerTechnicians():
    rows = service.mergeRows(
        [{"user_id": ALI, "name": "Ali"}, {"user_id": BALA, "name": "Bala"}],
        [{"technician_id": ALI, "name": "Ali", "jobs_completed": 2, "total_amount": Decimal("250.50")},
         {"technician_id": FORMER, "name": "Former", "jobs_completed": 1, "total_amount": Decimal("80.00")}],
        [{"technician_id": BALA, "name": "Bala", "postponed": 2}],
    )
    byName = {item["technician"]["name"]: (item["jobs_completed"], item["total_amount"], item["postponed"]) for item in rows}
    assert byName == {"Ali": (2, Decimal("250.50"), 0), "Bala": (0, Decimal(0), 2), "Former": (1, Decimal("80.00"), 0)}
    assert service.teamTotals(rows) == {"jobs_completed": 3, "total_amount": "330.50", "postponed": 2}

# A technician is refused before any database work.
def testTechnicianRefused():
    technician = AuthUser(userId=ALI, name="Ali", email="ali@example.com", roleCode="technician")
    assert service.teamDashboard(technician, None, TODAY)[1]["code"] == "FORBIDDEN"

from datetime import timedelta
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text
from core.businesstime import businessToday
from tests.order_support import insertOrder

EMAILS = {
    "admin": "admin.kpi.api@example.com", "manager": "manager.kpi.api@example.com",
    "techA": "tom.kpi.api@example.com", "techB": "bala.kpi.api@example.com",
}
INSERT_COMPLETION = (
    "INSERT INTO order_completion (service_order_id, technician_id, work_done, quoted_price, extra_charges, final_amount) "
    "VALUES (:orderId, :technicianId, 'Done', 150, 20.5, 170.5)"
)

# Users for every role.
@pytest.fixture
def world(appDb, seedUser):
    return {
        "admin": seedUser(EMAILS["admin"], "admin", name="Ada Admin"),
        "manager": seedUser(EMAILS["manager"], "manager", name="Max Manager"),
        "techA": seedUser(EMAILS["techA"], "technician", name="Tom Tech", phone="60111111111"),
        "techB": seedUser(EMAILS["techB"], "technician", name="Bala Tech", phone="60122222222"),
    }

# Returns a logged-in client for each role.
@pytest.fixture
def clients(world, loggedIn):
    return {role: loggedIn(email) for role, email in EMAILS.items()}

# Admins and managers get the dashboard; technicians are refused and anonymous is 401.
def testAccessPerRole(world, clients, app):
    assert clients["admin"].get("/kpi/dashboard").status_code == 200
    assert clients["manager"].get("/kpi/dashboard").status_code == 200
    assert clients["techA"].get("/kpi/dashboard").json()["code"] == "FORBIDDEN"
    assert TestClient(app).get("/kpi/dashboard").status_code == 401

# An empty week lists every technician with zeros, and amounts are two-decimal strings.
def testEmptyWeekListsEveryTechnician(world, clients):
    body = clients["manager"].get("/kpi/dashboard").json()
    assert body["week"]["isCurrent"] is True
    assert body["team"] == {"jobsCompleted": 0, "totalAmount": "0.00", "postponed": 0}
    assert [(row["rank"], row["technician"]["name"], row["jobsCompleted"], row["totalAmount"]) for row in body["leaderboard"]] == [
        (1, "Bala Tech", 0, "0.00"), (1, "Tom Tech", 0, "0.00"),
    ]

# A completion now counts in the current week for its technician, and not in last week.
def testCompletionCountsThisWeek(appDb, world, clients):
    orderId, _ = insertOrder(appDb, world["admin"], world["techA"], status="job_done")
    with appDb.begin() as conn:
        conn.execute(text(INSERT_COMPLETION), {"orderId": orderId, "technicianId": world["techA"]})
    body = clients["admin"].get("/kpi/dashboard").json()
    assert body["leaderboard"][0] == {
        "rank": 1, "technician": {"userId": str(world["techA"]), "name": "Tom Tech"}, "jobsCompleted": 1, "totalAmount": "170.50", "postponed": 0,
    }
    lastWeek = (businessToday() - timedelta(days=7)).isoformat()
    previous = clients["admin"].get("/kpi/dashboard", params={"date": lastWeek}).json()
    assert previous["team"]["jobsCompleted"] == 0 and previous["week"]["isCurrent"] is False

# Dates before 2020 or in a future week are INVALID_PERIOD; a malformed date fails validation.
def testInvalidDates(world, clients):
    nextWeek = (businessToday() + timedelta(days=7)).isoformat()
    for value in ("2019-12-31", nextWeek):
        response = clients["manager"].get("/kpi/dashboard", params={"date": value})
        assert (response.status_code, response.json()["code"]) == (422, "INVALID_PERIOD")
    response = clients["manager"].get("/kpi/dashboard", params={"date": "last-week"})
    assert (response.status_code, response.json()["code"]) == (422, "VALIDATION_FAILED")

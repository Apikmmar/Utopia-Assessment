from datetime import timedelta
import pytest
from fastapi.testclient import TestClient
from core.businesstime import businessToday
from tests.order_support import insertOrder
from tests.support import MISSING_ID, STATE_HEADERS

EMAILS = {
    "admin": "admin.postpone@example.com", "manager": "manager.postpone@example.com",
    "techA": "tom.postpone@example.com", "techB": "bala.postpone@example.com",
}

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

# Inserts one order for technician A in the given status and returns its id.
def orderIn(appDb, world, status):
    return str(insertOrder(appDb, world["admin"], world["techA"], status=status)[0])

# Postpones the order as the client and returns the response.
def postpone(client, orderId, headers=None, **body):
    return client.post(f"/orders/{orderId}/postpone", json={"reasonCode": "parts_needed", **body}, headers={**STATE_HEADERS, **(headers or {})})

# The assigned technician and an admin postpone from assigned and in_progress; the status stays and each call writes
# one postponed event with the request id, the reason, the new date, and the order's technician.
@pytest.mark.parametrize("status", ["assigned", "in_progress"])
@pytest.mark.parametrize("role", ["techA", "admin"])
def testPostponeKeepsStatusAndRecordsEvent(appDb, world, clients, scalar, status, role):
    orderId = orderIn(appDb, world, status)
    newDate = (businessToday() + timedelta(days=3)).isoformat()
    response = postpone(clients[role], orderId, headers={"X-Request-ID": "req-postpone-1"}, newDate=newDate)
    assert response.status_code == 200, response.text
    assert response.json()["order"]["status"] == status
    detail = scalar("SELECT detail FROM order_event WHERE service_order_id = :id AND event_type = 'postponed'", id=orderId)
    assert detail == {"reasonCode": "parts_needed", "newDate": newDate, "technicianId": str(world["techA"])}
    assert scalar("SELECT array_agg(request_id) FROM order_event WHERE service_order_id = :id AND event_type = 'postponed'", id=orderId) == ["req-postpone-1"]
    assert scalar("SELECT from_status = to_status AND to_status = :status FROM order_event WHERE service_order_id = :id AND event_type = 'postponed'", id=orderId, status=status)
    events = clients[role].get(f"/orders/{orderId}").json()["events"]
    assert events[-1]["eventType"] == "postponed"

# A manager is refused, another technician and an unknown order get 404, and anonymous is 401.
def testPostponeAccess(appDb, world, clients, app):
    orderId = orderIn(appDb, world, "assigned")
    assert postpone(clients["manager"], orderId).status_code == 403
    assert postpone(clients["techB"], orderId).json()["code"] == "ORDER_NOT_FOUND"
    assert postpone(clients["admin"], MISSING_ID).status_code == 404
    assert postpone(TestClient(app), orderId).status_code == 401

# A finished or closed order cannot be postponed.
@pytest.mark.parametrize("status", ["job_done", "closed"])
def testPostponeRefusedAfterWork(appDb, world, clients, status):
    response = postpone(clients["admin"], orderIn(appDb, world, status))
    assert (response.status_code, response.json()["code"]) == (409, "INVALID_TRANSITION")

# An unknown reason, a past date, a date over 90 days ahead, and a malformed date are refused with field errors.
def testPostponeValidation(appDb, world, clients, scalar):
    orderId = orderIn(appDb, world, "assigned")
    today = businessToday()
    cases = [
        ({"reasonCode": "lunch"}, "reasonCode"),
        ({"newDate": (today - timedelta(days=1)).isoformat()}, "newDate"),
        ({"newDate": (today + timedelta(days=91)).isoformat()}, "newDate"),
        ({"newDate": "next week"}, "newDate"),
    ]
    for body, field in cases:
        response = postpone(clients["techA"], orderId, **body)
        assert (response.status_code, response.json()["code"]) == (422, "VALIDATION_FAILED")
        assert field in response.json()["fields"]
    assert postpone(clients["techA"], orderId, newDate=(today + timedelta(days=90)).isoformat()).status_code == 200
    assert scalar("SELECT count(*) FROM order_event WHERE service_order_id = :id AND event_type = 'postponed'", id=orderId) == 1

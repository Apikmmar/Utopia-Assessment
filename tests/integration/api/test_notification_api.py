import pytest
from fastapi.testclient import TestClient
from modules.notification import service as notificationService
from tests.order_support import insertOrder, queueAssigned, queueDone
from tests.support import MISSING_ID, STATE_HEADERS

EMAILS = {"admin": "admin.notify@example.com", "manager": "manager.notify@example.com", "techA": "tom.notify@example.com", "techB": "bala.notify@example.com"}
RESPONSE_FIELDS = {
    "notificationId", "orderId", "orderNo", "notificationType", "channel", "recipientType", "recipientName", "recipientPhone",
    "message", "deepLink", "status", "readyAt", "openedAt", "openedBy", "canSend", "createdAt",
}

# Two technicians each with one assigned order, a job_assigned notification to them, and a job_done one they are to send.
@pytest.fixture
def world(appDb, seedUser):
    ids = {
        "admin": seedUser(EMAILS["admin"], "admin", name="Ada Admin"),
        "manager": seedUser(EMAILS["manager"], "manager", name="Max Manager"),
        "techA": seedUser(EMAILS["techA"], "technician", name="Tom Tech", phone="60111111111"),
        "techB": seedUser(EMAILS["techB"], "technician", name="Bala Tech", phone="60122222222"),
    }
    orderA, orderNoA = insertOrder(appDb, ids["admin"], ids["techA"])
    orderB, orderNoB = insertOrder(appDb, ids["admin"], ids["techB"])
    rows = {
        "assignedA": queueAssigned(appDb, orderA, orderNoA, ids["techA"]),
        "doneA": queueDone(appDb, orderA, orderNoA, ids["techA"]),
        "assignedB": queueAssigned(appDb, orderB, orderNoB, ids["techB"], technicianName="Bala Tech", technicianPhone="60122222222"),
        "doneB": queueDone(appDb, orderB, orderNoB, ids["techB"], technicianName="Bala Tech"),
    }
    return {"ids": ids, "orders": {"A": orderA, "B": orderB}, "orderNos": {"A": orderNoA, "B": orderNoB}, "rows": {key: row["notification_id"] for key, row in rows.items()}}

# Returns a logged-in client for each role in the world.
@pytest.fixture
def clients(world, loggedIn):
    return {role: loggedIn(email) for role, email in EMAILS.items()}

# Returns the notification ids a list response holds.
def idsOf(response):
    assert response.status_code == 200, response.text
    return {item["notificationId"] for item in response.json()["items"]}

# Returns the string id of a named notification.
def nid(world, key):
    return str(world["rows"][key])

# Sends a POST with the origin header.
def post(client, path):
    return client.post(path, headers=STATE_HEADERS)

# The list needs a session.
def testListRequiresSession(app, world):
    assert TestClient(app).get("/notifications").status_code == 401

# Admins and managers see every notification; a technician sees only rows where they are sender or recipient, whatever the filter.
def testListScopesByRole(world, clients):
    every = {nid(world, key) for key in world["rows"]}
    assert idsOf(clients["admin"].get("/notifications")) == every
    managerItems = clients["manager"].get("/notifications").json()["items"]
    assert {item["notificationId"] for item in managerItems} == every
    assert not any(item["canSend"] for item in managerItems)
    assert idsOf(clients["techA"].get("/notifications")) == {nid(world, "assignedA"), nid(world, "doneA")}
    assert idsOf(clients["techA"].get("/notifications", params={"orderId": str(world["orders"]["B"])})) == set()

# The response has exactly the contract fields, with no template data, job id, or sender id.
def testResponseFields(world, clients):
    item = clients["admin"].get("/notifications").json()["items"][0]
    assert set(item) == RESPONSE_FIELDS
    assert item["status"] == "queued" and item["message"] is None and item["deepLink"] is None

# State, order, type, and search filters narrow the list; search matches an order number prefix or a recipient name.
def testListFilters(world, clients):
    admin = clients["admin"]
    assert len(idsOf(admin.get("/notifications", params={"state": "pending"}))) == 4
    assert idsOf(admin.get("/notifications", params={"state": "sent"})) == set()
    assert idsOf(admin.get("/notifications", params={"notificationType": "job_done"})) == {nid(world, "doneA"), nid(world, "doneB")}
    assert idsOf(admin.get("/notifications", params={"orderId": str(world["orders"]["A"])})) == {nid(world, "assignedA"), nid(world, "doneA")}
    assert idsOf(admin.get("/notifications", params={"search": world["orderNos"]["B"]})) == {nid(world, "assignedB"), nid(world, "doneB")}
    assert idsOf(admin.get("/notifications", params={"search": "bala"})) == {nid(world, "assignedB")}
    assert idsOf(admin.get("/notifications", params={"search": "%"})) == set()
    assert admin.get("/notifications", params={"state": "lost"}).status_code == 422
    assert admin.get("/notifications", params={"pageSize": 101}).status_code == 422

# Sendable keeps the pending rows this user is expected to send: every one for admins, their own for a technician, none for a manager.
def testSendableFilter(world, clients):
    assert len(idsOf(clients["admin"].get("/notifications", params={"sendable": "true"}))) == 4
    assert idsOf(clients["techA"].get("/notifications", params={"sendable": "true"})) == {nid(world, "doneA")}
    assert clients["manager"].get("/notifications", params={"sendable": "true"}).json()["total"] == 0

# Opening before the worker prepared the message is refused with 409.
def testOpenBeforeReadyIsRefused(world, clients):
    response = post(clients["techA"], f"/notifications/{nid(world, 'doneA')}/open")
    assert (response.status_code, response.json()["code"]) == (409, "NOTIFICATION_NOT_READY")

# The sending technician opens their ready notification; opening again keeps the first time and user.
def testTechnicianOpensOwnNotification(world, clients):
    notificationService.deliver(world["rows"]["doneA"])
    first = post(clients["techA"], f"/notifications/{nid(world, 'doneA')}/open")
    assert first.status_code == 200, first.text
    opened = first.json()["notification"]
    assert opened["status"] == "opened" and opened["openedBy"]["name"] == "Tom Tech" and opened["canSend"] is True
    assert opened["deepLink"].startswith("https://wa.me/60123456789?text=Hi%20Siti")
    again = post(clients["techA"], f"/notifications/{nid(world, 'doneA')}/open").json()["notification"]
    assert again["openedAt"] == opened["openedAt"]
    assert idsOf(clients["admin"].get("/notifications", params={"state": "sent"})) == {nid(world, "doneA")}

# Managers cannot send, a technician cannot send another technician's or their own incoming notification, and unknown ids are 404.
def testOpenPermissions(world, clients):
    for key in world["rows"]:
        notificationService.deliver(world["rows"][key])
    assert post(clients["manager"], f"/notifications/{nid(world, 'doneA')}/open").status_code == 403
    assert post(clients["techA"], f"/notifications/{nid(world, 'doneB')}/open").json()["code"] == "NOTIFICATION_NOT_FOUND"
    assert post(clients["techA"], f"/notifications/{nid(world, 'assignedA')}/open").status_code == 403
    assert post(clients["admin"], f"/notifications/{MISSING_ID}/open").status_code == 404
    assert post(clients["admin"], f"/notifications/{nid(world, 'assignedA')}/open").status_code == 200

# Only a failed notification can be retried, only by an admin, and the retry queues a new job.
def testRetry(world, clients, scalar):
    doneA = nid(world, "doneA")
    assert post(clients["admin"], f"/notifications/{doneA}/retry").json()["code"] == "NOTIFICATION_NOT_FAILED"
    notificationService.markFailed(world["rows"]["doneA"], "ValueError")
    oldJob = scalar("SELECT job_id FROM notification WHERE notification_id = :id", id=doneA)
    assert post(clients["techA"], f"/notifications/{doneA}/retry").status_code == 403
    response = post(clients["admin"], f"/notifications/{doneA}/retry")
    assert response.status_code == 200 and response.json()["notification"]["status"] == "queued"
    newJob = scalar("SELECT job_id FROM notification WHERE notification_id = :id", id=doneA)
    assert newJob != oldJob
    assert scalar("SELECT status FROM job WHERE job_id = :id", id=newJob) == "pending"
    assert scalar("SELECT error_message IS NULL FROM notification WHERE notification_id = :id", id=doneA) is True
    assert post(clients["admin"], f"/notifications/{MISSING_ID}/retry").status_code == 404

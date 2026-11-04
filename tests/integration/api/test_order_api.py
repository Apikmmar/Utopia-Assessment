import pytest
from fastapi.testclient import TestClient
from tests.support import MISSING_ID, STATE_HEADERS

EMAILS = {"admin": "admin.orders@example.com", "manager": "manager.orders@example.com", "techA": "tom.orders@example.com", "techB": "bala.orders@example.com"}
ORDER_FIELDS = {
    "orderId", "orderNo", "customerName", "customerPhone", "address", "problemDescription", "serviceType", "quotedPrice", "technician",
    "adminNotes", "status", "statusChangedAt", "startedAt", "jobDoneAt", "reviewedAt", "closedAt", "createdAt",
}

# Seeded users for every role and the repair service type id.
@pytest.fixture
def world(appDb, seedUser, scalar):
    return {
        "admin": seedUser(EMAILS["admin"], "admin", name="Ada Admin"),
        "manager": seedUser(EMAILS["manager"], "manager", name="Max Manager"),
        "techA": seedUser(EMAILS["techA"], "technician", name="Tom Tech", phone="60111111111"),
        "techB": seedUser(EMAILS["techB"], "technician", name="Bala Tech", phone="60122222222"),
        "repair": str(scalar("SELECT service_type_id FROM service_type WHERE service_type_code = 'repair'")),
        "cleaning": str(scalar("SELECT service_type_id FROM service_type WHERE service_type_code = 'cleaning'")),
    }

# Returns a logged-in client for each role.
@pytest.fixture
def clients(world, loggedIn):
    return {role: loggedIn(email) for role, email in EMAILS.items()}

# Returns a valid create body with overrides.
def orderBody(world, **overrides):
    body = {
        "customerName": "Siti Customer", "customerPhone": "012-345 6789", "address": "No 1, Jalan Damai, KL",
        "problemDescription": "Aircond leaking water", "serviceTypeId": world["repair"], "quotedPrice": "150.5",
    }
    body.update(overrides)
    return body

# Sends one state-changing request with the origin header.
def send(client, method, path, body=None):
    return client.request(method, path, json=body, headers=STATE_HEADERS)

# Creates an order as the admin and returns its response body.
def createOrder(clients, world, **overrides):
    response = send(clients["admin"], "POST", "/orders", orderBody(world, **overrides))
    assert response.status_code == 201, response.text
    return response.json()

# Returns the event types of an order, oldest first.
def eventTypes(client, orderId):
    return [event["eventType"] for event in client.get(f"/orders/{orderId}").json()["events"]]

# Returns the request ids recorded on an order's events.
def eventRequestIds(scalar, orderId):
    return scalar("SELECT array_agg(DISTINCT request_id) FROM order_event WHERE service_order_id = :id", id=orderId)

# An unassigned order is created as new with a normalised phone, a two-place price, and a created event.
def testCreateUnassigned(world, clients):
    body = createOrder(clients, world, adminNotes="  ")
    order = body["order"]
    assert set(order) == ORDER_FIELDS
    assert (order["status"], order["customerPhone"], order["quotedPrice"], order["technician"], order["adminNotes"]) == ("new", "60123456789", "150.50", None, None)
    assert order["orderNo"].startswith("ORD-") and body["notification"] is None
    assert order["serviceType"]["name"] == "Repair"
    assert eventTypes(clients["admin"], order["orderId"]) == ["created"]

# Creating with a technician assigns it, queues the technician's notification, and records the events in order.
def testCreateAssignedQueuesNotification(world, clients, scalar):
    body = createOrder(clients, world, technicianId=str(world["techA"]), adminNotes="Bring a ladder")
    order, notification = body["order"], body["notification"]
    assert order["status"] == "assigned" and order["technician"]["name"] == "Tom Tech"
    assert (notification["notificationType"], notification["recipientName"], notification["status"]) == ("job_assigned", "Tom Tech", "queued")
    assert eventTypes(clients["admin"], order["orderId"]) == ["created", "assigned", "notification_queued"]
    assert scalar("SELECT template_data ->> 'adminNotes' FROM notification WHERE notification_id = :id", id=notification["notificationId"]) == "Bring a ladder"

# Field errors come back together under their camelCase names; a bad type or technician is refused.
def testCreateValidation(world, clients):
    response = send(clients["admin"], "POST", "/orders", orderBody(world, customerName=" ", customerPhone="12", quotedPrice="1.005", address=""))
    assert response.status_code == 422
    assert set(response.json()["fields"]) == {"customerName", "customerPhone", "quotedPrice", "address"}
    assert send(clients["admin"], "POST", "/orders", orderBody(world, quotedPrice=-1)).json()["fields"].keys() == {"quotedPrice"}
    assert send(clients["admin"], "POST", "/orders", orderBody(world, serviceTypeId=MISSING_ID)).json()["code"] == "INVALID_SERVICE_TYPE"
    assert send(clients["admin"], "POST", "/orders", orderBody(world, technicianId=str(world["manager"]))).json()["code"] == "INVALID_TECHNICIAN"
    assert send(clients["admin"], "POST", "/orders", {**orderBody(world), "status": "closed"}).status_code == 422

# Only admins create, edit, and assign; only technicians start; only managers review and close; anonymous is 401.
def testRolesPerEndpoint(world, clients, app):
    orderId = createOrder(clients, world, technicianId=str(world["techA"]))["order"]["orderId"]
    anonymous = TestClient(app)
    assert anonymous.get("/orders").status_code == 401
    for role in ("manager", "techA"):
        assert send(clients[role], "POST", "/orders", orderBody(world)).status_code == 403
        assert send(clients[role], "PATCH", f"/orders/{orderId}", {"address": "X"}).status_code == 403
        assert send(clients[role], "POST", f"/orders/{orderId}/assign", {"technicianId": str(world["techB"])}).status_code == 403
    for role in ("admin", "manager"):
        assert send(clients[role], "POST", f"/orders/{orderId}/start").status_code == 403
    for role in ("admin", "techA"):
        assert send(clients[role], "POST", f"/orders/{orderId}/review").status_code == 403
        assert send(clients[role], "POST", f"/orders/{orderId}/close").status_code == 403

# A technician sees only their own orders, in the list and by id, whatever filters they send.
def testTechnicianScope(world, clients):
    mine = createOrder(clients, world, technicianId=str(world["techA"]))["order"]["orderId"]
    theirs = createOrder(clients, world, technicianId=str(world["techB"]))["order"]["orderId"]
    createOrder(clients, world)
    listed = clients["techA"].get("/orders", params={"technicianId": str(world["techB"])}).json()
    assert [item["orderId"] for item in listed["items"]] == [mine]
    assert clients["techA"].get(f"/orders/{theirs}").json()["code"] == "ORDER_NOT_FOUND"
    assert send(clients["techA"], "POST", f"/orders/{theirs}/start").status_code == 404
    assert clients["admin"].get("/orders").json()["total"] == 3
    assert clients["manager"].get("/orders").json()["total"] == 3

# The list filters by search, status, and technician, sorts both ways, and caps the page size.
def testListFiltersAndSort(world, clients):
    first = createOrder(clients, world, customerName="Aminah")["order"]
    second = createOrder(clients, world, customerName="Bob", technicianId=str(world["techA"]))["order"]
    admin = clients["admin"]
    assert [item["orderId"] for item in admin.get("/orders").json()["items"]] == [second["orderId"], first["orderId"]]
    assert [item["orderId"] for item in admin.get("/orders", params={"sort": "oldest"}).json()["items"]] == [first["orderId"], second["orderId"]]
    assert [item["orderId"] for item in admin.get("/orders", params={"search": "amin"}).json()["items"]] == [first["orderId"]]
    assert [item["orderId"] for item in admin.get("/orders", params={"search": second["orderNo"]}).json()["items"]] == [second["orderId"]]
    assert admin.get("/orders", params={"status": ["new", "assigned"]}).json()["total"] == 2
    assert admin.get("/orders", params={"status": "assigned"}).json()["items"][0]["technician"] == {"userId": str(world["techA"]), "name": "Tom Tech"}
    assert admin.get("/orders", params={"technicianId": str(world["techA"])}).json()["total"] == 1
    assert admin.get("/orders", params={"status": "lost"}).status_code == 422
    assert admin.get("/orders", params={"pageSize": 101}).status_code == 422

# Editing records the changed fields; editing and reassigning after the job starts are locked.
def testEditThenLockAfterStart(world, clients):
    orderId = createOrder(clients, world, technicianId=str(world["techA"]))["order"]["orderId"]
    edited = send(clients["admin"], "PATCH", f"/orders/{orderId}", {"address": "No 2, Jalan Baru", "serviceTypeId": world["cleaning"], "quotedPrice": 200})
    assert edited.status_code == 200 and edited.json()["order"]["quotedPrice"] == "200.00"
    events = clients["admin"].get(f"/orders/{orderId}").json()["events"]
    assert events[-1]["eventType"] == "edited" and events[-1]["detail"] == {"fields": ["address", "quotedPrice", "serviceTypeId"]}
    assert send(clients["admin"], "PATCH", f"/orders/{orderId}", {"address": "No 2, Jalan Baru"}).status_code == 200
    assert eventTypes(clients["admin"], orderId).count("edited") == 1
    assert send(clients["techA"], "POST", f"/orders/{orderId}/start").status_code == 200
    assert send(clients["admin"], "PATCH", f"/orders/{orderId}", {"address": "X"}).json()["code"] == "ORDER_LOCKED"
    assert send(clients["admin"], "POST", f"/orders/{orderId}/assign", {"technicianId": str(world["techB"])}).json()["code"] == "ORDER_LOCKED"

# Assigning a new order moves it to assigned; reassigning records both technicians; the same technician again is a no-op.
def testAssignAndReassign(world, clients):
    orderId = createOrder(clients, world)["order"]["orderId"]
    assigned = send(clients["admin"], "POST", f"/orders/{orderId}/assign", {"technicianId": str(world["techA"])}).json()
    assert assigned["order"]["status"] == "assigned" and assigned["notification"]["recipientName"] == "Tom Tech"
    again = send(clients["admin"], "POST", f"/orders/{orderId}/assign", {"technicianId": str(world["techA"])}).json()
    assert again["notification"] is None
    moved = send(clients["admin"], "POST", f"/orders/{orderId}/assign", {"technicianId": str(world["techB"])}).json()
    assert moved["order"]["technician"]["name"] == "Bala Tech" and moved["notification"]["recipientName"] == "Bala Tech"
    events = clients["admin"].get(f"/orders/{orderId}").json()["events"]
    assert [event["eventType"] for event in events] == ["created", "assigned", "notification_queued", "reassigned", "notification_queued"]
    assert events[3]["detail"] == {"technicianId": str(world["techB"]), "previousTechnicianId": str(world["techA"])}
    assert clients["techA"].get(f"/orders/{orderId}").status_code == 404
    assert send(clients["admin"], "POST", f"/orders/{orderId}/assign", {"technicianId": MISSING_ID}).json()["code"] == "INVALID_TECHNICIAN"

# The full workflow runs start, then (with the job done) review and close, and each step out of order is a 409.
def testWorkflowAndInvalidTransitions(world, clients, execute, scalar):
    orderId = createOrder(clients, world, technicianId=str(world["techA"]))["order"]["orderId"]
    assert send(clients["manager"], "POST", f"/orders/{orderId}/review").json()["code"] == "INVALID_TRANSITION"
    started = send(clients["techA"], "POST", f"/orders/{orderId}/start").json()["order"]
    assert started["status"] == "in_progress" and started["startedAt"] is not None
    again = send(clients["techA"], "POST", f"/orders/{orderId}/start")
    assert again.status_code == 409 and "in_progress" in again.json()["detail"]
    execute("UPDATE service_order SET status = 'job_done', job_done_at = now() WHERE service_order_id = :id", id=orderId)
    assert send(clients["manager"], "POST", f"/orders/{orderId}/close").status_code == 409
    reviewed = send(clients["manager"], "POST", f"/orders/{orderId}/review").json()["order"]
    assert reviewed["status"] == "reviewed" and reviewed["reviewedAt"] is not None
    closed = send(clients["manager"], "POST", f"/orders/{orderId}/close").json()["order"]
    assert closed["status"] == "closed" and closed["closedAt"] is not None
    assert str(scalar("SELECT closed_by_id FROM service_order WHERE service_order_id = :id", id=orderId)) == str(world["manager"])
    assert eventTypes(clients["admin"], orderId)[-3:] == ["started", "reviewed", "closed"]

# Every event records the request id of the request that caused it.
def testEventsCarryRequestId(world, clients, scalar):
    response = clients["admin"].post("/orders", json=orderBody(world), headers={**STATE_HEADERS, "X-Request-ID": "req-create-1"})
    orderId = response.json()["order"]["orderId"]
    assert eventRequestIds(scalar, orderId) == ["req-create-1"]

# Unknown orders are 404 everywhere.
def testUnknownOrder(world, clients):
    assert clients["admin"].get(f"/orders/{MISSING_ID}").json()["code"] == "ORDER_NOT_FOUND"
    assert send(clients["admin"], "PATCH", f"/orders/{MISSING_ID}", {"address": "X"}).status_code == 404
    assert send(clients["manager"], "POST", f"/orders/{MISSING_ID}/review").status_code == 404

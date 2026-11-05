import pytest
from tests.order_support import JPEG_BYTES, PDF_BYTES, insertOrder
from tests.support import MISSING_ID, STATE_HEADERS

EMAILS = {
    "admin": "admin.done@example.com", "manager": "manager.done@example.com",
    "techA": "tom.done@example.com", "techB": "bala.done@example.com",
}

# Users for every role and one in-progress order (quoted 150.00) assigned to technician A. Storage is the in-memory
# fake, so these checks are labelled as mocked storage.
@pytest.fixture
def world(appDb, seedUser, fakeStorage):
    ids = {
        "admin": seedUser(EMAILS["admin"], "admin", name="Ada Admin"),
        "manager": seedUser(EMAILS["manager"], "manager", name="Max Manager"),
        "techA": seedUser(EMAILS["techA"], "technician", name="Tom Tech", phone="60111111111"),
        "techB": seedUser(EMAILS["techB"], "technician", name="Bala Tech", phone="60122222222"),
    }
    orderId, orderNo = insertOrder(appDb, ids["admin"], ids["techA"], status="in_progress")
    return {**ids, "orderId": str(orderId), "orderNo": orderNo, "storage": fakeStorage}

# Returns a logged-in client for each role.
@pytest.fixture
def clients(world, loggedIn):
    return {role: loggedIn(email) for role, email in EMAILS.items()}

# Requests an upload URL as the technician, optionally puts the bytes into fake storage, and returns the attachment id.
def addFile(world, client, orderId=None, kind="completion", contentType="image/jpeg", content=JPEG_BYTES, upload=True):
    body = {"kind": kind, "fileName": "file", "contentType": contentType, "sizeBytes": len(content)}
    response = client.post(f"/orders/{orderId or world['orderId']}/attachments", json=body, headers=STATE_HEADERS)
    assert response.status_code == 201, response.text
    payload = response.json()
    if upload:
        path = payload["uploadUrl"].split("/upload/", 1)[1].split("?", 1)[0]
        world["storage"].put(path, content, contentType)
    return payload["attachment"]["attachmentId"]

# Submits a completion as the given client and returns the response.
def submit(client, orderId, **body):
    return client.post(f"/orders/{orderId}/completion", json={"workDone": "Cleaned the filter", **body}, headers=STATE_HEADERS)

# The technician completes the job: the server computes the final amount from the order's quoted price, confirms the
# files, moves the order to job_done, and queues the customer's WhatsApp message sent by the technician.
def testSubmitCompletion(world, clients, scalar):
    photo = addFile(world, clients["techA"])
    response = submit(clients["techA"], world["orderId"], extraCharges="20.50", remarks=" Gas topped up ", attachmentIds=[photo])
    assert response.status_code == 201, response.text
    body = response.json()
    completion = body["completion"]
    assert (completion["quotedPrice"], completion["extraCharges"], completion["finalAmount"]) == ("150.00", "20.50", "170.50")
    assert (completion["remarks"], completion["payment"], completion["technician"]["name"]) == ("Gas topped up", None, "Tom Tech")
    assert (body["order"]["status"], body["order"]["jobDoneAt"] is not None) == ("job_done", True)
    notification = body["notification"]
    assert (notification["notificationType"], notification["recipientType"], notification["status"]) == ("job_done", "customer", "ready")
    assert notification["recipientName"] == "Siti Customer" and notification["orderNo"] == world["orderNo"]
    senderId = scalar("SELECT sender_user_id FROM notification WHERE notification_id = :id", id=notification["notificationId"])
    assert str(senderId) == str(world["techA"])
    assert scalar("SELECT status FROM order_attachment WHERE order_attachment_id = :id", id=photo) == "uploaded"
    events = scalar("SELECT string_agg(event_type, ',' ORDER BY created_at) FROM order_event WHERE service_order_id = :id", id=world["orderId"])
    assert events == "completed,notification_queued"
    assert scalar("SELECT count(*) FROM order_event WHERE service_order_id = :id AND request_id IS NULL", id=world["orderId"]) == 0

# Extra charges default to zero, and a client cannot send its own final amount or quoted price.
def testAmountsComeFromTheServer(world, clients):
    rejected = submit(clients["techA"], world["orderId"], finalAmount="1.00")
    assert (rejected.status_code, rejected.json()["code"]) == (422, "VALIDATION_FAILED")
    response = submit(clients["techA"], world["orderId"])
    assert response.status_code == 201, response.text
    assert (response.json()["completion"]["extraCharges"], response.json()["completion"]["finalAmount"]) == ("0.00", "150.00")

# Field rules: work done required, amounts non-negative with two places, payment method from the list.
@pytest.mark.parametrize("body, field", [
    ({"workDone": "   "}, "workDone"),
    ({"extraCharges": "-1"}, "extraCharges"),
    ({"extraCharges": "0.005"}, "extraCharges"),
    ({"remarks": "x" * 2001}, "remarks"),
    ({"payment": {"amount": "abc", "method": "cash"}}, "payment.amount"),
    ({"payment": {"amount": "10", "method": "cheque"}}, "payment.method"),
])
def testFieldRules(world, clients, scalar, body, field):
    response = submit(clients["techA"], world["orderId"], **body)
    assert (response.status_code, response.json()["code"]) == (422, "VALIDATION_FAILED")
    assert field in response.json()["fields"]
    assert scalar("SELECT status FROM service_order WHERE service_order_id = :id", id=world["orderId"]) == "in_progress"

# A payment with a receipt is stored as a pair, and the receipt file is confirmed with the completion.
def testPaymentWithReceipt(world, clients, scalar):
    receipt = addFile(world, clients["techA"], kind="receipt", contentType="application/pdf", content=PDF_BYTES)
    response = submit(clients["techA"], world["orderId"], payment={"amount": 170.5, "method": "ewallet", "receiptAttachmentId": receipt})
    assert response.status_code == 201, response.text
    assert response.json()["completion"]["payment"] == {"amount": "170.50", "method": "ewallet", "receiptAttachmentId": receipt}
    assert scalar("SELECT status FROM order_attachment WHERE order_attachment_id = :id", id=receipt) == "uploaded"

# A completion file given as the receipt, or a receipt given as a completion file, is refused.
def testFileKindMustMatch(world, clients):
    photo = addFile(world, clients["techA"])
    response = submit(clients["techA"], world["orderId"], payment={"amount": "10", "method": "cash", "receiptAttachmentId": photo})
    assert (response.status_code, response.json()["code"]) == (422, "ATTACHMENT_INVALID")

# A file that never reached storage, or one belonging to another order, is refused and nothing changes.
def testUnuploadedAndForeignFiles(world, clients, appDb, execute, scalar):
    missing = addFile(world, clients["techA"], upload=False)
    response = submit(clients["techA"], world["orderId"], attachmentIds=[missing])
    assert (response.status_code, response.json()["code"]) == (422, "ATTACHMENT_NOT_UPLOADED")
    otherId, _ = insertOrder(appDb, world["admin"], world["techA"], status="in_progress")
    foreign = addFile(world, clients["techA"], orderId=str(otherId))
    response = submit(clients["techA"], world["orderId"], attachmentIds=[foreign])
    assert (response.status_code, response.json()["code"]) == (422, "ATTACHMENT_INVALID")
    assert scalar("SELECT count(*) FROM order_completion") == 0
    assert scalar("SELECT status FROM service_order WHERE service_order_id = :id", id=world["orderId"]) == "in_progress"

# A second submit is refused with 409 and leaves the first record and its single notification in place.
def testSecondSubmitRefused(world, clients, scalar):
    assert submit(clients["techA"], world["orderId"]).status_code == 201
    response = submit(clients["techA"], world["orderId"], workDone="Again")
    assert (response.status_code, response.json()["code"]) == (409, "INVALID_TRANSITION")
    assert scalar("SELECT count(*) FROM order_completion") == 1
    assert scalar("SELECT count(*) FROM notification WHERE notification_type = 'job_done'") == 1

# Only the assigned technician may complete: other roles get 403, another technician 404, and a job not yet started 409.
def testWhoMayComplete(world, clients, execute):
    assert submit(clients["admin"], world["orderId"]).status_code == 403
    assert submit(clients["manager"], world["orderId"]).status_code == 403
    assert submit(clients["techB"], world["orderId"]).json()["code"] == "ORDER_NOT_FOUND"
    assert submit(clients["techA"], MISSING_ID).status_code == 404
    execute("UPDATE service_order SET status = 'assigned' WHERE service_order_id = :id", id=world["orderId"])
    response = submit(clients["techA"], world["orderId"])
    assert (response.status_code, response.json()["code"]) == (409, "INVALID_TRANSITION")

# With storage down, a completion with files answers 503 and changes nothing.
def testStorageDownChangesNothing(world, clients, scalar):
    photo = addFile(world, clients["techA"])
    world["storage"].down = True
    response = submit(clients["techA"], world["orderId"], attachmentIds=[photo])
    assert (response.status_code, response.json()["code"]) == (503, "STORAGE_UNAVAILABLE")
    assert scalar("SELECT count(*) FROM order_completion") == 0
    assert scalar("SELECT count(*) FROM notification") == 0
    assert scalar("SELECT status FROM order_attachment WHERE order_attachment_id = :id", id=photo) == "pending"
    assert scalar("SELECT status FROM service_order WHERE service_order_id = :id", id=world["orderId"]) == "in_progress"

# Reading the completion: 404 COMPLETION_NOT_FOUND before the job is done, then the record for every role that may
# see the order, and ORDER_NOT_FOUND for another technician.
def testGetCompletion(world, clients):
    response = clients["admin"].get(f"/orders/{world['orderId']}/completion")
    assert (response.status_code, response.json()["code"]) == (404, "COMPLETION_NOT_FOUND")
    created = submit(clients["techA"], world["orderId"], extraCharges=5).json()["completion"]
    for role in ("admin", "manager", "techA"):
        response = clients[role].get(f"/orders/{world['orderId']}/completion")
        assert response.status_code == 200, response.text
        assert response.json()["completion"] == created
    assert clients["techB"].get(f"/orders/{world['orderId']}/completion").json()["code"] == "ORDER_NOT_FOUND"

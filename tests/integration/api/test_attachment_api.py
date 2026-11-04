import uuid
import pytest
from core.auth import AuthUser
from modules.attachment import service as attachmentService
from modules.order import service as orderService
from tests.order_support import JPEG_BYTES, PDF_BYTES, insertOrder
from tests.support import MISSING_ID, STATE_HEADERS

EMAILS = {"admin": "admin.files@example.com", "manager": "manager.files@example.com", "techA": "tom.files@example.com", "techB": "bala.files@example.com"}

# Users for every role and one in-progress order assigned to technician A. Storage is the in-memory fake.
@pytest.fixture
def world(appDb, seedUser, fakeStorage):
    ids = {
        "admin": seedUser(EMAILS["admin"], "admin", name="Ada Admin"),
        "manager": seedUser(EMAILS["manager"], "manager", name="Max Manager"),
        "techA": seedUser(EMAILS["techA"], "technician", name="Tom Tech", phone="60111111111"),
        "techB": seedUser(EMAILS["techB"], "technician", name="Bala Tech", phone="60122222222"),
    }
    orderId, _ = insertOrder(appDb, ids["admin"], ids["techA"], status="in_progress")
    return {**ids, "orderId": str(orderId), "storage": fakeStorage}

# Returns a logged-in client for each role.
@pytest.fixture
def clients(world, loggedIn):
    return {role: loggedIn(email) for role, email in EMAILS.items()}

# Asks for an upload URL as the given client and returns the response.
def requestUpload(client, orderId, kind="completion", contentType="image/jpeg", size=len(JPEG_BYTES), fileName="photo.jpg"):
    body = {"kind": kind, "fileName": fileName, "contentType": contentType, "sizeBytes": size}
    return client.post(f"/orders/{orderId}/attachments", json=body, headers=STATE_HEADERS)

# Returns the storage path a fake signed upload URL points at.
def pathOf(uploadUrl):
    return uploadUrl.split("/upload/", 1)[1].split("?", 1)[0]

# The assigned technician gets a pending file and a signed URL whose path is built from ids, not the file name.
def testRequestUploadForOwnJob(world, clients):
    response = requestUpload(clients["techA"], world["orderId"], fileName="../../etc/passwd.jpg")
    assert response.status_code == 201, response.text
    body = response.json()
    attachment = body["attachment"]
    assert (attachment["status"], attachment["viewUrl"], attachment["fileName"]) == ("pending", None, "../../etc/passwd.jpg")
    assert pathOf(body["uploadUrl"]) == f"orders/{world['orderId']}/{attachment['attachmentId']}.jpg"

# Other roles are refused, another technician sees no such order, and a job not in progress takes no files.
def testUploadPermissionsAndStatus(world, clients, appDb, execute):
    assert requestUpload(clients["admin"], world["orderId"]).status_code == 403
    assert requestUpload(clients["manager"], world["orderId"]).status_code == 403
    assert requestUpload(clients["techB"], world["orderId"]).json()["code"] == "ORDER_NOT_FOUND"
    execute("UPDATE service_order SET status = 'assigned' WHERE service_order_id = :id", id=world["orderId"])
    response = requestUpload(clients["techA"], world["orderId"])
    assert (response.status_code, response.json()["code"]) == (409, "INVALID_TRANSITION")
    assert requestUpload(clients["techA"], MISSING_ID).status_code == 404

# A disallowed type or an oversized file is refused before anything is stored.
def testUploadTypeAndSizeRules(world, clients, scalar):
    assert requestUpload(clients["techA"], world["orderId"], contentType="text/html").json()["code"] == "ATTACHMENT_INVALID"
    assert requestUpload(clients["techA"], world["orderId"], size=10 * 1024 * 1024 + 1).json()["code"] == "ATTACHMENT_INVALID"
    assert requestUpload(clients["techA"], world["orderId"], kind="receipt", contentType="video/mp4", size=1000).json()["code"] == "ATTACHMENT_INVALID"
    assert scalar("SELECT count(*) FROM order_attachment") == 0

# The seventh completion file and the second receipt are refused with ATTACHMENT_LIMIT.
def testUploadCountLimits(world, clients):
    for _ in range(6):
        assert requestUpload(clients["techA"], world["orderId"]).status_code == 201
    response = requestUpload(clients["techA"], world["orderId"])
    assert (response.status_code, response.json()["code"]) == (409, "ATTACHMENT_LIMIT")
    assert requestUpload(clients["techA"], world["orderId"], kind="receipt", contentType="application/pdf", size=100).status_code == 201
    assert requestUpload(clients["techA"], world["orderId"], kind="receipt", contentType="application/pdf", size=100).json()["code"] == "ATTACHMENT_LIMIT"

# Deleting a pending file frees its slot and removes the stored object; an uploaded one is locked; unknown ids are 404.
def testDeletePendingAndLocked(world, clients, execute):
    body = requestUpload(clients["techA"], world["orderId"]).json()
    attachmentId = body["attachment"]["attachmentId"]
    assert clients["techB"].delete(f"/orders/{world['orderId']}/attachments/{attachmentId}", headers=STATE_HEADERS).status_code == 404
    assert clients["techA"].delete(f"/orders/{world['orderId']}/attachments/{attachmentId}", headers=STATE_HEADERS).status_code == 204
    assert pathOf(body["uploadUrl"]) in world["storage"].deleted
    assert clients["techA"].delete(f"/orders/{world['orderId']}/attachments/{attachmentId}", headers=STATE_HEADERS).json()["code"] == "ATTACHMENT_NOT_FOUND"
    second = requestUpload(clients["techA"], world["orderId"]).json()["attachment"]["attachmentId"]
    execute("UPDATE order_attachment SET status = 'uploaded' WHERE order_attachment_id = :id", id=second)
    response = clients["techA"].delete(f"/orders/{world['orderId']}/attachments/{second}", headers=STATE_HEADERS)
    assert (response.status_code, response.json()["code"]) == (409, "ATTACHMENT_LOCKED")

# Uploaded files carry view links for everyone who may see the order; pending ones show only to the assigned technician.
def testListShowsPendingOnlyToAssignedTechnician(world, clients, execute):
    pending = requestUpload(clients["techA"], world["orderId"]).json()["attachment"]["attachmentId"]
    uploaded = requestUpload(clients["techA"], world["orderId"]).json()["attachment"]["attachmentId"]
    execute("UPDATE order_attachment SET status = 'uploaded' WHERE order_attachment_id = :id", id=uploaded)
    techItems = clients["techA"].get(f"/orders/{world['orderId']}/attachments").json()["items"]
    assert {item["attachmentId"] for item in techItems} == {pending, uploaded}
    for role in ("admin", "manager"):
        items = clients[role].get(f"/orders/{world['orderId']}/attachments").json()["items"]
        assert [item["attachmentId"] for item in items] == [uploaded]
        assert items[0]["viewUrl"].startswith("https://storage.test/view/") and "expires=300" in items[0]["viewUrl"]
    assert clients["techB"].get(f"/orders/{world['orderId']}/attachments").status_code == 404

# With storage down, uploads and listing files answer 503 and leave nothing behind, while order actions still work.
def testStorageDown(world, clients, execute, scalar):
    uploaded = requestUpload(clients["techA"], world["orderId"]).json()["attachment"]["attachmentId"]
    execute("UPDATE order_attachment SET status = 'uploaded' WHERE order_attachment_id = :id", id=uploaded)
    world["storage"].down = True
    response = requestUpload(clients["techA"], world["orderId"])
    assert (response.status_code, response.json()["code"]) == (503, "STORAGE_UNAVAILABLE")
    assert scalar("SELECT count(*) FROM order_attachment") == 1
    assert clients["admin"].get(f"/orders/{world['orderId']}/attachments").status_code == 503
    assert clients["admin"].get(f"/orders/{world['orderId']}").status_code == 200

# Completion verification accepts uploaded files whose content matches, and refuses missing, mislabelled, or foreign ones.
def testVerifyForCompletion(world, clients, appDb):
    tech = clients["techA"]
    photo = requestUpload(tech, world["orderId"]).json()
    receipt = requestUpload(tech, world["orderId"], kind="receipt", contentType="application/pdf", size=len(PDF_BYTES), fileName="r.pdf").json()
    world["storage"].put(pathOf(photo["uploadUrl"]), JPEG_BYTES, "image/jpeg")
    world["storage"].put(pathOf(receipt["uploadUrl"]), PDF_BYTES, "application/pdf")
    technician = AuthUser(userId=world["techA"], name="Tom Tech", email=EMAILS["techA"], roleCode="technician")
    order = orderService.repository.getOrder(world["orderId"])
    photoId, receiptId = photo["attachment"]["attachmentId"], receipt["attachment"]["attachmentId"]
    verified, error = attachmentService.verifyForCompletion(technician, order, [uuid.UUID(photoId)], uuid.UUID(receiptId))
    assert error is None and verified[uuid.UUID(photoId)] == {"sizeBytes": len(JPEG_BYTES), "contentType": "image/jpeg"}
    assert attachmentService.verifyForCompletion(technician, order, [uuid.UUID(receiptId)], None)[1]["code"] == "ATTACHMENT_INVALID"
    assert attachmentService.verifyForCompletion(technician, order, [uuid.UUID(MISSING_ID)], None)[1]["code"] == "ATTACHMENT_INVALID"
    missing = requestUpload(tech, world["orderId"]).json()["attachment"]["attachmentId"]
    assert attachmentService.verifyForCompletion(technician, order, [uuid.UUID(missing)], None)[1]["code"] == "ATTACHMENT_NOT_UPLOADED"
    fake = requestUpload(tech, world["orderId"]).json()
    world["storage"].put(pathOf(fake["uploadUrl"]), b"<html><script>alert(1)</script>", "image/jpeg")
    assert attachmentService.verifyForCompletion(technician, order, [uuid.UUID(fake["attachment"]["attachmentId"])], None)[1]["code"] == "ATTACHMENT_INVALID"

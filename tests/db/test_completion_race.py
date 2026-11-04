import threading
from core.auth import AuthUser
from modules.completion import service as completionService
from tests.order_support import insertOrder

RACERS = 2

# Two completion submits racing on one order: the order row lock and the unique key let exactly one win.
def testRacingSubmitsLetOneWin(appDb, seedUser, scalar, fakeStorage):
    adminId = seedUser("admin.done.race@example.com", "admin", password=None)
    techId = seedUser("tech.done.race@example.com", "technician", password=None, phone="60111111111")
    orderId, _ = insertOrder(appDb, adminId, techId, status="in_progress")
    technician = AuthUser(userId=techId, name="Tom", email="tech.done.race@example.com", roleCode="technician")
    barrier = threading.Barrier(RACERS)
    errors = [None] * RACERS

    # Waits for the other racer, then submits.
    def run(index):
        barrier.wait()
        errors[index] = completionService.submitCompletion(technician, orderId, {"work_done": f"Done {index}"}, f"req-{index}")[1]

    threads = [threading.Thread(target=run, args=(index,)) for index in range(RACERS)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    codes = sorted((error or {}).get("code", "OK") for error in errors)
    assert codes[1] == "OK" and codes[0] in ("INVALID_TRANSITION", "COMPLETION_EXISTS")
    assert scalar("SELECT count(*) FROM order_completion WHERE service_order_id = :id", id=orderId) == 1
    assert scalar("SELECT count(*) FROM notification WHERE service_order_id = :id", id=orderId) == 1
    assert scalar("SELECT count(*) FROM order_event WHERE service_order_id = :id AND event_type = 'completed'", id=orderId) == 1

# A file removed after verification but before the completion saves makes the save refuse and keep nothing.
def testFileDeletedAfterVerificationRollsBack(appDb, seedUser, scalar, fakeStorage, monkeypatch):
    from modules.attachment import service as attachmentService
    from tests.order_support import JPEG_BYTES
    adminId = seedUser("admin.done.gone@example.com", "admin", password=None)
    techId = seedUser("tech.done.gone@example.com", "technician", password=None, phone="60111111111")
    orderId, _ = insertOrder(appDb, adminId, techId, status="in_progress")
    technician = AuthUser(userId=techId, name="Tom", email="tech.done.gone@example.com", roleCode="technician")
    ticket, error = attachmentService.requestUpload(technician, orderId, "completion", "photo.jpg", "image/jpeg", len(JPEG_BYTES))
    assert error is None
    attachmentId = ticket["attachment"]["attachment_id"]
    fakeStorage.put(ticket["upload_url"].split("/upload/", 1)[1].split("?", 1)[0], JPEG_BYTES, "image/jpeg")
    verify = attachmentService.verifyForCompletion

    # Verifies as usual, then deletes the file the way a second tab would, before the save starts.
    def verifyThenDelete(*args):
        result = verify(*args)
        assert attachmentService.deletePending(technician, orderId, attachmentId)[1] is None
        return result

    monkeypatch.setattr(attachmentService, "verifyForCompletion", verifyThenDelete)
    _, error = completionService.submitCompletion(technician, orderId, {"work_done": "Done", "attachment_ids": [attachmentId]}, "req-gone")
    assert error["code"] == "ATTACHMENT_NOT_UPLOADED"
    assert scalar("SELECT count(*) FROM order_completion") == 0
    assert scalar("SELECT count(*) FROM notification") == 0
    assert scalar("SELECT status FROM service_order WHERE service_order_id = :id", id=orderId) == "in_progress"

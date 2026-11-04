import threading
from core.auth import AuthUser
from modules.attachment import service as attachmentService
from tests.order_support import JPEG_BYTES, insertOrder

PREFILLED = 5
RACERS = 2

# A sixth and a seventh upload request racing each other: the order row lock lets exactly one take the last slot.
def testRacingUploadsRespectTheLimit(appDb, seedUser, scalar, fakeStorage):
    adminId = seedUser("admin.upload.race@example.com", "admin", password=None)
    techId = seedUser("tech.upload.race@example.com", "technician", password=None, phone="60111111111")
    orderId, _ = insertOrder(appDb, adminId, techId, status="in_progress")
    technician = AuthUser(userId=techId, name="Tom", email="tech.upload.race@example.com", roleCode="technician")
    for _ in range(PREFILLED):
        assert attachmentService.requestUpload(technician, orderId, "completion", "photo.jpg", "image/jpeg", len(JPEG_BYTES))[1] is None
    barrier = threading.Barrier(RACERS)
    errors = [None] * RACERS

    # Waits for the other racer, then asks for an upload.
    def run(index):
        barrier.wait()
        errors[index] = attachmentService.requestUpload(technician, orderId, "completion", "photo.jpg", "image/jpeg", len(JPEG_BYTES))[1]

    threads = [threading.Thread(target=run, args=(index,)) for index in range(RACERS)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    assert sorted((error or {}).get("code", "OK") for error in errors) == ["ATTACHMENT_LIMIT", "OK"]
    assert scalar("SELECT count(*) FROM order_attachment WHERE service_order_id = :id", id=orderId) == 6

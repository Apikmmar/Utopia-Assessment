import pytest
from modules.notification import service as notificationService
from tests.order_support import insertOrder, queueAssigned, queueDone
from worker.handlers import jobHandlers
from worker.main import Worker


class Rollback(Exception):
    pass

# An admin and a technician with one assigned order.
@pytest.fixture
def order(appDb, seedUser):
    adminId = seedUser("admin.delivery@example.com", "admin", password=None)
    techId = seedUser("tech.delivery@example.com", "technician", password=None, name="Tom Tech", phone="60111111111")
    orderId, orderNo = insertOrder(appDb, adminId, techId)
    return {"orderId": orderId, "orderNo": orderNo, "techId": techId}

# One worker iteration with the real handlers takes a queued notification to ready with its message and link.
def testWorkerPreparesQueuedNotification(appDb, order, scalar):
    row = queueDone(appDb, order["orderId"], order["orderNo"], order["techId"])
    assert Worker(jobHandlers(), pollSeconds=1, workerId="test").runOnce() is True
    ready = notificationService.repository.getNotification(row["notification_id"])
    assert ready["status"] == "ready" and ready["message"].startswith("Hi Siti Customer, Job ORD-")
    assert ready["deep_link"].startswith("https://wa.me/60123456789?text=")
    assert scalar("SELECT status FROM job WHERE job_id = :id", id=ready["job_id"]) == "succeeded"

# Delivering again, as a retried job would, leaves a notification that is no longer queued unchanged.
def testDeliverIsHarmlessWhenRepeated(appDb, order):
    row = queueAssigned(appDb, order["orderId"], order["orderNo"], order["techId"])
    notificationService.deliver(row["notification_id"])
    first = notificationService.repository.getNotification(row["notification_id"])
    notificationService.deliver(row["notification_id"])
    assert notificationService.repository.getNotification(row["notification_id"]) == first

# A delivery that keeps failing ends failed with a short reason and no personal data.
def testFailingDeliveryEndsFailed(appDb, order, execute, scalar, monkeypatch):
    row = queueDone(appDb, order["orderId"], order["orderNo"], order["techId"])
    execute("UPDATE job SET max_attempt = 1 WHERE job_id = :id", id=row["job_id"])
    monkeypatch.setattr(notificationService, "renderMessage", lambda *args: (_ for _ in ()).throw(KeyError("60123456789")))
    Worker(jobHandlers(), pollSeconds=1, workerId="test").runOnce()
    assert notificationService.repository.getNotification(row["notification_id"])["status"] == "failed"
    reason = scalar("SELECT error_message FROM notification WHERE notification_id = :id", id=row["notification_id"])
    assert reason == "KeyError"
    assert scalar("SELECT error_message FROM job WHERE job_id = :id", id=row["job_id"]) == "KeyError"

# A notification queued in a transaction that rolls back leaves neither the notification nor its job.
def testEnqueueRollsBackWithTheOrderChange(appDb, order, scalar):
    with pytest.raises(Rollback):
        with appDb.begin() as conn:
            notificationService.enqueue(
                conn, order["orderId"], order["orderNo"], "job_done", {"type": "customer", "name": "Siti", "phone": "60123456789"},
                order["techId"], {"orderNo": order["orderNo"], "customerName": "Siti", "technicianName": "Tom", "completedAt": "2026-11-04T07:45:00+00:00"},
                None, "tech@example.com",
            )
            raise Rollback()
    assert scalar("SELECT count(*) FROM notification") == 0
    assert scalar("SELECT count(*) FROM job") == 0

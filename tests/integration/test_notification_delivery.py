import pytest
from modules.notification import service as notificationService
from tests.order_support import createAssigned, createDone, insertOrder


class Rollback(Exception):
    pass

# An admin and a technician with one assigned order.
@pytest.fixture
def order(appDb, seedUser):
    adminId = seedUser("admin.delivery@example.com", "admin", password=None)
    techId = seedUser("tech.delivery@example.com", "technician", password=None, name="Tom Tech", phone="60111111111")
    orderId, orderNo = insertOrder(appDb, adminId, techId)
    return {"orderId": orderId, "orderNo": orderNo, "techId": techId}

# Creating a notification prepares its message and WhatsApp link in the same transaction.
def testCreatePreparesNotification(appDb, order):
    row = createDone(appDb, order["orderId"], order["orderNo"], order["techId"])
    assert row["status"] == "ready" and row["message"].startswith("Hi Siti Customer, Job ORD-")
    assert row["deep_link"].startswith("https://wa.me/60123456789?text=")
    assert row["ready_at"] is not None

# The technician's job_assigned message carries the customer, address, service, and instructions.
def testCreatePreparesAssignedMessage(appDb, order):
    row = createAssigned(appDb, order["orderId"], order["orderNo"], order["techId"])
    assert row["status"] == "ready"
    assert "Customer: Siti Customer (60123456789)" in row["message"] and "Instructions: Bring a ladder" in row["message"]
    assert row["deep_link"].startswith("https://wa.me/60111111111?text=")

# A message that cannot be prepared leaves the notification failed with a short reason and no personal data,
# while the surrounding transaction still commits.
def testFailedPreparationStoresReasonAndCommits(appDb, order, scalar, monkeypatch):
    monkeypatch.setattr(notificationService, "renderMessage", lambda *args: (_ for _ in ()).throw(KeyError("60123456789")))
    row = createDone(appDb, order["orderId"], order["orderNo"], order["techId"])
    assert (row["status"], row["message"], row["deep_link"]) == ("failed", None, None)
    reason = scalar("SELECT error_message FROM notification WHERE notification_id = :id", id=row["notification_id"])
    assert reason == "KeyError"

# A notification created in a transaction that rolls back leaves nothing behind.
def testCreateRollsBackWithTheOrderChange(appDb, order, scalar):
    with pytest.raises(Rollback):
        with appDb.begin() as conn:
            notificationService.create(
                conn, order["orderId"], order["orderNo"], "job_done", {"type": "customer", "name": "Siti", "phone": "60123456789"},
                order["techId"], {"orderNo": order["orderNo"], "customerName": "Siti", "technicianName": "Tom", "completedAt": "2026-11-04T07:45:00+00:00"},
                None, "tech@example.com",
            )
            raise Rollback()
    assert scalar("SELECT count(*) FROM notification") == 0

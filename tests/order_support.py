import threading
from sqlalchemy import text
from core.storage import StorageUnavailable
from modules.notification import service as notificationService
from modules.notification.constants import RECIPIENT_CUSTOMER, RECIPIENT_TECHNICIAN, TYPE_JOB_ASSIGNED, TYPE_JOB_DONE

CUSTOMER_PHONE = "60123456789"
CUSTOMER_NAME = "Siti Customer"
COMPLETED_AT = "2026-11-04T07:45:00+00:00"

INSERT_ORDER = text(
    "INSERT INTO service_order (customer_name, customer_phone, address, problem_description, service_type_id, quoted_price, "
    "assigned_technician_id, status, created_by_id) "
    "SELECT :customerName, :customerPhone, 'No 1, Jalan Damai, KL', 'Aircond leaking', service_type_id, 150, :technicianId, :status, :adminId "
    "FROM service_type WHERE service_type_code = 'repair' RETURNING service_order_id, order_no"
)

# Inserts one order with the given technician and status, bypassing the order module, and returns its id and number.
def insertOrder(engine, adminId, technicianId, status="assigned"):
    with engine.begin() as conn:
        row = conn.execute(INSERT_ORDER, {
            "customerName": CUSTOMER_NAME, "customerPhone": CUSTOMER_PHONE, "technicianId": technicianId, "status": status, "adminId": adminId,
        }).one()
    return row.service_order_id, row.order_no

# Creates a job_assigned notification to the technician through the notification service and returns its row.
def createAssigned(engine, orderId, orderNo, technicianId, technicianName="Tom Tech", technicianPhone="60111111111"):
    with engine.begin() as conn:
        return notificationService.create(
            conn, orderId, orderNo, TYPE_JOB_ASSIGNED,
            {"type": RECIPIENT_TECHNICIAN, "name": technicianName, "phone": technicianPhone, "userId": technicianId},
            None,
            {"orderNo": orderNo, "technicianName": technicianName, "customerName": CUSTOMER_NAME, "customerPhone": CUSTOMER_PHONE,
             "address": "No 1, Jalan Damai, KL", "serviceTypeName": "Repair", "adminNotes": "Bring a ladder"},
            "req-assigned", "admin@example.com",
        )

# Creates a job_done notification to the customer, sent by the technician, and returns its row.
def createDone(engine, orderId, orderNo, technicianId, technicianName="Tom Tech"):
    with engine.begin() as conn:
        return notificationService.create(
            conn, orderId, orderNo, TYPE_JOB_DONE,
            {"type": RECIPIENT_CUSTOMER, "name": CUSTOMER_NAME, "phone": CUSTOMER_PHONE},
            technicianId,
            {"orderNo": orderNo, "customerName": CUSTOMER_NAME, "technicianName": technicianName, "completedAt": COMPLETED_AT},
            "req-done", "tech@example.com",
        )

JPEG_BYTES = b"\xff\xd8\xff\xe0" + b"\x00" * 60
PNG_BYTES = b"\x89PNG\r\n\x1a\n" + b"\x00" * 60
PDF_BYTES = b"%PDF-1.7\n" + b"\x00" * 60
MP4_BYTES = b"\x00\x00\x00\x18ftypmp42" + b"\x00" * 60


class FakeStorage:
    # An in-memory stand-in for the storage client; uploads are simulated with put, and down makes every call fail.
    def __init__(self):
        self.objects = {}
        self.deleted = []
        self.down = False
        self.lock = threading.Lock()

    # Raises StorageUnavailable while the fake is marked down.
    def check(self):
        if self.down:
            raise StorageUnavailable("fake storage down")

    # Simulates the browser uploading bytes to a signed URL.
    def put(self, path, content, contentType):
        with self.lock:
            self.objects[path] = (content, contentType)

    # Returns a fake signed upload URL for the path.
    def signUpload(self, path):
        self.check()
        return f"https://storage.test/upload/{path}?token=t"

    # Returns one fake signed view URL per path.
    def signViews(self, paths, expiresIn):
        self.check()
        return [f"https://storage.test/view/{path}?expires={expiresIn}" for path in paths]

    # Returns the stored size and type, or None when nothing was uploaded.
    def objectInfo(self, path):
        self.check()
        stored = self.objects.get(path)
        return None if stored is None else {"sizeBytes": len(stored[0]), "contentType": stored[1]}

    # Returns the first bytes of a stored object, or None.
    def readHead(self, path, length):
        self.check()
        stored = self.objects.get(path)
        return None if stored is None else stored[0][:length]

    # Deletes an object, ignoring a missing one.
    def deleteObject(self, path):
        self.check()
        with self.lock:
            self.objects.pop(path, None)
            self.deleted.append(path)

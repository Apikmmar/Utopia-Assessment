from sqlalchemy import text
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

# Queues a job_assigned notification to the technician through the notification service and returns its row.
def queueAssigned(engine, orderId, orderNo, technicianId, technicianName="Tom Tech", technicianPhone="60111111111"):
    with engine.begin() as conn:
        return notificationService.enqueue(
            conn, orderId, orderNo, TYPE_JOB_ASSIGNED,
            {"type": RECIPIENT_TECHNICIAN, "name": technicianName, "phone": technicianPhone, "userId": technicianId},
            None,
            {"orderNo": orderNo, "technicianName": technicianName, "customerName": CUSTOMER_NAME, "customerPhone": CUSTOMER_PHONE,
             "address": "No 1, Jalan Damai, KL", "serviceTypeName": "Repair", "adminNotes": "Bring a ladder"},
            "req-assigned", "admin@example.com",
        )

# Queues a job_done notification to the customer, sent by the technician, and returns its row.
def queueDone(engine, orderId, orderNo, technicianId, technicianName="Tom Tech"):
    with engine.begin() as conn:
        return notificationService.enqueue(
            conn, orderId, orderNo, TYPE_JOB_DONE,
            {"type": RECIPIENT_CUSTOMER, "name": CUSTOMER_NAME, "phone": CUSTOMER_PHONE},
            technicianId,
            {"orderNo": orderNo, "customerName": CUSTOMER_NAME, "technicianName": technicianName, "completedAt": COMPLETED_AT},
            "req-done", "tech@example.com",
        )

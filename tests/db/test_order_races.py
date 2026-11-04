import threading
from core.auth import AuthUser
from modules.order import service as orderService
from tests.order_support import insertOrder

RACERS = 2

# Returns the auth value for a seeded user.
def actorFor(userId, roleCode, email):
    return AuthUser(userId=userId, name="User", email=email, roleCode=roleCode)

# Runs the same call from several threads released together and returns their results.
def race(call, count=RACERS):
    barrier = threading.Barrier(count)
    results = [None] * count

    # Waits for every racer, then makes the call.
    def run(index):
        barrier.wait()
        results[index] = call()

    threads = [threading.Thread(target=run, args=(index,)) for index in range(count)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    return results

# Two starts of the same job at once let exactly one through; the other sees the new status.
def testRacingStartsLetOneWin(appDb, seedUser, scalar):
    adminId = seedUser("admin.race@example.com", "admin", password=None)
    techId = seedUser("tech.race@example.com", "technician", password=None, phone="60111111111")
    orderId, _ = insertOrder(appDb, adminId, techId)
    technician = actorFor(techId, "technician", "tech.race@example.com")
    results = race(lambda: orderService.startJob(technician, orderId, None))
    errors = sorted((error or {}).get("code", "OK") for _, error in results)
    assert errors == ["INVALID_TRANSITION", "OK"]
    assert scalar("SELECT count(*) FROM order_event WHERE service_order_id = :id AND event_type = 'started'", id=orderId) == 1

# A reassignment racing the technician's start ends with exactly one of them applied.
def testReassignRacingStart(appDb, seedUser, scalar):
    adminId = seedUser("admin.race2@example.com", "admin", password=None)
    techA = seedUser("tech.a.race@example.com", "technician", password=None, phone="60111111111")
    techB = seedUser("tech.b.race@example.com", "technician", password=None, phone="60122222222")
    orderId, _ = insertOrder(appDb, adminId, techA)
    admin = actorFor(adminId, "admin", "admin.race2@example.com")
    technician = actorFor(techA, "technician", "tech.a.race@example.com")
    calls = [lambda: orderService.assignTechnician(admin, orderId, techB, None), lambda: orderService.startJob(technician, orderId, None)]
    barrier = threading.Barrier(2)
    outcomes = [None, None]

    # Waits for the other racer, then runs its call.
    def run(index):
        barrier.wait()
        outcomes[index] = calls[index]()

    threads = [threading.Thread(target=run, args=(index,)) for index in range(2)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    assignError, startError = outcomes[0][1], outcomes[1][1]
    assert (assignError is None) != (startError is None)
    status, technicianId = scalar("SELECT status FROM service_order WHERE service_order_id = :id", id=orderId), scalar(
        "SELECT assigned_technician_id FROM service_order WHERE service_order_id = :id", id=orderId)
    if assignError is None:
        assert (status, technicianId) == ("assigned", techB) and startError["code"] in ("ORDER_NOT_FOUND", "INVALID_TRANSITION")
    else:
        assert (status, technicianId) == ("in_progress", techA) and assignError["code"] == "ORDER_LOCKED"

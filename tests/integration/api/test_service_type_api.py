from fastapi.testclient import TestClient
from core.db import transaction
from modules.service_type.service import activeServiceType
from tests.support import MISSING_ID

TECH_EMAIL = "tech.service.types@example.com"
SEEDED_NAMES = ["Aircond cleaning", "Repair", "Gas refill", "Installation", "General servicing"]

# The list needs a session.
def testListRequiresSession(app, appDb):
    response = TestClient(app).get("/service-types")
    assert response.status_code == 401
    assert response.json()["code"] == "NOT_AUTHENTICATED"

# Any signed-in role gets the five seeded types in display order, with camelCase fields only.
def testListsSeededTypesInOrder(seedUser, loggedIn):
    seedUser(TECH_EMAIL, "technician", phone="60123456789")
    response = loggedIn(TECH_EMAIL).get("/service-types")
    assert response.status_code == 200
    items = response.json()["items"]
    assert [item["name"] for item in items] == SEEDED_NAMES
    assert set(items[0]) == {"serviceTypeId", "code", "name"}
    assert items[0]["code"] == "cleaning"

# An inactive type is left out of the list.
def testInactiveTypeIsHidden(seedUser, loggedIn, execute):
    seedUser(TECH_EMAIL, "technician", phone="60123456789")
    execute("UPDATE service_type SET is_active = false WHERE service_type_code = 'repair'")
    names = [item["name"] for item in loggedIn(TECH_EMAIL).get("/service-types").json()["items"]]
    assert "Repair" not in names and len(names) == 4

# The order module's check accepts an active type and refuses an unknown or inactive one with a field error.
def testActiveServiceTypeCheck(appDb, scalar, execute):
    repairId = scalar("SELECT service_type_id FROM service_type WHERE service_type_code = 'repair'")
    with transaction() as conn:
        serviceType, error = activeServiceType(conn, repairId)
        assert error is None and serviceType["code"] == "repair"
        for unknown in (MISSING_ID, None):
            serviceType, error = activeServiceType(conn, unknown)
            assert serviceType is None and error["code"] == "INVALID_SERVICE_TYPE" and "serviceTypeId" in error["fields"]
    execute("UPDATE service_type SET is_active = false WHERE service_type_id = :id", id=repairId)
    with transaction() as conn:
        assert activeServiceType(conn, repairId)[1]["code"] == "INVALID_SERVICE_TYPE"

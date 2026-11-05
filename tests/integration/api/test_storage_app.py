from fastapi import APIRouter, Depends
from fastapi.testclient import TestClient
from api import main as apiMain
from core.auth import currentUser
from core.storage import StorageUnavailable

KEY = "service-role-key-value"

# A storage failure inside a route answers 503 STORAGE_UNAVAILABLE without the reason or any key.
def testStorageFailureAnswers503(monkeypatch):
    router = APIRouter()

    # Fails the way an unreachable storage service does.
    @router.get("/storage-probe", dependencies=[Depends(currentUser)])
    def probe():
        raise StorageUnavailable(f"sign_upload status 500 {KEY}")

    monkeypatch.setattr(apiMain, "featureRouters", lambda: [router])
    app = apiMain.createApp()
    app.dependency_overrides[currentUser] = lambda: None
    response = TestClient(app).get("/storage-probe")
    assert response.status_code == 503
    assert response.json() == {"detail": "File storage is temporarily unavailable.", "code": "STORAGE_UNAVAILABLE"}
    assert KEY not in response.text

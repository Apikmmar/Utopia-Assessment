import threading
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

# With WORKER_EMBEDDED on, the app starts the worker thread at startup and stops it at shutdown.
def testEmbeddedWorkerStartsAndStops(monkeypatch):
    monkeypatch.setenv("WORKER_EMBEDDED", "true")
    monkeypatch.setattr(apiMain.config, "requireStartupSettings", lambda: None)
    monkeypatch.setattr(apiMain, "dummyHash", lambda: None)
    stopped = threading.Event()

    class FakeWorker:
        # Records that the app asked the worker to stop.
        def stop(self):
            stopped.set()

    thread = threading.Thread(target=stopped.wait)
    started = []

    # Starts the fake worker thread the way the embedded worker would.
    def start():
        thread.start()
        started.append(True)
        return FakeWorker(), thread

    monkeypatch.setattr(apiMain, "startEmbeddedWorker", start)
    with TestClient(apiMain.createApp()):
        assert started == [True]
    assert stopped.is_set()
    assert not thread.is_alive()

# With WORKER_EMBEDDED off, no worker thread is started.
def testEmbeddedWorkerOffByDefault(monkeypatch):
    monkeypatch.delenv("WORKER_EMBEDDED", raising=False)
    monkeypatch.setattr(apiMain.config, "requireStartupSettings", lambda: None)
    monkeypatch.setattr(apiMain, "dummyHash", lambda: None)
    monkeypatch.setattr(apiMain, "startEmbeddedWorker", lambda: (_ for _ in ()).throw(AssertionError("started")))
    with TestClient(apiMain.createApp()):
        pass

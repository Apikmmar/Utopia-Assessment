import json
import httpx
import pytest
from core import config
from core import storage as coreStorage
from core.storage import StorageClient, StorageUnavailable

BASE_URL = "https://project.supabase.co"
KEY = "service-role-key"
BUCKET = "order-files"
PATH = "orders/abc/def.jpg"


class Recorder:
    # Answers every request with the given handler and keeps the requests it saw.
    def __init__(self, handler):
        self.handler = handler
        self.requests = []

    # Records one request and returns the handler's response.
    def __call__(self, request):
        self.requests.append(request)
        return self.handler(request)

# Returns a client whose HTTP traffic goes to the recorder instead of the network.
def clientFor(recorder):
    return StorageClient(BASE_URL, KEY, BUCKET, transport=httpx.MockTransport(recorder))

# Signing an upload calls the bucket path with the service role key and returns a full URL.
def testSignUploadReturnsFullUrl():
    recorder = Recorder(lambda request: httpx.Response(200, json={"url": f"/object/upload/sign/{BUCKET}/{PATH}?token=t"}))
    url = clientFor(recorder).signUpload(PATH)
    request = recorder.requests[0]
    assert url == f"{BASE_URL}/storage/v1/object/upload/sign/{BUCKET}/{PATH}?token=t"
    assert (request.method, request.url.path) == ("POST", f"/storage/v1/object/upload/sign/{BUCKET}/{PATH}")
    assert request.headers["Authorization"] == f"Bearer {KEY}" and request.headers["apikey"] == KEY

# View links are signed in one call and returned in path order, with None for a path storage could not sign.
def testSignViewsBatchesAndKeepsOrder():
    recorder = Recorder(lambda request: httpx.Response(200, json=[
        {"path": "b", "signedURL": "/object/sign/order-files/b?token=2"},
        {"path": "a", "signedURL": "/object/sign/order-files/a?token=1"},
        {"path": "c", "signedURL": None, "error": "not found"},
    ]))
    urls = clientFor(recorder).signViews(["a", "b", "c"], 300)
    assert urls == [f"{BASE_URL}/storage/v1/object/sign/order-files/a?token=1", f"{BASE_URL}/storage/v1/object/sign/order-files/b?token=2", None]
    assert len(recorder.requests) == 1
    assert json.loads(recorder.requests[0].content) == {"expiresIn": 300, "paths": ["a", "b", "c"]}

# No paths means no storage call.
def testSignViewsWithoutPathsSkipsTheCall():
    recorder = Recorder(lambda request: httpx.Response(500))
    assert clientFor(recorder).signViews([], 300) == []
    assert recorder.requests == []

# Object info reads the real size and type from either response shape.
@pytest.mark.parametrize("body", [
    {"size": 1234, "content_type": "image/jpeg"},
    {"metadata": {"size": 1234, "mimetype": "image/jpeg"}},
])
def testObjectInfoReadsSizeAndType(body):
    recorder = Recorder(lambda request: httpx.Response(200, json=body))
    assert clientFor(recorder).objectInfo(PATH) == {"sizeBytes": 1234, "contentType": "image/jpeg"}

# A missing object gives None, whether storage answers 404 or a 400 carrying a 404 body.
@pytest.mark.parametrize("response", [
    httpx.Response(404, json={"error": "not_found"}),
    httpx.Response(400, json={"statusCode": "404", "error": "not_found", "message": "Object not found"}),
])
def testObjectInfoMissingIsNone(response):
    assert clientFor(Recorder(lambda request: response)).objectInfo(PATH) is None

# Deleting sends the path as a prefix and ignores a missing object.
def testDeleteObjectIgnoresMissing():
    recorder = Recorder(lambda request: httpx.Response(404, json={"error": "not_found"}))
    clientFor(recorder).deleteObject(PATH)
    request = recorder.requests[0]
    assert (request.method, request.url.path, json.loads(request.content)) == ("DELETE", f"/storage/v1/object/{BUCKET}", {"prefixes": [PATH]})

# Timeouts, network errors, error statuses, and unreadable bodies all raise StorageUnavailable.
@pytest.mark.parametrize("handler", [
    lambda request: (_ for _ in ()).throw(httpx.ReadTimeout("slow", request=request)),
    lambda request: (_ for _ in ()).throw(httpx.ConnectError("down", request=request)),
    lambda request: httpx.Response(500, json={"error": "boom"}),
    lambda request: httpx.Response(200, content=b"not json"),
])
def testFailuresRaiseStorageUnavailable(handler):
    with pytest.raises(StorageUnavailable):
        clientFor(Recorder(handler)).signUpload(PATH)

# A storage failure reason never carries the key or a URL.
def testFailureReasonHasNoSecrets():
    with pytest.raises(StorageUnavailable) as raised:
        clientFor(Recorder(lambda request: httpx.Response(403))).objectInfo(PATH)
    assert KEY not in raised.value.reason and BASE_URL not in raised.value.reason

# The bucket is created private when missing and updated when it exists.
@pytest.mark.parametrize("existing,outcome,method", [(False, "created", "POST"), (True, "updated", "PUT")])
def testEnsureBucket(existing, outcome, method):
    recorder = Recorder(lambda request: httpx.Response(200 if existing or request.method != "GET" else 404, json={}))
    assert clientFor(recorder).ensureBucket(49, ["image/jpeg"]) == outcome
    write = recorder.requests[-1]
    assert write.method == method
    assert json.loads(write.content)["public"] is False and json.loads(write.content)["file_size_limit"] == 49

# Without storage settings the shared client is refused rather than half built.
def testGetStorageWithoutSettingsRaises(monkeypatch):
    monkeypatch.setattr(config, "supabaseUrl", lambda: None)
    monkeypatch.setattr(coreStorage, "_client", None)
    with pytest.raises(StorageUnavailable):
        coreStorage.getStorage()

# Reading a file's first bytes sends a range request to the authenticated object path, and a missing object is None.
def testReadHeadUsesRangeRequest():
    recorder = Recorder(lambda request: httpx.Response(206, content=b"\xff\xd8\xff\xe0rest"))
    assert clientFor(recorder).readHead(PATH, 4) == b"\xff\xd8\xff\xe0"
    request = recorder.requests[0]
    assert (request.url.path, request.headers["Range"]) == (f"/storage/v1/object/authenticated/{BUCKET}/{PATH}", "bytes=0-3")
    assert clientFor(Recorder(lambda request: httpx.Response(404, json={"error": "not_found"}))).readHead(PATH, 4) is None
    with pytest.raises(StorageUnavailable):
        clientFor(Recorder(lambda request: httpx.Response(500, json={}))).readHead(PATH, 4)

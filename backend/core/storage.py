import threading
from urllib.parse import quote
import httpx
from core import config
from core.logger import getLogger

log = getLogger(__name__)

STORAGE_PREFIX = "/storage/v1"
TIMEOUT_SECONDS = 10
NOT_FOUND_STATUSES = (404,)
NOT_FOUND_BODY_STATUS = "404"
NOT_FOUND_BODY_ERRORS = ("not_found", "Not Found")

_client = None
_clientLock = threading.Lock()


class StorageUnavailable(Exception):
    # Keeps a short reason for the log; it never holds a URL, token, or key.
    def __init__(self, reason):
        super().__init__(reason)
        self.reason = reason


class StorageClient:
    # Holds one reusable HTTP client for the project's storage API, with an optional test transport.
    def __init__(self, baseUrl, serviceRoleKey, bucket, transport=None):
        self.bucket = bucket
        self.storageUrl = baseUrl.rstrip("/") + STORAGE_PREFIX
        self.http = httpx.Client(
            base_url=self.storageUrl, timeout=TIMEOUT_SECONDS, transport=transport,
            headers={"Authorization": f"Bearer {serviceRoleKey}", "apikey": serviceRoleKey},
        )

    # Sends one storage request and returns the response, turning timeouts and network failures into StorageUnavailable.
    def send(self, operation, method, path, **kwargs):
        try:
            return self.http.request(method, path, **kwargs)
        except httpx.HTTPError as error:
            log.error("storage_request_failed operation=%s error_type=%s", operation, type(error).__name__)
            raise StorageUnavailable(f"{operation} {type(error).__name__}") from None

    # Returns the JSON body of a successful response, raising StorageUnavailable for any other status.
    def expectJson(self, operation, response):
        if response.is_success:
            try:
                return response.json()
            except ValueError:
                raise StorageUnavailable(f"{operation} invalid body") from None
        log.error("storage_request_rejected operation=%s status=%s", operation, response.status_code)
        raise StorageUnavailable(f"{operation} status {response.status_code}")

    # Returns the bucket-relative object path, percent-encoded for use in a URL.
    def objectPath(self, path):
        return f"{quote(self.bucket, safe='')}/{quote(path, safe='/')}"

    # Returns whether a response says the object does not exist; older storage versions answer 400 with a 404 body.
    def isNotFound(self, response):
        if response.status_code in NOT_FOUND_STATUSES:
            return True
        if response.status_code != 400:
            return False
        try:
            body = response.json()
        except ValueError:
            return False
        return str(body.get("statusCode")) == NOT_FOUND_BODY_STATUS or body.get("error") in NOT_FOUND_BODY_ERRORS

    # Returns a URL the browser PUTs the file to; storage never overwrites an existing object through it.
    def signUpload(self, path):
        body = self.expectJson("sign_upload", self.send("sign_upload", "POST", f"/object/upload/sign/{self.objectPath(path)}"))
        return self.storageUrl + body["url"]

    # Returns one signed view URL per path, in the same order, or None for a path storage could not sign.
    def signViews(self, paths, expiresIn):
        if not paths:
            return []
        response = self.send("sign_views", "POST", f"/object/sign/{quote(self.bucket, safe='')}", json={"expiresIn": expiresIn, "paths": list(paths)})
        signedByPath = {item.get("path"): item.get("signedURL") for item in self.expectJson("sign_views", response)}
        return [self.storageUrl + signedByPath[path] if signedByPath.get(path) else None for path in paths]

    # Returns the stored object's real size and content type, or None when the object does not exist.
    def objectInfo(self, path):
        response = self.send("object_info", "GET", f"/object/info/{self.objectPath(path)}")
        if self.isNotFound(response):
            return None
        body = self.expectJson("object_info", response)
        metadata = body.get("metadata") or {}
        size = body.get("size", metadata.get("size"))
        contentType = body.get("content_type") or body.get("contentType") or metadata.get("mimetype")
        if size is None or contentType is None:
            raise StorageUnavailable("object_info incomplete")
        return {"sizeBytes": int(size), "contentType": contentType}

    # Deletes one object; a missing object is ignored.
    def deleteObject(self, path):
        response = self.send("delete_object", "DELETE", f"/object/{quote(self.bucket, safe='')}", json={"prefixes": [path]})
        if not self.isNotFound(response):
            self.expectJson("delete_object", response)

    # Creates the private bucket, or updates its limits when it already exists, and returns which happened.
    def ensureBucket(self, fileSizeLimit, allowedTypes):
        settings = {"public": False, "file_size_limit": fileSizeLimit, "allowed_mime_types": list(allowedTypes)}
        bucketPath = f"/bucket/{quote(self.bucket, safe='')}"
        if self.isNotFound(self.send("get_bucket", "GET", bucketPath)):
            self.expectJson("create_bucket", self.send("create_bucket", "POST", "/bucket", json={"id": self.bucket, "name": self.bucket, **settings}))
            return "created"
        self.expectJson("update_bucket", self.send("update_bucket", "PUT", bucketPath, json=settings))
        return "updated"

    # Closes the underlying HTTP connection pool.
    def close(self):
        self.http.close()

# Returns the shared storage client, built once from configuration, raising StorageUnavailable when it is not configured.
def getStorage():
    global _client
    if _client is None:
        with _clientLock:
            if _client is None:
                url, key = config.supabaseUrl(), config.supabaseServiceRoleKey()
                if not url or not key:
                    raise StorageUnavailable("storage not configured")
                _client = StorageClient(url, key, config.storageBucket())
    return _client

# Closes and forgets the shared storage client.
def closeStorage():
    global _client
    with _clientLock:
        if _client is not None:
            _client.close()
            _client = None


__all__ = ["StorageClient", "StorageUnavailable", "closeStorage", "getStorage"]

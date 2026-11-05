import base64
import logging
import os
import httpx
import pytest
from core import config
from core.storage import closeStorage, getStorage
from tests.support import STATE_HEADERS

PNG_BYTES = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+jRZkAAAAASUVORK5CYII="
)
LIVE_STORAGE_BUCKET = config.storageBucket()

pytestmark = pytest.mark.skipif(
    os.getenv("RUN_LIVE_STORAGE_TESTS") != "1",
    reason="Set RUN_LIVE_STORAGE_TESTS=1 and RUN_DB_TESTS=1 for real Supabase writes with cleanup",
)


# Exercises real authentication, completion APIs, PostgreSQL, and Supabase with synthetic data and removes its files.
def testLiveUploadCompletionAndManagerView(appDb, seedUser, loggedIn, monkeypatch, caplog):
    caplog.set_level(logging.WARNING, logger="httpx")
    assert config.supabaseUrl() and config.supabaseServiceRoleKey(), "Configure real storage before opting in"
    monkeypatch.setenv("STORAGE_BUCKET", LIVE_STORAGE_BUCKET)
    seedUser("storage.admin@example.com", "admin", name="Storage Test Admin")
    technicianId = seedUser("storage.tech@example.com", "technician", name="Storage Test Technician", phone="60111111111")
    seedUser("storage.manager@example.com", "manager", name="Storage Test Manager")
    storage = getStorage()
    paths = []
    clients = []
    try:
        admin = loggedIn("storage.admin@example.com")
        clients.append(admin)
        technician = loggedIn("storage.tech@example.com")
        clients.append(technician)
        manager = loggedIn("storage.manager@example.com")
        clients.append(manager)
        serviceTypes = admin.get("/service-types")
        assert serviceTypes.status_code == 200
        created = admin.post("/orders", headers=STATE_HEADERS, json={
            "customerName": "Synthetic Storage Test", "customerPhone": "60123456789", "address": "Synthetic test address",
            "problemDescription": "Live storage verification", "serviceTypeId": serviceTypes.json()["items"][0]["serviceTypeId"],
            "quotedPrice": "150.00", "technicianId": str(technicianId),
        })
        assert created.status_code == 201
        orderId = created.json()["order"]["orderId"]
        assert technician.post(f"/orders/{orderId}/start", headers=STATE_HEADERS).status_code == 200
        attachments = {}
        with httpx.Client(timeout=15) as browser:
            for kind in ("completion", "receipt"):
                ticket = technician.post(f"/orders/{orderId}/attachments", headers=STATE_HEADERS, json={
                    "kind": kind, "fileName": "storage-test.png", "contentType": "image/png", "sizeBytes": len(PNG_BYTES),
                })
                assert ticket.status_code == 201
                body = ticket.json()
                attachmentId = body["attachment"]["attachmentId"]
                paths.append(f"orders/{orderId}/{attachmentId}.png")
                uploaded = browser.put(body["uploadUrl"], content=PNG_BYTES, headers={"Content-Type": "image/png", "x-upsert": "false"})
                assert uploaded.is_success, f"Signed upload returned HTTP {uploaded.status_code}"
                attachments[kind] = attachmentId
            completed = technician.post(f"/orders/{orderId}/completion", headers=STATE_HEADERS, json={
                "workDone": "Verified real storage upload and reading", "extraCharges": "20.50",
                "attachmentIds": [attachments["completion"]],
                "payment": {"amount": "170.50", "method": "cash", "receiptAttachmentId": attachments["receipt"]},
            })
            assert completed.status_code == 201
            result = completed.json()
            assert result["order"]["status"] == "job_done"
            assert result["completion"]["finalAmount"] == "170.50"
            assert result["completion"]["payment"]["receiptAttachmentId"] == attachments["receipt"]
            listed = manager.get(f"/orders/{orderId}/attachments")
            assert listed.status_code == 200
            items = listed.json()["items"]
            assert {item["attachmentId"] for item in items} == set(attachments.values())
            for item in items:
                assert item["status"] == "uploaded"
                assert item["sizeBytes"] == len(PNG_BYTES)
                viewed = browser.get(item["viewUrl"])
                assert viewed.is_success and viewed.content == PNG_BYTES, "Manager signed view did not return the uploaded bytes"
        assert manager.post(f"/orders/{orderId}/review", headers=STATE_HEADERS).status_code == 200
        assert manager.post(f"/orders/{orderId}/close", headers=STATE_HEADERS).status_code == 200
    except httpx.HTTPError as error:
        raise AssertionError(f"Live storage HTTP transport failed: {type(error).__name__}") from None
    finally:
        cleanupErrors = []
        try:
            for path in paths:
                try:
                    storage.deleteObject(path)
                    assert storage.objectInfo(path) is None, "Test object cleanup failed"
                except Exception as error:
                    cleanupErrors.append(type(error).__name__)
        finally:
            for client in clients:
                client.close()
            closeStorage()
        assert not cleanupErrors, f"Test object cleanup failures: {cleanupErrors}"

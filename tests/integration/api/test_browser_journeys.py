import logging
import os
from pathlib import Path
import shutil
import subprocess
import threading
import time
import pytest
from sqlalchemy import text
import uvicorn
from api.main import createApp
from core import config
from core.storage import closeStorage, getStorage

ROOT = Path(__file__).resolve().parents[3]
LIVE_BUCKET = config.storageBucket()
pytestmark = pytest.mark.skipif(
    os.getenv("RUN_LIVE_E2E") != "1", reason="Set RUN_LIVE_E2E=1 and RUN_DB_TESTS=1 for real browser/database/storage tests",
)


# Hosts the real app over HTTP for Playwright using only the fixture's disposable schema, then cleans up uploads.
def testNonAiBrowserJourneys(appDb, seedUser, monkeypatch, caplog):
    caplog.set_level(logging.WARNING, logger="httpx")
    monkeypatch.setenv("APP_ALLOWED_ORIGIN", "http://localhost:5174")
    monkeypatch.setenv("STORAGE_BUCKET", LIVE_BUCKET)
    monkeypatch.setenv("AI_ENABLED", "false")
    assert config.supabaseUrl() and config.supabaseServiceRoleKey(), "Live storage configuration is required"
    seedUser("admin.live@example.com", "admin", name="Live Admin")
    seedUser("manager.live@example.com", "manager", name="Live Manager")
    seedUser("other.live@example.com", "technician", name="Other Technician", phone="60111111111")
    output = ROOT / "tmp" / "e2e-live"
    output.mkdir(parents=True, exist_ok=True)
    server = uvicorn.Server(uvicorn.Config(createApp(), host="127.0.0.1", port=8765, access_log=False, log_level="warning"))
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    cleanupErrors = []
    try:
        deadline = time.monotonic() + 15
        while not server.started and thread.is_alive() and time.monotonic() < deadline:
            threading.Event().wait(0.05)
        assert server.started, "Isolated test API did not start on port 8765"
        node = shutil.which("node")
        assert node, "Node is required for Playwright"
        command = [node, str(ROOT / "frontend/node_modules/@playwright/test/cli.js"), "test", "--config", "playwright.live.config.ts"]
        with (output / "browser.log").open("w", encoding="utf-8") as log:
            result = subprocess.run(command, cwd=ROOT / "frontend", stdout=log, stderr=subprocess.STDOUT, timeout=720)
        assert result.returncode == 0, "Real browser journeys failed; inspect tmp/e2e-live/browser.log and failure screenshots"
    finally:
        server.should_exit = True
        thread.join(timeout=15)
        assert not thread.is_alive(), "Test API did not stop before schema cleanup"
        with appDb.connect() as conn:
            paths = conn.execute(text("SELECT storage_path FROM order_attachment")).scalars().all()
        storage = getStorage()
        try:
            for path in paths:
                try:
                    assert path.startswith("orders/"), "Unexpected test attachment prefix"
                    storage.deleteObject(path)
                    assert storage.objectInfo(path) is None, "Test object still exists"
                except Exception as error:
                    cleanupErrors.append(type(error).__name__)
        finally:
            closeStorage()
        assert not cleanupErrors, f"Live upload cleanup failed: {cleanupErrors}"

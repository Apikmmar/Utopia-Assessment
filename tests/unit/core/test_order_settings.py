import logging
import pytest
from core import config
from core.error import STATUS_BY_CODE
from core.logger import RedactionFilter

STORAGE_SETTINGS = ("SUPABASE_URL", "SUPABASE_SERVICE_ROLE_KEY", "STORAGE_BUCKET", "STORAGE_VIEW_URL_SECONDS")
ORDER_ERROR_STATUSES = {
    "ORDER_NOT_FOUND": 404, "INVALID_TRANSITION": 409, "ORDER_LOCKED": 409, "INVALID_SERVICE_TYPE": 422,
    "INVALID_TECHNICIAN": 422, "COMPLETION_EXISTS": 409, "COMPLETION_NOT_FOUND": 404, "ATTACHMENT_LIMIT": 409,
    "ATTACHMENT_INVALID": 422, "ATTACHMENT_NOT_UPLOADED": 422, "ATTACHMENT_NOT_FOUND": 404, "ATTACHMENT_LOCKED": 409,
    "STORAGE_UNAVAILABLE": 503, "NOTIFICATION_NOT_FOUND": 404, "NOTIFICATION_NOT_READY": 409, "NOTIFICATION_NOT_FAILED": 409,
}

# Clears every storage setting so a developer's backend/.env cannot change the expectations.
@pytest.fixture(autouse=True)
def cleanSettings(monkeypatch):
    for name in STORAGE_SETTINGS:
        monkeypatch.delenv(name, raising=False)

# Without configuration, storage is absent and uses its defaults.
def testStorageDefaults():
    assert config.supabaseUrl() is None
    assert config.supabaseServiceRoleKey() is None
    assert config.storageBucket() == "order-files"
    assert config.storageViewUrlSeconds() == 300

# Configured values override the defaults, and the project URL loses its trailing slash.
def testStorageOverrides(monkeypatch):
    monkeypatch.setenv("SUPABASE_URL", "https://example.supabase.co/")
    monkeypatch.setenv("STORAGE_BUCKET", "other")
    monkeypatch.setenv("STORAGE_VIEW_URL_SECONDS", "60")
    assert config.supabaseUrl() == "https://example.supabase.co"
    assert (config.storageBucket(), config.storageViewUrlSeconds()) == ("other", 60)

# Storage settings are not startup requirements.
def testStorageIsNotRequiredAtStartup():
    assert "SUPABASE_URL" not in config.REQUIRED_APP_SETTINGS
    assert "SUPABASE_SERVICE_ROLE_KEY" not in config.REQUIRED_APP_SETTINGS

# Invalid numbers and booleans fail loudly instead of being ignored.
@pytest.mark.parametrize("name,value,reader", [
    ("STORAGE_VIEW_URL_SECONDS", "0", config.storageViewUrlSeconds),
    ("STORAGE_VIEW_URL_SECONDS", "abc", config.storageViewUrlSeconds),
    ("AUTH_COOKIE_SECURE", "maybe", config.authCookieSecure),
])
def testInvalidSettingsRaise(monkeypatch, name, value, reader):
    monkeypatch.setenv(name, value)
    with pytest.raises(RuntimeError):
        reader()

# Every order error code is registered with the status the design gives it.
def testOrderErrorCodesRegistered():
    assert {code: STATUS_BY_CODE.get(code) for code in ORDER_ERROR_STATUSES} == ORDER_ERROR_STATUSES

# Storage keys, signed URLs, message text, and deep links are masked in log text and extras.
def testRedactsStorageAndNotificationSecrets():
    record = logging.LogRecord(
        "n", logging.INFO, "p", 1,
        "service_role_key=sk upload_url=https://u view_url=https://v deep_link=https://wa.me/601 message=Hi%20Ali", None, None,
    )
    record.serviceRoleKey = "sk"
    RedactionFilter().filter(record)
    text = record.getMessage()
    for secret in ("sk ", "https://u", "https://v", "wa.me", "Hi%20Ali"):
        assert secret not in text
    assert record.serviceRoleKey == "[redacted]"

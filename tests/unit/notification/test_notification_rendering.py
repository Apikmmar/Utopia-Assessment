import uuid
from urllib.parse import parse_qs, urlparse
import pytest
from core.auth import AuthUser
from modules.notification.provider import DeepLinkProvider, providerFor, whatsappUrl
from modules.notification.service import canSend, formatLocalTime, renderMessage

TECH_ID = uuid.uuid4()
OTHER_ID = uuid.uuid4()
ASSIGNED_DATA = {
    "orderNo": "ORD-000123", "technicianName": "Tom Tech", "customerName": "Siti & Co", "customerPhone": "60123456789",
    "address": "No 1, Jalan Damai", "serviceTypeName": "Repair", "adminNotes": "Bring a ladder",
}

# Returns an actor with the given role and id.
def actor(roleCode, userId=TECH_ID):
    return AuthUser(userId=userId, name="User", email="user@example.com", roleCode=roleCode)

# The customer message is the PDF sample with the time shown in Malaysian time.
def testJobDoneMessage():
    message = renderMessage("job_done", {"customerName": "Siti", "orderNo": "ORD-000123", "technicianName": "Tom Tech", "completedAt": "2026-11-04T07:45:00+00:00"})
    assert message == "Hi Siti, Job ORD-000123 has been completed by Technician Tom Tech at 4 Nov 2026, 3:45 PM. Please check and leave feedback. Thank you!"

# Midnight and noon use the 12 hour clock, and the date follows Malaysian time across midnight UTC.
@pytest.mark.parametrize("isoText,expected", [
    ("2026-11-04T16:00:00+00:00", "5 Nov 2026, 12:00 AM"),
    ("2026-11-04T04:00:00Z", "4 Nov 2026, 12:00 PM"),
    ("2026-01-01T01:05:00+00:00", "1 Jan 2026, 9:05 AM"),
])
def testLocalTimeFormat(isoText, expected):
    assert formatLocalTime(isoText) == expected

# The technician summary lists the job, and includes the instructions only when present.
def testJobAssignedMessageWithAndWithoutNotes():
    withNotes = renderMessage("job_assigned", ASSIGNED_DATA)
    assert withNotes.splitlines() == [
        "Hi Tom Tech, you have a new job: ORD-000123.",
        "Customer: Siti & Co (60123456789)",
        "Address: No 1, Jalan Damai",
        "Service: Repair",
        "Instructions: Bring a ladder",
    ]
    for notes in (None, "", "   "):
        assert "Instructions" not in renderMessage("job_assigned", {**ASSIGNED_DATA, "adminNotes": notes})

# Braces in customer text are kept as text rather than treated as template fields.
def testUserTextIsNotATemplate():
    message = renderMessage("job_assigned", {**ASSIGNED_DATA, "customerName": "{orderNo}", "adminNotes": "{x}"})
    assert "Customer: {orderNo} (60123456789)" in message and "Instructions: {x}" in message

# The deep link carries the phone digits and the fully percent-encoded message, which decodes back exactly.
def testWhatsappUrlEncoding():
    message = "Hi Siti & Co, Job #1 100% done?\nLine 2 / é"
    url = whatsappUrl("+60 12-345 6789", message)
    parsed = urlparse(url)
    assert (parsed.scheme, parsed.netloc, parsed.path) == ("https", "wa.me", "/60123456789")
    assert parse_qs(parsed.query)["text"] == [message]
    assert " " not in url and "&" not in parsed.query

# The deep link provider returns a ready link, refuses an over-long link, and unknown providers are refused.
def testDeepLinkProvider():
    result = DeepLinkProvider().deliver({"recipient_phone": "60123456789"}, "Hello")
    assert result.status == "ready" and result.deepLink == "https://wa.me/60123456789?text=Hello"
    with pytest.raises(ValueError):
        DeepLinkProvider().deliver({"recipient_phone": "60123456789"}, "x" * 9000)
    assert isinstance(providerFor("deeplink"), DeepLinkProvider)
    with pytest.raises(LookupError):
        providerFor("whatsapp_api")

# Only ready or opened notifications can be sent: by any admin, or by the technician who is their sender, never by a manager.
@pytest.mark.parametrize("role,senderId,status,expected", [
    ("admin", None, "ready", True),
    ("admin", None, "opened", True),
    ("admin", None, "queued", False),
    ("admin", None, "failed", False),
    ("technician", TECH_ID, "ready", True),
    ("technician", OTHER_ID, "ready", False),
    ("technician", None, "ready", False),
    ("manager", None, "ready", False),
])
def testCanSend(role, senderId, status, expected):
    assert canSend(actor(role), {"status": status, "sender_user_id": senderId}) is expected

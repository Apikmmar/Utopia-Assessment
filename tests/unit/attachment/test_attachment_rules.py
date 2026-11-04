import uuid
import pytest
from modules.attachment.constants import IMAGE_MAX_BYTES, VIDEO_MAX_BYTES
from modules.attachment.service import checkTypeAndSize, matchesSignature, storagePath
from tests.order_support import JPEG_BYTES, MP4_BYTES, PDF_BYTES, PNG_BYTES

HEIC_BYTES = b"\x00\x00\x00\x18ftypheic" + b"\x00" * 8
MOV_BYTES = b"\x00\x00\x00\x14ftypqt  " + b"\x00" * 8
WEBP_BYTES = b"RIFF\x00\x00\x00\x00WEBPVP8 "

# Allowed types pass up to their limit: 10 MB for images and PDF, 49 MB for video.
@pytest.mark.parametrize("kind,contentType,size", [
    ("completion", "image/jpeg", IMAGE_MAX_BYTES),
    ("completion", "image/heic", 1),
    ("completion", "application/pdf", IMAGE_MAX_BYTES),
    ("completion", "video/mp4", VIDEO_MAX_BYTES),
    ("completion", "video/quicktime", VIDEO_MAX_BYTES),
    ("receipt", "image/png", IMAGE_MAX_BYTES),
    ("receipt", "application/pdf", 1000),
])
def testAllowedTypesAndSizes(kind, contentType, size):
    assert checkTypeAndSize(kind, contentType, size) is None

# One byte over a limit, an empty file, a video receipt, and an unknown type are refused.
@pytest.mark.parametrize("kind,contentType,size", [
    ("completion", "image/jpeg", IMAGE_MAX_BYTES + 1),
    ("completion", "application/pdf", IMAGE_MAX_BYTES + 1),
    ("completion", "video/mp4", VIDEO_MAX_BYTES + 1),
    ("completion", "image/jpeg", 0),
    ("receipt", "video/mp4", 1000),
    ("completion", "image/gif", 1000),
    ("completion", "text/html", 1000),
])
def testRefusedTypesAndSizes(kind, contentType, size):
    assert checkTypeAndSize(kind, contentType, size)["code"] == "ATTACHMENT_INVALID"

# Each type is recognised by its first bytes.
@pytest.mark.parametrize("contentType,head", [
    ("image/jpeg", JPEG_BYTES), ("image/png", PNG_BYTES), ("image/webp", WEBP_BYTES), ("image/heic", HEIC_BYTES),
    ("application/pdf", PDF_BYTES), ("video/mp4", MP4_BYTES), ("video/quicktime", MOV_BYTES), ("video/quicktime", b"\x00\x00\x00\x08wide"),
])
def testSignaturesMatch(contentType, head):
    assert matchesSignature(contentType, head) is True

# A file labelled with the wrong type, such as HTML or a PDF named as a photo, is refused.
@pytest.mark.parametrize("contentType,head", [
    ("image/jpeg", b"<html><script>"), ("image/png", JPEG_BYTES), ("application/pdf", PNG_BYTES), ("video/mp4", HEIC_BYTES),
    ("image/heic", MP4_BYTES), ("image/webp", b"RIFF\x00\x00\x00\x00WAVE"), ("image/gif", b"GIF89a"),
])
def testSignaturesMismatch(contentType, head):
    assert matchesSignature(contentType, head) is False

# The storage path is built from ids and the type's extension only.
def testStoragePathIgnoresFileName():
    orderId, attachmentId = uuid.uuid4(), uuid.uuid4()
    assert storagePath(orderId, attachmentId, "video/quicktime") == f"orders/{orderId}/{attachmentId}.mov"

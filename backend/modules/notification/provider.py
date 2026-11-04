from dataclasses import dataclass
from typing import Optional
from urllib.parse import quote
from modules.notification.constants import DEEP_LINK_MAX_LENGTH, PROVIDER_DEEPLINK, STATUS_READY, WHATSAPP_BASE_URL


@dataclass(frozen=True)
class DeliveryResult:
    status: str
    deepLink: Optional[str] = None
    providerMessageId: Optional[str] = None


class DeepLinkProvider:
    # Builds a wa.me link for a person to open and send; it cannot know whether the message is then sent.
    def deliver(self, notification, message):
        link = whatsappUrl(notification["recipient_phone"], message)
        if len(link) > DEEP_LINK_MAX_LENGTH:
            raise ValueError("DeepLinkTooLong")
        return DeliveryResult(status=STATUS_READY, deepLink=link)

# Returns the WhatsApp deep link that opens a chat with the phone and the message filled in.
def whatsappUrl(phone, message):
    digits = "".join(character for character in phone if character.isdigit())
    return f"{WHATSAPP_BASE_URL}{digits}?text={quote(message, safe='')}"

# Returns the provider for a notification's provider column.
def providerFor(providerCode):
    if providerCode == PROVIDER_DEEPLINK:
        return DeepLinkProvider()
    raise LookupError("UnknownProvider")


__all__ = ["DeepLinkProvider", "DeliveryResult", "providerFor", "whatsappUrl"]

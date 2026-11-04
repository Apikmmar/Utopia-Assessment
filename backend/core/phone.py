import re

PHONE_SEPARATORS = re.compile(r"[\s\-()]")
PHONE_MIN_DIGITS = 8
PHONE_MAX_DIGITS = 15
LOCAL_PREFIX = "0"
COUNTRY_PREFIX = "60"
INVALID_PHONE_MESSAGE = "Enter a valid phone number."

# Returns a customer phone as 8 to 15 digits with a local leading 0 turned into Malaysia's 60,
# or None when it cannot be one.
def normaliseCustomerPhone(raw):
    if not isinstance(raw, str):
        return None
    digits = PHONE_SEPARATORS.sub("", raw.strip())
    if digits.startswith("+"):
        digits = digits[1:]
    if not digits.isascii() or not digits.isdigit():
        return None
    if digits.startswith(LOCAL_PREFIX):
        digits = COUNTRY_PREFIX + digits[1:]
    if not PHONE_MIN_DIGITS <= len(digits) <= PHONE_MAX_DIGITS:
        return None
    return digits


__all__ = ["INVALID_PHONE_MESSAGE", "PHONE_MAX_DIGITS", "PHONE_MIN_DIGITS", "normaliseCustomerPhone"]

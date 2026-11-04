import re

EMAIL_PATTERN = re.compile(r"[^@\s]+@[^@\s]+\.[^@\s]+")
EMAIL_MAX_LENGTH = 255

# Returns the one canonical form of an email used for every lookup and write.
def normalizeEmail(email):
    return (email or "").strip().lower()

# Returns whether a normalized email has a plausible shape and fits the column.
def isValidEmail(email):
    return len(email) <= EMAIL_MAX_LENGTH and EMAIL_PATTERN.fullmatch(email) is not None


__all__ = ["EMAIL_MAX_LENGTH", "isValidEmail", "normalizeEmail"]

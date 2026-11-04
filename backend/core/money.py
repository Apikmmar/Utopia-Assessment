from decimal import Decimal, InvalidOperation

CENTS = Decimal("0.01")
MAX_AMOUNT = Decimal("99999999.99")
MAX_DECIMAL_PLACES = 2
INVALID_AMOUNT_MESSAGE = "Enter an amount from 0 to 99999999.99 with at most two decimal places."

# Returns a JSON number or numeric string as a two-place Decimal amount, or None when it is not
# a finite, non-negative value within the limit with at most two decimal places.
def parseAmount(raw):
    if isinstance(raw, bool) or not isinstance(raw, (int, float, str, Decimal)):
        return None
    try:
        value = Decimal(str(raw).strip()) if not isinstance(raw, Decimal) else raw
    except InvalidOperation:
        return None
    if not value.is_finite() or value < 0 or value > MAX_AMOUNT:
        return None
    if value.normalize().as_tuple().exponent < -MAX_DECIMAL_PLACES:
        return None
    return (Decimal(0) if value.is_zero() else value).quantize(CENTS)

# Returns an amount as a plain two-decimal string, the form amounts take in JSON responses.
def formatAmount(value):
    return format(Decimal(value).quantize(CENTS), "f")


__all__ = ["INVALID_AMOUNT_MESSAGE", "MAX_AMOUNT", "formatAmount", "parseAmount"]

from decimal import Decimal
import pytest
from core.money import formatAmount, parseAmount
from core.phone import normaliseCustomerPhone

# Local, spaced, dashed, bracketed, and international forms all become the same digits.
@pytest.mark.parametrize("raw,expected", [
    ("012-345 6789", "60123456789"),
    ("+60 12 345 6789", "60123456789"),
    ("(012) 345-6789", "60123456789"),
    ("60123456789", "60123456789"),
    ("  0123456789  ", "60123456789"),
    ("12345678", "12345678"),
])
def testNormalisesCustomerPhones(raw, expected):
    assert normaliseCustomerPhone(raw) == expected

# Too short, too long, letters, non-ASCII digits, empty, and non-text values are refused.
@pytest.mark.parametrize("raw", ["+60 12", "1234567", "6012345678901234", "012-ABC-6789", "０１２３４５６７８９", "", "   ", None, 60123456789])
def testRejectsInvalidCustomerPhones(raw):
    assert normaliseCustomerPhone(raw) is None

# Numbers and numeric strings become two-place Decimals, including the boundaries.
@pytest.mark.parametrize("raw,expected", [
    (0, "0.00"),
    ("150.5", "150.50"),
    (150.5, "150.50"),
    ("1.500", "1.50"),
    (" 20 ", "20.00"),
    ("99999999.99", "99999999.99"),
    ("-0", "0.00"),
    (Decimal("12.3"), "12.30"),
])
def testParsesAmounts(raw, expected):
    assert parseAmount(raw) == Decimal(expected)
    assert formatAmount(parseAmount(raw)) == expected

# Negative, over the limit, more than two places, non-finite, boolean, and non-numeric values are refused.
@pytest.mark.parametrize("raw", ["0.005", "-1", -0.01, "100000000.00", "99999999.991", "NaN", "Infinity", "abc", "", True, None, [1]])
def testRejectsInvalidAmounts(raw):
    assert parseAmount(raw) is None

# Formatting never uses scientific notation.
def testFormatAmountIsPlain():
    assert formatAmount(Decimal("1E+2")) == "100.00"

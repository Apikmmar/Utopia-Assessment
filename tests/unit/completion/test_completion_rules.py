from decimal import Decimal
import pytest
from modules.completion.service import cleanCompletion

# Missing extra charges count as zero, text is trimmed, and blank remarks become None.
def testDefaultsAndTrimming():
    fields = {}
    values = cleanCompletion({"work_done": "  Replaced capacitor ", "remarks": "   "}, fields)
    assert fields == {}
    assert (values["work_done"], values["remarks"], values["extra_charges"]) == ("Replaced capacitor", None, Decimal("0.00"))
    assert (values["payment_amount"], values["payment_method"], values["receipt_attachment_id"]) == (None, None, None)

# Extra charge boundaries: zero and the maximum pass, negatives, a third decimal place, and one cent over do not.
@pytest.mark.parametrize("raw, valid", [
    (0, True), ("20.50", True), ("99999999.99", True), ("-0.01", False), ("0.005", False), ("100000000.00", False), ("abc", False),
])
def testExtraChargeBoundaries(raw, valid):
    fields = {}
    cleanCompletion({"work_done": "Done", "extra_charges": raw}, fields)
    assert ("extraCharges" not in fields) is valid

# Work done is required and limited to 2000 characters, remarks to 2000.
def testTextLimits():
    fields = {}
    cleanCompletion({"work_done": "x" * 2001, "remarks": "y" * 2001}, fields)
    assert set(fields) == {"workDone", "remarks"}
    fields = {}
    cleanCompletion({"work_done": "x" * 2000, "remarks": "y" * 2000}, fields)
    assert fields == {}

# A payment keeps its amount, method, and receipt together; a bad amount is reported under payment.amount.
def testPaymentFields():
    fields = {}
    values = cleanCompletion({"work_done": "Done", "payment": {"amount": 50, "method": "cash", "receipt_attachment_id": "r1"}}, fields)
    assert fields == {}
    assert (values["payment_amount"], values["payment_method"], values["receipt_attachment_id"]) == (Decimal("50.00"), "cash", "r1")
    fields = {}
    cleanCompletion({"work_done": "Done", "payment": {"amount": "-5", "method": "cash"}}, fields)
    assert set(fields) == {"payment.amount"}

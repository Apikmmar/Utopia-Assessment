from datetime import date
import pytest
from modules.order.service import checkPostpone

TODAY = date(2026, 11, 5)

# The reason must be a known code; the new date must be from today to 90 days ahead.
@pytest.mark.parametrize("reasonCode,newDate,expected", [
    ("parts_needed", None, set()),
    ("weather", date(2026, 11, 5), set()),
    ("other", date(2027, 2, 3), set()),
    ("lunch", None, {"reasonCode"}),
    ("weather", date(2026, 11, 4), {"newDate"}),
    ("weather", date(2027, 2, 4), {"newDate"}),
])
def testPostponeChecks(reasonCode, newDate, expected):
    assert set(checkPostpone(reasonCode, newDate, TODAY)) == expected

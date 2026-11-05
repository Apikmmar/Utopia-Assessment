from datetime import timedelta
from modules.ai.constants import DAYS_PER_WEEK, PERIOD_LAST_WEEK, PERIOD_THIS_WEEK, PERIOD_TODAY
from modules.kpi.period import midnightUtc, weekLabel, weekStart

# Returns the named period relative to the business date as display dates, a label, and [startUtc, endUtc) bounds.
# Weeks run Monday to Sunday, as on the KPI dashboard.
def resolvePeriod(period, today):
    if period == PERIOD_TODAY:
        first, days = today, 1
    elif period == PERIOD_THIS_WEEK:
        first, days = weekStart(today), DAYS_PER_WEEK
    elif period == PERIOD_LAST_WEEK:
        first, days = weekStart(today) - timedelta(days=DAYS_PER_WEEK), DAYS_PER_WEEK
    else:
        raise ValueError(f"Unknown period {period}")
    end = first + timedelta(days=days)
    last = end - timedelta(days=1)
    label = f"{first.day} {first:%b} {first.year}" if days == 1 else weekLabel(first, last)
    return {"label": label, "start_date": first, "end_date": last, "start_utc": midnightUtc(first), "end_utc": midnightUtc(end)}


__all__ = ["resolvePeriod"]

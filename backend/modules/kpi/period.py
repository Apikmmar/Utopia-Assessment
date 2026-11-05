from datetime import datetime, time, timedelta, timezone
from core.businesstime import businessZone
from modules.kpi.constants import DAYS_PER_WEEK, EARLIEST_WEEK_DATE

# Returns the Monday that starts the week containing the day.
def weekStart(day):
    return day - timedelta(days=day.weekday())

# Returns the UTC instant of a business-time midnight, so the bounds never depend on a fixed offset.
def midnightUtc(day):
    return datetime.combine(day, time.min, tzinfo=businessZone).astimezone(timezone.utc)

# Returns a short label such as "3 to 9 Nov 2026", "27 Oct to 2 Nov 2026", or "29 Dec 2025 to 4 Jan 2026".
def weekLabel(first, last):
    end = f"{last.day} {last:%b} {last.year}"
    if first.year != last.year:
        return f"{first.day} {first:%b} {first.year} to {end}"
    if first.month != last.month:
        return f"{first.day} {first:%b} to {end}"
    return f"{first.day} to {end}"

# Resolves the business week (Monday to Sunday) containing the anchor, or today's week when there is none, to its
# display dates and [startUtc, endUtc) bounds; returns None for an anchor before 2020 or in a future week.
def resolveWeek(anchorDate, today):
    anchor = anchorDate or today
    if anchor < EARLIEST_WEEK_DATE or weekStart(anchor) > weekStart(today):
        return None
    start = weekStart(anchor)
    end = start + timedelta(days=DAYS_PER_WEEK)
    last = end - timedelta(days=1)
    return {
        "label": weekLabel(start, last), "start_date": start, "end_date": last,
        "start_utc": midnightUtc(start), "end_utc": midnightUtc(end), "is_current": start == weekStart(today),
    }


__all__ = ["midnightUtc", "resolveWeek", "weekLabel", "weekStart"]

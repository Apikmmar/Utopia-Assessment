from datetime import date

EARLIEST_WEEK_DATE = date(2020, 1, 1)
DAYS_PER_WEEK = 7
INVALID_PERIOD_MESSAGE = "Choose a week from 2020 up to this week."
NOT_ALLOWED_MESSAGE = "Only admins and managers can view the KPI dashboard."


__all__ = ["DAYS_PER_WEEK", "EARLIEST_WEEK_DATE", "INVALID_PERIOD_MESSAGE", "NOT_ALLOWED_MESSAGE"]

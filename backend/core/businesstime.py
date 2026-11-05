from datetime import datetime
from zoneinfo import ZoneInfo

BUSINESS_TIMEZONE = "Asia/Kuala_Lumpur"
businessZone = ZoneInfo(BUSINESS_TIMEZONE)

# Returns today's date in the business timezone, from the given aware time or the clock.
def businessToday(now=None):
    return (now or datetime.now(businessZone)).astimezone(businessZone).date()


__all__ = ["BUSINESS_TIMEZONE", "businessToday", "businessZone"]

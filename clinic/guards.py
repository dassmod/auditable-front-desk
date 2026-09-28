from datetime import datetime, timedelta
from clinic.world import OPEN_DAYS, OPEN_TIME, CLOSE_TIME, SLOT_MINUTES

def slot_is_free(start, booked):
    if start not in booked:
        return "allow"
    else:
        return "deny"

def within_opening_hours(start):
    start_time = datetime.fromisoformat(start)
    end_time = start_time + timedelta(minutes=SLOT_MINUTES)

    day_ok = start_time.weekday() in OPEN_DAYS
    starts_ok = start_time.strftime("%H:%M") >= OPEN_TIME
    end_ok = end_time.strftime("%H:%M") <= CLOSE_TIME
    same_day = end_time.date() == start_time.date()

    if day_ok and starts_ok and end_ok and same_day:
        return "allow"
    else:
        return "deny"

def not_in_past(start, now):
    if datetime.fromisoformat(start) > datetime.fromisoformat(now):
        return "allow"
    else:
        return "deny"
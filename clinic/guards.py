"""
The booking guards: pure functions that return "allow" or "deny".

Each one depends only on its arguments (no clock, no globals), so a replay
engine can re-run it from a recorded trace. Parameter names are public: a
trace records its inputs under these names, so renaming one breaks every
trace already saved.
"""

from datetime import datetime, timedelta
from clinic.world import OPEN_DAYS, OPEN_TIME, CLOSE_TIME, SLOT_MINUTES

def slot_is_free(start, booked):
    """allow if `start` is not already in `booked`."""
    if start not in booked:
        return "allow"
    else:
        return "deny"

def within_opening_hours(start):
    """allow if a slot starting at `start` is on an open day and ends the same day within opening hours."""
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
    """allow if `start` is later than `now`. `now` is an argument, never read from a clock."""
    if datetime.fromisoformat(start) > datetime.fromisoformat(now):
        return "allow"
    else:
        return "deny"
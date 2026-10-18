"""
The clinic's world: its name, opening hours, slot length and calendar.

These are plain values with no logic. The guards read the hours. The agent
reads the name and passes the calendar to the guards as an argument.
"""

CLINIC_NAME = "Alder Street Family Clinic"

# Weekday numbers as Python counts them: Monday is 0, Sunday is 6.
OPEN_DAYS = (0, 1, 2, 3, 4)
# "HH:MM" strings, so the guards can compare them as text.
OPEN_TIME = "09:00"
CLOSE_TIME = "18:00"

SLOT_MINUTES = 30

# The starting calendar: slot start times as ISO strings. A Session takes its
# own copy (`fresh_calendar` in session.py). `agent.py` and `scripted.py` use
# this one list directly and their booking effect appends to it, so it changes
# while a run goes on. It is not saved between runs.
BOOKED = [
    "2026-10-06T14:00",
    "2026-10-06T16:00",
    "2026-10-07T09:30",
]

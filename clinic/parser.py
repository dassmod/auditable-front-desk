"""
Pure functions that read input. `parse_booking` turns a typed message into a
slot (used by the scripted loop). `parse_arguments` checks the model's
tool-call arguments (used by the agent).
"""

from datetime import datetime, timedelta
import json

DAYS = {
    "monday": 0,
    "tuesday": 1,
    "wednesday": 2,
    "thursday": 3,
    "friday": 4
}

def parse_booking(text, now):
    """
    Turn "book tuesday 15:00" into an ISO start like "2026-10-06T15:00".
    Returns None if the text cannot be read.

    `now` is an ISO string passed in, so the same text and `now` always give
    the same answer. A weekday means its next occurrence, never today.
    """
    words = text.lower().split()

    if len(words) != 3:
        return None

    verb, day, time_text = words

    if verb != "book":
        return None

    target = DAYS.get(day)
    if target == None:
        return None

    try:
        clock = datetime.strptime(time_text, "%H:%M")
    except ValueError:
        return None

    now = datetime.fromisoformat(now)
    today = now.weekday()

    ahead = (target - today) % 7
    if ahead == 0:
        ahead = 7

    date = now.date() + timedelta(days=ahead)
    return date.isoformat() + "T" + clock.strftime("%H:%M")

def parse_arguments(arguments):
    """
    Return "ok" if `arguments` is a JSON object with a `start` key. Otherwise
    return the layer that failed: "invalid_json" (not JSON), "not_an_object"
    (JSON, but not an object) or "missing_start" (an object with no `start`).

    It does not check the type or the format of `start`.
    """
    try:
        json.loads(arguments)["start"]
    except json.JSONDecodeError:
        return "invalid_json"
    except KeyError:
        return "missing_start"
    except TypeError:
        return "not_an_object"
    return "ok"
